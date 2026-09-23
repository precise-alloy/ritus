import { readFile, realpath, stat } from "node:fs/promises";
import { homedir } from "node:os";
import { dirname, isAbsolute, join, parse, relative } from "node:path";
import { git, gitAvailable, gitTopLevel, mainWorktree } from "./git.ts";
import { contains, samePath, toPosix } from "./paths.ts";
import { DEFAULT_MODEL } from "./policy.ts";
import { ToolError } from "./types.ts";

export interface Workspace {
  /** Real path of the directory the agent works in. */
  root: string;
  /** Git top-level containing `root`, or null outside a repository. */
  gitTop: string | null;
}

export type KeySource = "workspace" | "main-worktree" | "environment";

export interface JevConfig {
  apiKey: string | null;
  keySource: KeySource | null;
  keyFile: string | null;
  model: string;
  baseURL: string | undefined;
  proxy: string | undefined;
  /** Where to put the key when none is configured. */
  setupFile: string;
  /** A key file that was skipped because git tracks it. */
  ignoredKeyFile: string | null;
}

const KEYS = ["TYPESAFE_API_KEY", "TYPESAFE_DEFAULT_MODEL", "TYPESAFE_BASE_URL", "HTTPS_PROXY", "https_proxy"] as const;
type Key = (typeof KEYS)[number];

export async function resolveWorkspace(input: string, roots: readonly string[] | null): Promise<Workspace> {
  if (!isAbsolute(input)) {
    throw new ToolError("input_error", "workspace must be an absolute path.",
      "Pass the absolute path of the repository you are working in (your current working directory).");
  }
  let root: string;
  try {
    root = await realpath(input);
    if (!(await stat(root)).isDirectory()) throw new Error("not a directory");
  } catch {
    throw new ToolError("input_error", `workspace is not an existing directory: ${input}`);
  }
  if (parse(root).root === root || samePath(root, homedir())) {
    throw new ToolError("input_error", "workspace must be a project directory, not a filesystem root or the home directory.");
  }
  if (roots && roots.length > 0 && !roots.some((allowed) => contains(allowed, root))) {
    throw new ToolError("input_error", `workspace is outside the host's workspace roots: ${root}`);
  }
  return { root, gitTop: await gitTopLevel(root) };
}

/** Minimal dotenv reader for the few keys ritus-jev uses; the first definition of a key wins. */
export function parseEnv(text: string): Partial<Record<Key, string>> {
  const values: Partial<Record<Key, string>> = {};
  for (const raw of text.replace(/^\uFEFF/, "").split(/\r?\n/)) {
    const line = raw.trim().replace(/^export\s+/, "");
    if (!line || line.startsWith("#")) continue;
    const eq = line.indexOf("=");
    if (eq <= 0) continue;
    const key = line.slice(0, eq).trim() as Key;
    if (!KEYS.includes(key) || values[key] !== undefined) continue;
    let value = line.slice(eq + 1).trim();
    const quote = value[0];
    if ((quote === '"' || quote === "'") && value.indexOf(quote, 1) > 0) {
      value = value.slice(1, value.indexOf(quote, 1));
    } else {
      value = value.replace(/\s+#.*$/, "").trim();
    }
    if (value) values[key] = value;
  }
  return values;
}

const fileCache = new Map<string, {
  mtimeMs: number;
  size: number;
  values: Partial<Record<Key, string>>;
  tracked?: { value: boolean; at: number };
}>();

async function readEnvFile(file: string): Promise<Partial<Record<Key, string>> | null> {
  let info;
  try {
    info = await stat(file);
  } catch {
    return null;
  }
  if (!info.isFile()) return null;
  const cached = fileCache.get(file);
  if (cached && cached.mtimeMs === info.mtimeMs && cached.size === info.size) return cached.values;
  const values = parseEnv(await readFile(file, "utf8"));
  fileCache.set(file, { mtimeMs: info.mtimeMs, size: info.size, values });
  return values;
}

const TRACKED_TTL_MS = 30_000;

/**
 * True when the repository at `top` tracks `file`, under any letter case (a case-insensitive file system lets a
 * committed `.RITUS/.env.local` stand in for `.ritus/.env.local`) or through a committed directory symlink.
 */
async function isTracked(file: string, top: string | null): Promise<boolean> {
  if (!top || !gitAvailable()) return false;
  const entry = fileCache.get(file);
  if (entry?.tracked && Date.now() - entry.tracked.at < TRACKED_TTL_MS) return entry.tracked.value;
  const specs = new Set<string>();
  for (const path of [file, await realpath(file).catch(() => null)]) {
    if (path && contains(top, path)) specs.add(`:(literal,icase)${toPosix(relative(top, path))}`);
  }
  let value = false;
  if (specs.size > 0) {
    const out = await git(top, ["ls-files", "-z", "--cached", "--", ...specs], 1024 * 1024).catch(() => null);
    value = out !== null && out.code === 0 && out.stdout.length > 0;
  }
  if (entry) entry.tracked = { value, at: Date.now() };
  return value;
}

/** Validates a configured URL without echoing it (proxy URLs can carry credentials). */
function checkedURL(value: string | undefined, name: string, allowPlainHttp: boolean): string | undefined {
  if (!value) return undefined;
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw new ToolError("input_error", `${name} is not a valid URL.`);
  }
  const loopback = url.hostname === "localhost" || url.hostname === "127.0.0.1" || url.hostname === "[::1]";
  if (url.protocol === "https:" || (url.protocol === "http:" && (allowPlainHttp || loopback))) return value;
  throw new ToolError("input_error", `${name} must be an https URL${allowPlainHttp ? " or an http proxy" : " (http only for localhost)"}.`);
}

async function envFiles(ws: Workspace): Promise<{ file: string; source: KeySource; top: string | null }[]> {
  const files: { file: string; source: KeySource; top: string | null }[] = [];
  const repo = ws.gitTop && contains(ws.gitTop, ws.root) ? ws.gitTop : null;
  for (let dir = ws.root; ; dir = dirname(dir)) {
    files.push({ file: join(dir, ".ritus", ".env.local"), source: "workspace", top: repo });
    if (samePath(dir, repo ?? ws.root) || dirname(dir) === dir) break;
  }
  if (ws.gitTop) {
    const main = await mainWorktree(ws.gitTop);
    if (main && !samePath(main, ws.gitTop)) files.push({ file: join(main, ".ritus", ".env.local"), source: "main-worktree", top: main });
  }
  return files;
}

/**
 * Key lookup: nearest .ritus/.env.local up to the git top-level, then the main worktree's, then the environment.
 * Model, base URL and proxy come only from the source that supplies the key, so a file in the repository cannot
 * redirect a key defined elsewhere. A key file that git tracks is repository-controlled (any checked-out branch can
 * supply it), so it is skipped and the lookup continues.
 */
export async function loadConfig(ws: Workspace, env: NodeJS.ProcessEnv = process.env): Promise<JevConfig> {
  const setupFile = join(ws.gitTop && contains(ws.gitTop, ws.root) ? ws.gitTop : ws.root, ".ritus", ".env.local");
  let ignoredKeyFile: string | null = null;
  for (const { file, source, top } of await envFiles(ws)) {
    const values = await readEnvFile(file);
    if (!values?.TYPESAFE_API_KEY) continue;
    if (await isTracked(file, top)) {
      ignoredKeyFile ??= file;
      continue;
    }
    return {
      apiKey: values.TYPESAFE_API_KEY,
      keySource: source,
      keyFile: file,
      model: values.TYPESAFE_DEFAULT_MODEL ?? DEFAULT_MODEL,
      baseURL: checkedURL(values.TYPESAFE_BASE_URL, "TYPESAFE_BASE_URL", false),
      proxy: checkedURL(values.HTTPS_PROXY ?? values.https_proxy, "HTTPS_PROXY", true),
      setupFile,
      ignoredKeyFile,
    };
  }
  const envKey = env.TYPESAFE_API_KEY?.trim() || null;
  if (!envKey && ignoredKeyFile) {
    throw new ToolError("disabled", `${ignoredKeyFile} is tracked by git, so ritus-jev ignores the key in it.`,
      "Untrack it with `git rm --cached` (rotate the key if it was pushed), or set TYPESAFE_API_KEY in the environment. Continue with ordinary tools.");
  }
  return {
    apiKey: envKey,
    keySource: envKey ? "environment" : null,
    keyFile: null,
    model: (envKey && env.TYPESAFE_DEFAULT_MODEL?.trim()) || DEFAULT_MODEL,
    baseURL: envKey ? checkedURL(env.TYPESAFE_BASE_URL?.trim(), "TYPESAFE_BASE_URL", false) : undefined,
    // Bun's fetch reads HTTPS_PROXY from the environment on its own.
    proxy: undefined,
    setupFile,
    ignoredKeyFile,
  };
}

export function maskKey(key: string): string {
  return key.length > 12 ? `${key.slice(0, 3)}...${key.slice(-4)}` : "****";
}
