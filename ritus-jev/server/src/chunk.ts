import { extname } from "node:path";
import { CHUNK, LIMITS } from "./policy.ts";
import type { Block, BlockKind } from "./types.ts";

const CODE_EXT = new Set([
  ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts", ".py", ".cs", ".java", ".kt", ".kts", ".go", ".rs",
  ".rb", ".php", ".swift", ".c", ".h", ".cc", ".cpp", ".hpp", ".scala", ".sh", ".bash", ".zsh", ".ps1", ".psm1",
  ".sql", ".vue", ".svelte", ".lua", ".dart", ".r", ".m", ".fs", ".fsx", ".ex", ".exs", ".erl", ".clj", ".groovy",
  ".gradle", ".tf", ".hcl", ".proto", ".graphql", ".gql", ".css", ".scss", ".sass", ".less", ".html", ".htm", ".xml",
  ".xaml", ".cshtml", ".razor", ".json", ".jsonc", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".properties",
  ".csproj", ".props", ".targets", ".sln", ".dockerfile", ".mk",
]);
const DOC_EXT = new Set([".md", ".mdx", ".markdown", ".rst", ".adoc", ".asciidoc"]);

// Lines that open a code unit: declarations with optional modifiers, top-level bindings, access-modified
// members, decorators/attributes, and test blocks. Local variables and object keys are deliberately excluded.
const DECLARATION = new RegExp(
  "^\\s{0,8}(?:(?:export|public|private|protected|internal|static|async|abstract|override|sealed|partial|virtual|default|pub(?:\\([a-z]+\\))?)\\s+)*" +
    "(?:(?:function\\*?|class|interface|enum|struct|trait|fn|func|def|namespace|record|object|module)\\s+[A-Za-z_$(]" +
    "|impl\\b|type\\s+[A-Za-z_$][\\w$]*\\s*(?:<[^>]*>)?\\s*=|(?:describe|it|test)(?:\\.\\w+)?\\s*\\()" +
    "|^(?:export\\s+)?(?:const|let|var|val)\\s" +
    "|^\\s{0,8}(?:public|private|protected|internal)\\s" +
    "|^\\s{0,8}(?:@[A-Za-z]|\\[[A-Z][A-Za-z]*[(\\]])",
);
const HEADING = /^#{1,6}\s/;

export function blockKind(path: string): BlockKind {
  const name = path.toLowerCase();
  const ext = extname(name);
  if (DOC_EXT.has(ext)) return "doc";
  if (CODE_EXT.has(ext) || /(^|\/)(dockerfile|makefile|jenkinsfile)$/.test(name)) return "code";
  return "text";
}

export function splitLines(text: string): string[] {
  const lines = text.split(/\r?\n/);
  if (lines.length > 1 && lines[lines.length - 1] === "") lines.pop();
  return lines.map((line) => (line.length > LIMITS.MAX_LINE_CHARS ? `${line.slice(0, LIMITS.MAX_LINE_CHARS)} ...` : line));
}

function isBlank(line: string | undefined): boolean {
  return line === undefined || line.trim() === "";
}

/** Paragraph segments [start, end) over line indices: runs of lines separated by blank lines or headings. */
function segments(lines: string[], kind: BlockKind): [number, number][] {
  const result: [number, number][] = [];
  let start = 0;
  for (let i = 1; i <= lines.length; i++) {
    const boundary = i === lines.length || (isBlank(lines[i - 1]) && !isBlank(lines[i])) ||
      (kind === "doc" && HEADING.test(lines[i] ?? ""));
    if (boundary) {
      result.push([start, i]);
      start = i;
    }
  }
  return result;
}

function pack(lines: string[], kind: BlockKind): [number, number][] {
  const ranges: [number, number][] = [];
  let start = -1;
  let end = -1;
  for (const [segStart, segEnd] of segments(lines, kind)) {
    for (let s = segStart; s < segEnd; s += CHUNK.MAX_LINES) {
      const e = Math.min(segEnd, s + CHUNK.MAX_LINES);
      const opensUnit = isAnchor(lines[s], kind);
      if (start >= 0) {
        const size = end - start;
        const unitMin = kind === "doc" ? CHUNK.DOC_UNIT_MIN_LINES : CHUNK.UNIT_MIN_LINES;
        if ((opensUnit && size >= unitMin) || size + (e - s) > CHUNK.MAX_LINES) {
          ranges.push([start, end]);
          start = -1;
        }
      }
      if (start < 0) start = s;
      end = e;
    }
  }
  if (start >= 0) ranges.push([start, end]);
  return ranges;
}

/** Lines that open a unit: declarations in code, headings in docs. */
export function isAnchor(line: string | undefined, kind: BlockKind): boolean {
  if (line === undefined) return false;
  if (kind === "doc") return HEADING.test(line);
  return kind === "code" && DECLARATION.test(line);
}

function indent(line: string): number {
  return line.length - line.trimStart().length;
}

function clip(line: string, max = 120): string {
  const trimmed = line.trim();
  return trimmed.length > max ? `${trimmed.slice(0, max - 3)}...` : trimmed;
}

/**
 * One-line description of a block: its declarations/headings (up to three), else the enclosing one above it
 * (prefixed "in "), else its first non-empty line.
 */
export function describeBlock(block: Block, fileLines?: readonly string[]): string {
  const kind = block.kind === "hunk" || block.kind === "inline" ? blockKind(block.path) : block.kind;
  const own = block.text.split("\n");
  const anchors = own.filter((line) => isAnchor(line, kind));
  if (anchors.length === 1) return clip(anchors[0] as string);
  if (anchors.length > 1) return clip(anchors.slice(0, 3).map((line) => clip(line, 60)).join(" | "), 180);
  const first = own.find((line) => line.trim() !== "") ?? "";
  if (fileLines && kind !== "text") {
    const limit = Math.max(0, block.start - 1 - 300);
    for (let i = block.start - 2; i >= limit; i--) {
      const line = fileLines[i];
      if (line !== undefined && isAnchor(line, kind) && (kind === "doc" || indent(line) <= indent(first))) return `in ${clip(line)}`;
    }
  }
  return clip(first);
}

/** Splits file text into blocks: declaration/heading-aware packs for code and docs, fixed windows for logs and text. */
export function chunkText(path: string, text: string, kind: BlockKind = blockKind(path)): Block[] {
  const lines = splitLines(text);
  const ranges: [number, number][] = [];
  if (kind === "text") {
    for (let s = 0; s < lines.length; s += CHUNK.WINDOW_LINES) ranges.push([s, Math.min(lines.length, s + CHUNK.WINDOW_LINES)]);
  } else {
    ranges.push(...pack(lines, kind));
  }
  const blocks: Block[] = [];
  for (const [s, e] of ranges) {
    const slice = lines.slice(s, e);
    if (slice.every((line) => isBlank(line))) continue;
    blocks.push({ path, start: s + 1, end: e, text: slice.join("\n"), kind });
  }
  return blocks;
}

/** Lines `start..end` (1-based, inclusive) of `lines`, widened by `context` lines on each side. */
export function sliceWithContext(lines: readonly string[], start: number, end: number, context: number) {
  const from = Math.max(1, start - context);
  const to = Math.min(lines.length, end + context);
  return { start: from, end: to, text: lines.slice(from - 1, to).join("\n") };
}
