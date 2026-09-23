import { open, realpath, stat } from "node:fs/promises";
import { relative } from "node:path";
import { contains } from "./paths.ts";
import { LIMITS } from "./policy.ts";

// Paths that are never read or sent (credentials, keys, VCS internals).
const DENY: RegExp[] = [
  /(^|\/)\.git\//,
  /\.(pem|key|p12|pfx|jks|keystore|kdbx|ppk|asc|gpg)$/,
  /(^|\/)id_(rsa|dsa|ecdsa|ed25519)(\.pub)?$/,
  /(^|\/)\.(npmrc|yarnrc\.yml|pypirc|netrc|pgpass|git-credentials|htpasswd)$/,
  /(^|\/)(credentials|secrets?)(\.(json|ya?ml|toml|ini|txt|xml|cfg|conf))?$/,
  /(^|\/)\.(aws|ssh|gnupg|docker|kube)\//,
  /(^|\/)\.terraform\/|\.tfstate(\.backup)?$/,
];

// Paths skipped unless the caller names them explicitly (binary, generated, vendored, lockfiles).
const NOISE: RegExp[] = [
  /\.(png|jpe?g|gif|bmp|ico|webp|avif|tiff?|psd|ai|sketch|fig|mp[34]|m4a|wav|ogg|flac|mov|avi|mkv|webm|woff2?|ttf|otf|eot|zip|gz|tgz|bz2|xz|zst|7z|rar|jar|war|ear|nupkg|whl|egg|exe|dll|so|dylib|a|lib|o|obj|pdb|class|pyc|pyo|wasm|db|sqlite3?|mdb|accdb|pdf|docx?|xlsx?|pptx?|odt|bin|dat|lockb|map)$/,
  /(^|\/)(package-lock\.json|npm-shrinkwrap\.json|yarn\.lock|pnpm-lock\.yaml|bun\.lock|composer\.lock|cargo\.lock|gemfile\.lock|poetry\.lock|pipfile\.lock|go\.sum|packages\.lock\.json|flake\.lock)$/,
  /\.min\.(js|mjs|css)$/,
  /(^|\/)(node_modules|vendor|dist|\.yarn)\//,
];

function normalized(path: string): string {
  return path.replaceAll("\\", "/").toLowerCase();
}

export function isDenied(path: string): boolean {
  const p = normalized(path);
  const base = p.slice(p.lastIndexOf("/") + 1);
  if (base === ".env" || base.endsWith(".env")) return !/\.(example|sample|template)\.env$/.test(base);
  if (base.startsWith(".env.")) return !/^\.env\.(example|sample|template|dist|defaults)$/.test(base);
  return DENY.some((pattern) => pattern.test(p));
}

export function isNoise(path: string): boolean {
  const p = normalized(path);
  return NOISE.some((pattern) => pattern.test(p));
}

export type Access = { ok: true; real: string; root: string } | { ok: false; reason: "missing" | "outside" | "denied" };

/**
 * Resolves the file actually opened (symlinks, Windows short names and stream suffixes expand here) and applies the
 * containment and deny rules to that real path - relative to its root and absolute - rather than to the requested name.
 */
export async function access(abs: string, roots: readonly string[]): Promise<Access> {
  let real: string;
  try {
    real = await realpath(abs);
  } catch {
    return { ok: false, reason: "missing" };
  }
  const root = roots.find((candidate) => contains(candidate, real));
  if (root === undefined) return { ok: false, reason: "outside" };
  if (isDenied(real) || isDenied(relative(root, real))) return { ok: false, reason: "denied" };
  return { ok: true, real, root };
}

/** Reads a UTF-8 text file; null when it is missing, a directory, binary, or over the size cap. */
export async function readText(abs: string, explicit: boolean): Promise<string | null> {
  try {
    const info = await stat(abs);
    const cap = explicit ? LIMITS.MAX_EXPLICIT_FILE_BYTES : LIMITS.MAX_FILE_BYTES;
    if (!info.isFile() || info.size > cap) return null;
    const handle = await open(abs, "r");
    try {
      const bytes = new Uint8Array(info.size);
      const { bytesRead } = await handle.read(bytes, 0, info.size, 0);
      const data = bytes.subarray(0, bytesRead);
      if (data.subarray(0, 8000).includes(0)) return null;
      return new TextDecoder("utf-8").decode(data);
    } finally {
      await handle.close();
    }
  } catch {
    return null;
  }
}

export type SafeRead = { text: string; real: string } | { text: null; reason: "missing" | "outside" | "denied" | "unreadable" };

/** `access` then `readText` on the resolved real path. */
export async function readSafe(abs: string, explicit: boolean, roots: readonly string[]): Promise<SafeRead> {
  const checked = await access(abs, roots);
  if (!checked.ok) return { text: null, reason: checked.reason };
  const text = await readText(checked.real, explicit);
  return text === null ? { text: null, reason: "unreadable" } : { text, real: checked.real };
}

// Redaction patterns run on whole files before chunking, so each one must stay linear: every pattern either starts
// with a lookbehind that rejects positions inside a run or has bounded quantifiers.
const PEM_BEGIN = /-----BEGIN [A-Z0-9 ]{0,40}PRIVATE KEY(?: BLOCK)?-----/g;
const PEM_END = /-----END [A-Z0-9 ]{0,40}PRIVATE KEY(?: BLOCK)?-----/g;
const PEM_BODY_LINE = /\r?\n(?:[A-Za-z0-9+/=]{16,}|[A-Za-z-]{3,20}: [^\r\n]{0,200}|)(?=\r?\n|$)/y;
const TOKENS: RegExp[] = [
  /(?<![A-Za-z0-9_])gh[pousr]_[A-Za-z0-9]{36,255}/g,
  /(?<![A-Za-z0-9_])github_pat_[A-Za-z0-9_]{40,255}/g,
  /(?<![A-Za-z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Za-z0-9])/g,
  /(?<![A-Za-z0-9_-])xox[abprs]-[A-Za-z0-9-]{10,255}/g,
  /(?<![A-Za-z0-9_])[sr]k_(?:live|test)_[A-Za-z0-9]{16,255}/g,
  /(?<![A-Za-z0-9_-])AIza[0-9A-Za-z_-]{35}(?![0-9A-Za-z_-])/g,
  /(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{8,4096}\.[A-Za-z0-9_-]{8,8192}\.[A-Za-z0-9_-]{8,4096}/g,
  /(?<![A-Za-z0-9_-])sk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,255}/g,
  /(?<![A-Za-z0-9_])ATATT[A-Za-z0-9_=-]{20,512}/g,
  /(?<![A-Za-z0-9_-])glpat-[A-Za-z0-9_-]{20,255}/g,
  /(?<![A-Za-z0-9_])npm_[A-Za-z0-9]{36}(?![A-Za-z0-9])/g,
];
// `<keyword><suffix> <op> <quote?><value>`, e.g. `SECRET_KEY = '...'`, `DB_PASSWORD=...`, `"apiKey": "..."`.
const ASSIGNMENT = new RegExp(
  "((?:api[_-]?key|apikey|secret|token|passw(?:or)?d|passphrase|pwd|access[_-]?key|account[_-]?key|client[_-]?secret|" +
    "private[_-]?key|auth[_-]?token|(?<![a-z0-9])pat(?![a-z0-9]))[a-z0-9_.-]{0,24}[\"']?[ \\t]{0,8}(?::=|=>|:|=)[ \\t]{0,8})" +
    "([\"'`]?)([^\\s\"'`,;]{8,512})",
  "gi",
);
const AUTH_HEADER = /(?<![A-Za-z0-9_])((?:bearer|basic|token)[ \t]{1,8})([A-Za-z0-9._~+/=-]{16,2048})/gi;
const URL_CREDENTIALS = /(?<![a-z0-9+.-])([a-z][a-z0-9+.-]{0,31}:\/\/[^\s:@/]{1,256}:)([^\s@/]{3,256})(@)/gi;

/** A configuration value that reads like a literal credential rather than code, a reference or a placeholder. */
function looksSecret(value: string): boolean {
  if (value.length < 8 || value.includes("[REDACTED]")) return false;
  if (/^[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)+$/.test(value)) return false;
  if (/[()[\]{}<>]|^\$|^%|\$\{|^\*+$|^x+$/i.test(value)) return false;
  if (/^(?:[a-z][a-z0-9+.-]*:\/\/|\.{0,2}\/|~\/)/i.test(value)) return false;
  if (!/[A-Za-z]/.test(value)) return false;
  return /[0-9]/.test(value) || (value.length >= 12 && /[^A-Za-z0-9]/.test(value));
}

function looksToken(value: string): boolean {
  return /[0-9]/.test(value) || value.endsWith("=") || (/[a-z]/.test(value) && /[A-Z]/.test(value));
}

function blank(text: string): string {
  return text.replace(/[^\r\n]+/g, "[REDACTED]");
}

/** Private key blocks; a BEGIN without END (truncated input) redacts the base64 lines that follow it. */
function redactPem(text: string): { text: string; count: number } {
  let out = "";
  let last = 0;
  let count = 0;
  let endsRemain = true;
  PEM_BEGIN.lastIndex = 0;
  for (let begin = PEM_BEGIN.exec(text); begin !== null; begin = PEM_BEGIN.exec(text)) {
    let stop = begin.index + begin[0].length;
    let end: RegExpExecArray | null = null;
    if (endsRemain) {
      PEM_END.lastIndex = stop;
      end = PEM_END.exec(text);
      endsRemain = end !== null;
    }
    if (end) {
      stop = end.index + end[0].length;
    } else {
      PEM_BODY_LINE.lastIndex = stop;
      while (PEM_BODY_LINE.exec(text) !== null) stop = PEM_BODY_LINE.lastIndex;
    }
    out += text.slice(last, begin.index) + blank(text.slice(begin.index, stop));
    last = stop;
    count++;
    PEM_BEGIN.lastIndex = stop;
  }
  return { text: count > 0 ? out + text.slice(last) : text, count };
}

/** Replaces likely secrets with [REDACTED], keeping line structure so line numbers stay valid. */
export function redactText(text: string, extra: readonly string[] = []): { text: string; count: number } {
  const pem = redactPem(text);
  let count = pem.count;
  let out = pem.text;
  for (const pattern of TOKENS) {
    out = out.replace(pattern, () => {
      count++;
      return "[REDACTED]";
    });
  }
  out = out.replace(ASSIGNMENT, (match, prefix: string, quote: string, value: string) => {
    if (!looksSecret(value)) return match;
    count++;
    return `${prefix}${quote}[REDACTED]`;
  });
  out = out.replace(AUTH_HEADER, (match, prefix: string, value: string) => {
    if (!looksToken(value)) return match;
    count++;
    return `${prefix}[REDACTED]`;
  });
  out = out.replace(URL_CREDENTIALS, (_match, prefix: string, _secret: string, at: string) => {
    count++;
    return `${prefix}[REDACTED]${at}`;
  });
  for (const secret of extra) {
    if (secret.length < 8 || !out.includes(secret)) continue;
    const parts = out.split(secret);
    count += parts.length - 1;
    out = parts.join("[REDACTED]");
  }
  return { text: out, count };
}

export async function mapLimit<T, R>(items: readonly T[], limit: number, fn: (item: T, index: number) => Promise<R>): Promise<R[]> {
  const results: R[] = new Array(items.length);
  let next = 0;
  const worker = async () => {
    while (next < items.length) {
      const index = next++;
      results[index] = await fn(items[index] as T, index);
    }
  };
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker));
  return results;
}
