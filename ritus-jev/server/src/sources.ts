import { createHash } from "node:crypto";
import { readdir, stat } from "node:fs/promises";
import { isAbsolute, join, relative } from "node:path";
import { blockKind, chunkText, splitLines } from "./chunk.ts";
import type { Workspace } from "./config.ts";
import { diffBlocks, type DiffSpec } from "./diff.ts";
import { access, isDenied, isNoise, mapLimit, readSafe, readText, redactText } from "./files.ts";
import { git, splitNul } from "./git.ts";
import { contains, hasStreamSyntax, inTempRoot, IS_WINDOWS, realpathOrNull, tempRoots, toPosix } from "./paths.ts";
import { LIMITS } from "./policy.ts";
import { ToolError, type Block } from "./types.ts";

export interface ScopeFile {
  /** Workspace-relative POSIX path, or the absolute path of a temp file. */
  display: string;
  abs: string;
  explicit: boolean;
}

export interface Scope {
  files: ScopeFile[];
  skipped: { denied: number; noise: number; missing: string[] };
}

export interface SourceRef {
  path?: string;
  start_line?: number;
  end_line?: number;
  text?: string;
  id?: string;
  diff?: DiffSpec;
}

const IGNORE_DIRS = new Set([
  "node_modules", ".git", ".hg", ".svn", "dist", "build", "out", "coverage", ".next", ".nuxt", "target", "bin", "obj",
  "vendor", ".venv", "venv", "__pycache__", ".idea", ".vscode", ".ritus", ".cache", ".turbo", ".gradle",
]);
const GLOB = /[*?[\]{}]/;
const INLINE_ID = /^[A-Za-z0-9_.:-]{1,64}$/;

const fold = (path: string): string => (IS_WINDOWS ? path.toLowerCase() : path);

async function walk(root: string): Promise<string[]> {
  const files: string[] = [];
  const queue = [""];
  while (queue.length > 0 && files.length <= LIMITS.MAX_FILES * 2) {
    const dir = queue.shift() as string;
    let entries;
    try {
      entries = await readdir(join(root, dir), { withFileTypes: true });
    } catch {
      continue;
    }
    for (const entry of entries) {
      const rel = dir ? `${dir}/${entry.name}` : entry.name;
      if (entry.isDirectory()) {
        if (!IGNORE_DIRS.has(entry.name)) queue.push(rel);
      } else if (entry.isFile()) {
        files.push(rel);
      }
    }
  }
  return files;
}

/** Workspace files as relative POSIX paths: git-tracked plus untracked-not-ignored, or a filesystem walk. */
export async function listFiles(ws: Workspace): Promise<string[]> {
  if (ws.gitTop) {
    const out = await git(ws.root, ["ls-files", "-z", "--cached", "--others", "--exclude-standard"], 128 * 1024 * 1024);
    if (out.code === 0) return [...new Set(splitNul(out.stdout))];
  }
  return walk(ws.root);
}

/** Converts a caller path (relative, or absolute inside the workspace) to a workspace-relative POSIX path. */
export function toRelative(ws: Workspace, raw: string): string {
  const input = raw.trim();
  if (hasStreamSyntax(input)) throw new ToolError("input_error", `Unsupported path syntax (\`:\`): ${raw}`);
  const rel = isAbsolute(input) ? toPosix(relative(ws.root, input)) : input.replaceAll("\\", "/");
  const clean = rel.replace(/^(\.\/)+/, "").replace(/\/+$/, "");
  if (clean.split("/").includes("..") || isAbsolute(clean)) throw new ToolError("input_error", `Path is outside the workspace: ${raw}`);
  return clean === "." ? "" : clean;
}

function externalFile(raw: string): ScopeFile | null {
  if (hasStreamSyntax(raw.trim())) return null;
  const real = realpathOrNull(raw.trim());
  if (!real || !inTempRoot(real)) return null;
  return { display: toPosix(real), abs: real, explicit: true };
}

/** Leading path segments of a glob before its first wildcard segment. */
function staticPrefix(glob: string): string {
  const fixed: string[] = [];
  for (const part of glob.split("/")) {
    if (GLOB.test(part)) break;
    fixed.push(part);
  }
  return fixed.join("/");
}

/** Listed files under `dir` plus files on disk there (walk skips dependency and build directories). */
async function filesUnder(ws: Workspace, listed: readonly string[], dir: string): Promise<string[]> {
  const prefix = `${fold(dir)}/`;
  const files = new Map<string, string>();
  for (const path of listed) if (fold(path).startsWith(prefix)) files.set(fold(path), path);
  const info = await stat(join(ws.root, dir)).catch(() => null);
  if (info?.isDirectory()) for (const path of await walk(join(ws.root, dir))) files.set(fold(`${dir}/${path}`), `${dir}/${path}`);
  return [...files.values()];
}

/** Resolves `paths` (files, directories, globs; default = whole workspace) into readable candidate files. */
export async function resolveScope(ws: Workspace, patterns: readonly string[] | undefined): Promise<Scope> {
  const listed = await listFiles(ws);
  const listedByKey = new Map(listed.map((path) => [fold(path), path]));
  const chosen = new Map<string, ScopeFile>();
  const skipped: Scope["skipped"] = { denied: 0, noise: 0, missing: [] };
  const add = (rel: string, explicit: boolean) => {
    if (isDenied(rel)) {
      skipped.denied++;
      return;
    }
    if (!explicit && isNoise(rel)) {
      skipped.noise++;
      return;
    }
    chosen.set(fold(rel), { display: rel, abs: join(ws.root, rel), explicit });
  };

  if (!patterns || patterns.length === 0) {
    for (const path of listed) add(path, false);
  }
  for (const raw of patterns ?? []) {
    if (isAbsolute(raw.trim()) && !contains(ws.root, raw.trim())) {
      const file = externalFile(raw);
      if (!file) {
        throw new ToolError("input_error", `Path is outside the workspace: ${raw}`,
          "Use workspace paths, or save command output under the OS temp directory.");
      }
      if (isDenied(file.display)) skipped.denied++;
      else chosen.set(fold(file.abs), file);
      continue;
    }
    const rel = toRelative(ws, raw);
    if (rel === "") {
      for (const path of listed) add(path, false);
      continue;
    }
    const before = chosen.size + skipped.denied + skipped.noise;
    if (GLOB.test(rel)) {
      // A glob with a directory prefix also sees ignored files under that directory; a bare glob stays gitignore-aware.
      const base = staticPrefix(rel);
      const glob = new Bun.Glob(rel);
      for (const path of base ? await filesUnder(ws, listed, base) : listed) if (glob.match(path)) add(path, false);
      if (chosen.size + skipped.denied + skipped.noise === before) skipped.missing.push(raw);
      continue;
    }
    const exact = listedByKey.get(fold(rel));
    const info = exact ? null : await stat(join(ws.root, rel)).catch(() => null);
    if (exact || info?.isFile()) {
      add(exact ?? rel, true);
    } else if (info?.isDirectory()) {
      // A named directory is read from the filesystem, including files git ignores (for example local-only docs).
      for (const path of await filesUnder(ws, listed, rel)) add(path, false);
      if (chosen.size + skipped.denied + skipped.noise === before) skipped.missing.push(raw);
    } else {
      skipped.missing.push(raw);
    }
  }
  if (chosen.size > LIMITS.MAX_FILES) {
    throw new ToolError("scope_too_large", `${chosen.size} files in scope (limit ${LIMITS.MAX_FILES}).`, "Narrow `paths`.");
  }
  return { files: [...chosen.values()], skipped };
}

export interface LoadedFile {
  file: ScopeFile;
  lines: string[];
  blocks: Block[];
  redactions: number;
}

const loadedCache = new Map<string, { mtimeMs: number; size: number; loaded: Omit<LoadedFile, "file"> }>();
let cachedChars = 0;

/**
 * Reads, redacts and chunks scope files. Containment and deny rules run on each file's real path before the cache
 * (keyed by real path, display path and the redacted secrets) is consulted. Display paths are rebuilt from the real
 * path (relative to `roots[0]`, the workspace, else absolute), so short names and links cite the file actually read.
 */
export async function loadScope(
  scope: Scope,
  secrets: readonly string[],
  roots: readonly string[],
): Promise<{ loaded: LoadedFile[]; unreadable: number; denied: number }> {
  let total = 0;
  let unreadable = 0;
  let denied = 0;
  const seen = new Set<string>();
  const secretsKey = createHash("sha256").update(secrets.join("\0")).digest("hex").slice(0, 16);
  const results = await mapLimit(scope.files, LIMITS.READ_CONCURRENCY, async (requested): Promise<LoadedFile | null> => {
    const checked = await access(requested.abs, roots);
    if (!checked.ok) {
      if (checked.reason === "denied") denied++;
      else unreadable++;
      return null;
    }
    if (seen.has(fold(checked.real))) return null;
    seen.add(fold(checked.real));
    const display = checked.root === roots[0] ? toPosix(relative(checked.root, checked.real)) : toPosix(checked.real);
    const file: ScopeFile = { ...requested, display, abs: checked.real };
    const info = await stat(checked.real).catch(() => null);
    if (!info?.isFile()) {
      unreadable++;
      return null;
    }
    const key = `${checked.real}\0${file.display}\0${secretsKey}`;
    const cached = loadedCache.get(key);
    if (cached && cached.mtimeMs === info.mtimeMs && cached.size === info.size) return { file, ...cached.loaded };
    const text = await readText(checked.real, file.explicit);
    if (text === null) {
      unreadable++;
      return null;
    }
    total += text.length;
    if (total > LIMITS.MAX_READ_BYTES) {
      throw new ToolError("scope_too_large", "Scope exceeds the read limit.", "Narrow `paths` or add `terms`.");
    }
    const redacted = redactText(text, secrets);
    const loaded = { lines: splitLines(redacted.text), blocks: chunkText(file.display, redacted.text), redactions: redacted.count };
    if (cachedChars > 64 * 1024 * 1024) {
      loadedCache.clear();
      cachedChars = 0;
    }
    loadedCache.set(key, { mtimeMs: info.mtimeMs, size: info.size, loaded });
    cachedChars += text.length;
    return { file, ...loaded };
  });
  return { loaded: results.filter((entry): entry is LoadedFile => entry !== null), unreadable, denied };
}

/**
 * Resolves evidence/item references. `blocks` chunks file ranges for search; `whole` keeps each reference as one
 * block. Diff references expand to hunks either way. Default reference: working-tree diff against HEAD.
 */
export async function resolveRefs(
  ws: Workspace,
  refs: readonly SourceRef[],
  mode: "blocks" | "whole",
  secrets: readonly string[],
): Promise<{ blocks: Block[]; redactions: number }> {
  const blocks: Block[] = [];
  let redactions = 0;
  let inline = 0;
  for (const ref of refs) {
    const kinds = [ref.path !== undefined, ref.text !== undefined, ref.diff !== undefined].filter(Boolean).length;
    if (kinds !== 1) throw new ToolError("input_error", "Each source needs exactly one of `path`, `text` or `diff`.");
    if (ref.text !== undefined) {
      if (ref.text.length > 40_000) throw new ToolError("input_error", "Inline `text` is limited to 40,000 characters; pass a `path` instead.");
      if (ref.id !== undefined && !INLINE_ID.test(ref.id)) throw new ToolError("input_error", `Inline id ${JSON.stringify(ref.id)} must match ${INLINE_ID.source}.`);
      const redacted = redactText(ref.text, secrets);
      redactions += redacted.count;
      inline++;
      blocks.push({ path: ref.id ?? `T${inline}`, start: 1, end: splitLines(redacted.text).length, text: redacted.text, kind: "inline" });
      continue;
    }
    if (ref.diff !== undefined) {
      const relPaths = (ref.diff.paths ?? []).map((path) => toRelative(ws, path)).filter(Boolean);
      const diffed = await diffBlocks(ws, ref.diff, relPaths, secrets);
      redactions += diffed.redactions;
      blocks.push(...diffed.blocks);
      continue;
    }
    const raw = ref.path as string;
    let file: ScopeFile | null;
    if (isAbsolute(raw.trim()) && !contains(ws.root, raw.trim())) {
      file = externalFile(raw);
    } else {
      const rel = toRelative(ws, raw);
      file = rel ? { display: rel, abs: join(ws.root, rel), explicit: true } : null;
    }
    if (!file) throw new ToolError("input_error", `Path is outside the workspace: ${raw}`);
    const read = isDenied(file.display)
      ? ({ text: null, reason: "denied" } as const)
      : await readSafe(file.abs, true, [ws.root, ...tempRoots()]);
    if (read.text === null) {
      if (read.reason === "denied") throw new ToolError("input_error", `Refusing to read a credential or key file: ${raw}`);
      if (read.reason === "outside") throw new ToolError("input_error", `Path resolves outside the workspace: ${raw}`);
      throw new ToolError("input_error", `Not a readable text file (missing, binary, or over 2 MB): ${raw}`);
    }
    const text = read.text;
    file = { ...file, abs: read.real, display: contains(ws.root, read.real) ? toPosix(relative(ws.root, read.real)) : toPosix(read.real) };
    const redacted = redactText(text, secrets);
    redactions += redacted.count;
    const lines = splitLines(redacted.text);
    const start = Math.min(Math.max(1, Math.floor(ref.start_line ?? 1)), Math.max(1, lines.length));
    const end = Math.min(Math.max(start, Math.floor(ref.end_line ?? lines.length)), lines.length);
    const slice = lines.slice(start - 1, end).join("\n");
    if (mode === "whole") {
      blocks.push({ path: file.display, start, end, text: slice, kind: blockKind(file.display) });
    } else {
      for (const block of chunkText(file.display, slice)) {
        blocks.push({ ...block, start: block.start + start - 1, end: block.end + start - 1 });
      }
    }
  }
  return { blocks, redactions };
}
