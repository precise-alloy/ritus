import { join } from "node:path";
import { chunkText } from "./chunk.ts";
import type { Workspace } from "./config.ts";
import { isDenied, isNoise, readSafe, redactText } from "./files.ts";
import { assertRef, git, splitNul } from "./git.ts";
import { CHUNK, LIMITS } from "./policy.ts";
import { ToolError, type Block } from "./types.ts";

export interface DiffSpec {
  base?: string;
  head?: string;
  staged?: boolean;
  paths?: string[];
}

/** One hunk of a file: `path` is the post-image path (pre-image for deletions); `oldPath` is null for new files. */
export interface ParsedHunk {
  path: string;
  oldPath: string | null;
  deleted: boolean;
  header: string;
  newStart: number;
  /** Marker-prefixed lines (" ", "-", "+", "\"). */
  lines: string[];
}

// Pin the output format regardless of user git config (mnemonic/no prefixes, blank context lines, quoting) and
// treat caller paths literally (no pathspec magic such as `:(top)` or globs).
const GIT_DIFF_CONFIG = [
  "-c", "core.quotePath=false",
  "-c", "diff.mnemonicPrefix=false",
  "-c", "diff.noprefix=false",
  "-c", "diff.suppressBlankEmpty=false",
  "--literal-pathspecs",
];

function clip(line: string): string {
  return line.length > LIMITS.MAX_LINE_CHARS ? `${line.slice(0, LIMITS.MAX_LINE_CHARS)} ...` : line;
}

function cleanPath(raw: string, prefix: string): string | null {
  let path = raw.replace(/\t$/, "");
  if (path === "/dev/null") return null;
  if (path.startsWith('"') && path.endsWith('"')) path = path.slice(1, -1).replace(/\\(["\\])/g, "$1");
  return path.startsWith(prefix) ? path.slice(prefix.length) : path;
}

export function parseUnifiedDiff(text: string): ParsedHunk[] {
  const hunks: ParsedHunk[] = [];
  let oldPath: string | null = null;
  let newPath: string | null = null;
  let inFile = false;
  let hunk: { header: string; newStart: number; lines: string[] } | null = null;
  let oldLeft = 0;
  let newLeft = 0;
  const flush = () => {
    const path = newPath ?? oldPath;
    if (hunk && path) hunks.push({ path, oldPath, deleted: newPath === null, ...hunk });
    hunk = null;
  };
  for (const rawLine of text.split("\n")) {
    const line = rawLine.endsWith("\r") ? rawLine.slice(0, -1) : rawLine;
    if (hunk !== null) {
      const marker = line[0];
      if ((oldLeft > 0 || newLeft > 0) && (marker === " " || marker === "-" || marker === "+" || line === "")) {
        // An empty line inside a hunk is a blank context line (git's diff.suppressBlankEmpty form).
        const entry = line === "" ? " " : line;
        if (entry[0] !== "+") oldLeft--;
        if (entry[0] !== "-") newLeft--;
        hunk.lines.push(entry);
        continue;
      }
      if (marker === "\\") {
        hunk.lines.push(line);
        continue;
      }
      flush();
    }
    if (line.startsWith("diff ")) {
      flush();
      // Combined (merge) diffs use a different hunk format; skip them.
      inFile = line.startsWith("diff --git ");
      oldPath = null;
      newPath = null;
      continue;
    }
    if (!inFile) continue;
    const header = /^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$/.exec(line);
    if (header) {
      hunk = { header: line, newStart: Number(header[3]), lines: [] };
      oldLeft = header[2] === undefined ? 1 : Number(header[2]);
      newLeft = header[4] === undefined ? 1 : Number(header[4]);
      continue;
    }
    if (line.startsWith("--- ")) oldPath = cleanPath(line.slice(4), "a/");
    else if (line.startsWith("+++ ")) newPath = cleanPath(line.slice(4), "b/");
  }
  flush();
  return hunks;
}

/** Splits one hunk into slices of at most CHUNK.MAX_LINES lines, each labelled with its new-file line range. */
export function sliceHunk(hunk: ParsedHunk): Block[] {
  const blocks: Block[] = [];
  const prefix = hunk.deleted ? "deleted file " : "";
  let line = hunk.newStart;
  for (let i = 0; i < hunk.lines.length; i += CHUNK.MAX_LINES) {
    const slice = hunk.lines.slice(i, i + CHUNK.MAX_LINES);
    const start = Math.max(1, line);
    for (const entry of slice) if (entry.startsWith(" ") || entry.startsWith("+")) line++;
    const end = Math.max(start, line - 1);
    const header = i === 0 ? `${prefix}${hunk.header}` : `${prefix}${hunk.header} (continued)`;
    blocks.push({ path: hunk.path, start, end, text: `${header}\n${slice.map(clip).join("\n")}`, kind: "hunk" });
  }
  return blocks;
}

/** Redacts a whole hunk at once (a key block may span slices) while keeping each line's diff marker. */
function redactHunk(hunk: ParsedHunk, secrets: readonly string[]): { hunk: ParsedHunk; count: number } {
  const redacted = redactText(hunk.lines.map((line) => line.slice(1)).join("\n"), secrets);
  if (redacted.count === 0) return { hunk, count: 0 };
  const content = redacted.text.split("\n");
  return { hunk: { ...hunk, lines: hunk.lines.map((line, i) => `${line[0] ?? " "}${content[i] ?? ""}`) }, count: redacted.count };
}

/** Read-only `git diff` as redacted hunk blocks; working-tree mode also includes untracked files as new-file blocks. */
export async function diffBlocks(
  ws: Workspace,
  spec: DiffSpec,
  relPaths: readonly string[],
  secrets: readonly string[],
): Promise<{ blocks: Block[]; redactions: number }> {
  if (!ws.gitTop) throw new ToolError("input_error", "Diff evidence needs a git repository.", "Pass file `path` evidence instead.");
  const args = [
    ...GIT_DIFF_CONFIG, "diff", "--no-color", "--no-ext-diff", "--no-textconv", "--unified=3", "--relative",
    "--src-prefix=a/", "--dst-prefix=b/",
  ];
  if (spec.staged) {
    args.push("--cached");
    if (spec.base) args.push(assertRef(spec.base, "diff.base"));
  } else if (spec.head) {
    args.push(`${assertRef(spec.base ?? "HEAD", "diff.base")}...${assertRef(spec.head, "diff.head")}`);
  } else {
    args.push(assertRef(spec.base ?? "HEAD", "diff.base"));
  }
  args.push("--", ...relPaths);
  const result = await git(ws.root, args);
  if (result.code !== 0) throw new ToolError("input_error", `git diff failed: ${result.stderr.slice(0, 300)}`);
  const explicit = new Set(relPaths);
  const keep = (path: string) => !isDenied(path) && (explicit.has(path) || !isNoise(path));
  const blocks: Block[] = [];
  let redactions = 0;
  for (const parsed of parseUnifiedDiff(new TextDecoder().decode(result.stdout))) {
    if (!keep(parsed.path) || (parsed.oldPath !== null && isDenied(parsed.oldPath))) continue;
    const { hunk, count } = redactHunk(parsed, secrets);
    redactions += count;
    blocks.push(...sliceHunk(hunk));
  }

  if (!spec.staged && !spec.head) {
    const untracked = await git(ws.root, ["--literal-pathspecs", "ls-files", "-z", "--others", "--exclude-standard", "--", ...relPaths]);
    if (untracked.code === 0) {
      let total = 0;
      for (const path of splitNul(untracked.stdout)) {
        if (!keep(path)) continue;
        const read = await readSafe(join(ws.root, path), explicit.has(path), [ws.root]);
        if (read.text === null) continue;
        total += read.text.length;
        if (total > LIMITS.MAX_READ_BYTES) {
          throw new ToolError("scope_too_large", "Untracked files in the diff exceed the read limit.",
            "Pass `diff.paths` to limit the diff, or ignore generated files.");
        }
        const redacted = redactText(read.text, secrets);
        redactions += redacted.count;
        for (const chunk of chunkText(path, redacted.text)) {
          const body = chunk.text.split("\n").map((line) => `+${line}`).join("\n");
          blocks.push({ ...chunk, text: `new file (untracked)\n${body}`, kind: "hunk" });
        }
      }
    }
  }
  return { blocks, redactions };
}
