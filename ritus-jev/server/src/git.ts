import { basename, dirname, resolve } from "node:path";
import { LIMITS } from "./policy.ts";
import { ToolError } from "./types.ts";

export interface GitOutput {
  code: number;
  stdout: Uint8Array;
  stderr: string;
}

let gitPath: string | null | undefined;

export function gitAvailable(): boolean {
  if (gitPath === undefined) gitPath = Bun.which("git");
  return gitPath !== null;
}

// Each call sets its own pathspec mode (`--literal-pathspecs` or `:(literal,icase)`); these variables would disable
// that magic or make git refuse the combination.
const PATHSPEC_ENV = new Set(["GIT_LITERAL_PATHSPECS", "GIT_GLOB_PATHSPECS", "GIT_NOGLOB_PATHSPECS", "GIT_ICASE_PATHSPECS"]);

function gitEnv(): Record<string, string | undefined> {
  const env: Record<string, string | undefined> = { ...process.env, GIT_OPTIONAL_LOCKS: "0", GIT_TERMINAL_PROMPT: "0" };
  for (const key of Object.keys(env)) {
    if (PATHSPEC_ENV.has(key.toUpperCase())) delete env[key];
  }
  return env;
}

/** Runs git with a fixed argument array (no shell) and read-only intent. */
export async function git(cwd: string, args: string[], maxBytes: number = LIMITS.MAX_DIFF_BYTES): Promise<GitOutput> {
  if (!gitAvailable()) throw new ToolError("input_error", "git is not available on PATH.");
  const proc = Bun.spawn(["git", ...args], {
    cwd,
    stdin: "ignore",
    stdout: "pipe",
    stderr: "pipe",
    env: gitEnv(),
  });
  const timer = setTimeout(() => proc.kill(), LIMITS.GIT_TIMEOUT_MS);
  try {
    const [stdout, stderr, code] = await Promise.all([
      new Response(proc.stdout).arrayBuffer(),
      new Response(proc.stderr).text(),
      proc.exited,
    ]);
    if (stdout.byteLength > maxBytes) {
      throw new ToolError("scope_too_large", `git ${args[0]} output exceeds ${Math.round(maxBytes / 1048576)} MB.`,
        "Narrow the request with `paths`.");
    }
    return { code, stdout: new Uint8Array(stdout), stderr: stderr.trim() };
  } finally {
    clearTimeout(timer);
  }
}

export async function gitText(cwd: string, args: string[]): Promise<string | null> {
  const result = await git(cwd, args, 1024 * 1024);
  return result.code === 0 ? new TextDecoder().decode(result.stdout).trim() : null;
}

export async function gitTopLevel(dir: string): Promise<string | null> {
  if (!gitAvailable()) return null;
  const top = await gitText(dir, ["rev-parse", "--show-toplevel"]);
  return top ? resolve(top) : null;
}

/** Root of the main worktree when `top` is a linked worktree, otherwise null. */
export async function mainWorktree(top: string): Promise<string | null> {
  const common = await gitText(top, ["rev-parse", "--path-format=absolute", "--git-common-dir"]);
  if (!common) return null;
  const commonDir = resolve(common);
  return basename(commonDir) === ".git" ? dirname(commonDir) : null;
}

/** Commit where HEAD's branch left `ref`, or null when there is none (unrelated histories, unknown ref). */
export async function mergeBase(cwd: string, ref: string): Promise<string | null> {
  return gitText(cwd, ["merge-base", "--", ref, "HEAD"]).catch(() => null);
}

/** True when the working tree has staged, unstaged or untracked (not ignored) changes. */
export async function hasWorkingTreeChanges(cwd: string): Promise<boolean> {
  const out = await git(cwd, ["status", "--porcelain", "-z", "--untracked-files=normal"], 1024 * 1024).catch(() => null);
  return out !== null && out.code === 0 && out.stdout.length > 0;
}

export function splitNul(bytes: Uint8Array): string[] {
  return new TextDecoder().decode(bytes).split("\0").filter(Boolean);
}

const REF = /^(?!-)(?!.*\.\.)[A-Za-z0-9._\/@{}~^-]{1,200}$/;

export function assertRef(ref: string, field: string): string {
  if (!REF.test(ref)) throw new ToolError("input_error", `Invalid git ref in ${field}: ${JSON.stringify(ref)}.`);
  return ref;
}
