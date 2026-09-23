import { z } from "zod";

// Lean schemas: every tool schema is sent to the agent on every turn, so size limits are enforced in the tools.

const workspace = z.string().describe("Absolute path of the repository you are working in (your current working directory).");

const source = z
  .object({
    path: z.string().optional().describe("Workspace-relative file (or an absolute file in the OS temp dir)."),
    start_line: z.number().optional(),
    end_line: z.number().optional(),
    text: z.string().optional().describe("Inline text instead of a file."),
    id: z.string().optional().describe("Id for inline text."),
    diff: z
      .object({
        base: z.string().optional().describe("Default HEAD; with head, compares base...head."),
        head: z.string().optional(),
        staged: z.boolean().optional(),
        paths: z.array(z.string()).optional(),
      })
      .strict()
      .optional()
      .describe("Git diff hunks; {} = working tree vs HEAD plus untracked files."),
  })
  .strict()
  .describe("Exactly one of path, text or diff.");

export const locateShape = {
  workspace,
  query: z.string().describe("What you are looking for, in plain English."),
  paths: z.array(z.string()).optional().describe("Files, directories or globs to search (default: whole workspace)."),
  terms: z.array(z.string()).optional().describe("Optional literal keywords; only blocks containing one are searched."),
  limit: z.number().optional().describe("Maximum results (default 6, max 20)."),
  include_text: z.enum(["none", "top", "all"]).optional().describe("Block text to return (default top: confident best hits)."),
};

export const checkShape = {
  workspace,
  claims: z.array(z.string()).describe("1-20 specific, testable statements."),
  evidence: z.array(source).optional().describe("What to check against (default: working-tree diff vs HEAD plus untracked files)."),
  context: z.string().optional().describe("Task or requirement summary, as background."),
  include_evidence: z.boolean().optional().describe("Include the cited lines (default true)."),
};

export const classifyShape = {
  workspace,
  items: z.array(source).optional().describe("Items to classify; each diff hunk becomes an item (default: working-tree diff)."),
  preset: z.enum(["failure_kind", "review_comment", "change_risk", "change_scope"]).optional(),
  labels: z.record(z.string(), z.string()).optional().describe("Custom label -> description map, instead of preset."),
  multi: z.boolean().optional().describe("Custom labels: judge each label independently; the question then needs {label}."),
  question: z.string().optional().describe("Custom labels: the question; {item} marks the item, {label} the label description."),
  context: z.string().optional().describe("What items are judged against (PR intent; required for change_scope)."),
};

export const askShape = {
  workspace,
  state: z.union([z.string(), z.record(z.string(), z.unknown())]).optional().describe("Text or JSON to judge."),
  sources: z.array(source).optional().describe("Added to state as sources.<id>."),
  questions: z
    .record(
      z.string(),
      z
        .object({
          type: z.enum(["noul", "choice", "score"]),
          instructions: z.union([z.string(), z.record(z.string(), z.unknown())]),
          criteria: z.union([z.record(z.string(), z.string().nullable()), z.array(z.string())]).optional(),
        })
        .strict(),
    )
    .describe("id -> question. choice: criteria = option -> description; score: 2-10 ordered levels; noul: optional {true, false}."),
};

export const SHAPES = { locate: locateShape, check: checkShape, classify: classifyShape, ask: askShape } as const;
export type ToolName = keyof typeof SHAPES;
