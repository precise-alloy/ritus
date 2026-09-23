import { existsSync, realpathSync } from "node:fs";
import { homedir, tmpdir } from "node:os";
import { isAbsolute, join, relative, resolve, sep } from "node:path";

export const IS_WINDOWS = process.platform === "win32";

function comparable(path: string): string {
  const resolved = resolve(path);
  return IS_WINDOWS ? resolved.toLowerCase() : resolved;
}

export function samePath(a: string, b: string): boolean {
  return comparable(a) === comparable(b);
}

/** True when `child` is `parent` or inside it. */
export function contains(parent: string, child: string): boolean {
  const rel = relative(comparable(parent), comparable(child));
  return rel === "" || (rel !== ".." && !rel.startsWith(`..${sep}`) && !isAbsolute(rel));
}

export function toPosix(path: string): string {
  return path.split(sep).join("/");
}

export function realpathOrNull(path: string): string | null {
  try {
    // The native variant expands Windows short (8.3) names and resolves the file actually opened.
    return realpathSync.native(path);
  } catch {
    return null;
  }
}

/** True for a Windows path that names an NTFS stream (`file::$DATA`, `dir::$INDEX_ALLOCATION`) or a device-qualified part. */
export function hasStreamSyntax(path: string): boolean {
  if (!IS_WINDOWS) return false;
  const rest = /^[A-Za-z]:/.test(path) ? path.slice(2) : path;
  return rest.includes(":");
}

let cachedTempRoots: string[] | null = null;

/** Directories where agents may save long command output for `locate` (outside the workspace). */
export function tempRoots(): string[] {
  if (cachedTempRoots) return cachedTempRoots;
  const candidates = [tmpdir(), process.env.TEMP, process.env.TMP, process.env.TMPDIR, "/tmp"];
  if (IS_WINDOWS) candidates.push(join(homedir(), "AppData", "Local", "Temp"));
  const roots: string[] = [];
  for (const candidate of candidates) {
    if (!candidate || !existsSync(candidate)) continue;
    const real = realpathOrNull(candidate);
    if (real && !roots.some((root) => samePath(root, real))) roots.push(real);
  }
  cachedTempRoots = roots;
  return roots;
}

export function inTempRoot(path: string): boolean {
  return tempRoots().some((root) => contains(root, path));
}
