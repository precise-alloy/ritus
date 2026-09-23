export type Status =
  | "ok"
  | "disabled"
  | "scope_too_large"
  | "rate_limited"
  | "unavailable"
  | "auth_error"
  | "input_error";

export interface Usage {
  requests: number;
  cached: number;
  input_tokens: number;
}

export type BlockKind = "code" | "doc" | "text" | "hunk" | "inline";

/** A contiguous piece of evidence: file lines, a diff hunk slice, or caller-supplied text. */
export interface Block {
  /** Workspace-relative POSIX path, absolute path for temp files, or an inline text id. */
  path: string;
  /** 1-based inclusive line range (1-1 for inline text). */
  start: number;
  end: number;
  text: string;
  kind: BlockKind;
}

export interface ToolResult {
  status: Status;
  [key: string]: unknown;
}

export class ToolError extends Error {
  constructor(
    readonly status: Exclude<Status, "ok">,
    message: string,
    readonly hint?: string,
  ) {
    super(message);
  }
}

export interface ToolContext {
  /** Host workspace roots when the MCP client advertises them, otherwise null. */
  roots(): Promise<readonly string[] | null>;
}
