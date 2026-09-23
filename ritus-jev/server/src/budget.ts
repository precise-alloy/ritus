import { BUDGET } from "./policy.ts";
import { ToolError, type Block } from "./types.ts";

export function estimateTokens(text: string): number {
  return Math.ceil(text.length / BUDGET.CHARS_PER_TOKEN);
}

/**
 * Tokens `text` takes as a JSON string value, which is how state is sent and measured before each request. Quotes,
 * backslashes, newlines and control characters grow when escaped, so packing by raw length would overfill requests.
 */
export function jsonTokens(text: string): number {
  return estimateTokens(JSON.stringify(text));
}

/** How a block appears inside Jev state: its location header, then its text. */
export function blockLabel(block: Block): string {
  if (block.kind === "inline") return block.text;
  return `${block.path}:${block.start}-${block.end}\n${block.text}`;
}

export function blockTokens(block: Block): number {
  return jsonTokens(blockLabel(block)) + BUDGET.BLOCK_OVERHEAD_TOKENS;
}

const TRUNCATED = "\n[truncated]";

/** Shortens `text` so that, with a truncation marker, it takes at most `maxTokens` as a JSON string value. */
export function clipTokens(text: string, maxTokens: number): string {
  const maxChars = Math.floor(maxTokens * BUDGET.CHARS_PER_TOKEN);
  if (JSON.stringify(text).length <= maxChars) return text;
  let end = Math.min(text.length, maxChars);
  for (;;) {
    let cut = text.slice(0, end);
    if (/[\uD800-\uDBFF]$/.test(cut)) cut = cut.slice(0, -1);
    const size = JSON.stringify(cut + TRUNCATED).length;
    if (size <= maxChars || cut.length === 0) return cut + TRUNCATED;
    end = Math.min(cut.length - 1, Math.floor((cut.length * maxChars) / size));
  }
}

/** Greedy in-order packing (keeps file locality) under a token budget and a count cap. */
export function packBy<T>(items: readonly T[], size: (item: T) => number, budget: number, maxCount: number): T[][] {
  const batches: T[][] = [];
  let batch: T[] = [];
  let used = 0;
  for (const item of items) {
    const cost = size(item);
    if (batch.length > 0 && (used + cost > budget || batch.length >= maxCount)) {
      batches.push(batch);
      batch = [];
      used = 0;
    }
    batch.push(item);
    used += cost;
  }
  if (batch.length > 0) batches.push(batch);
  return batches;
}

export function questionTokens(questions: Record<string, unknown>): { total: number; longest: number; count: number } {
  let total = 0;
  let longest = 0;
  let count = 0;
  for (const question of Object.values(questions)) {
    const size = estimateTokens(JSON.stringify(question));
    total += size;
    longest = Math.max(longest, size);
    count++;
  }
  return { total, longest, count };
}

export function fitsRequest(stateTokens: number, questions: Record<string, unknown>): boolean {
  const q = questionTokens(questions);
  return q.count <= BUDGET.QUESTIONS_PER_REQUEST &&
    stateTokens + q.longest <= BUDGET.STATE_PLUS_QUESTION_TOKENS &&
    stateTokens + q.total <= BUDGET.REQUEST_TOKENS;
}

/** Splits question groups into as few requests as the budget allows; each group stays together and must fit alone. */
export function groupQuestions<G>(groups: readonly G[], build: (group: G) => Record<string, unknown>, stateTokens: number): G[][] {
  const requests: G[][] = [];
  let current: G[] = [];
  let merged: Record<string, unknown> = {};
  for (const group of groups) {
    const own = build(group);
    if (!fitsRequest(stateTokens, own)) {
      throw new ToolError("input_error", "One question set exceeds Jev's request budget (about 32k tokens of state plus the longest question).",
        "Shorten `context`, the claims or the label descriptions, narrow the evidence or items, or split the call.");
    }
    const next = { ...merged, ...own };
    if (current.length > 0 && !fitsRequest(stateTokens, next)) {
      requests.push(current);
      current = [group];
      merged = own;
    } else {
      current.push(group);
      merged = next;
    }
  }
  if (current.length > 0) requests.push(current);
  return requests;
}

/**
 * Tokens available for packed evidence or items: the state target, reduced so the longest question still fits
 * beside it, minus fixed state such as `context` or the query.
 */
export function packBudget(longestQuestionTokens: number, fixedStateTokens: number): number {
  const budget = Math.min(BUDGET.STATE_TOKENS, BUDGET.STATE_PLUS_QUESTION_TOKENS - longestQuestionTokens) - fixedStateTokens;
  if (budget < BUDGET.MIN_PACK_TOKENS) {
    throw new ToolError("input_error", "The fixed parts of the request (context, question and labels) leave too little room for evidence.",
      "Shorten `context`, the question or the label descriptions.");
  }
  return budget;
}

export function padId(prefix: string, index: number, total: number): string {
  return `${prefix}${String(index + 1).padStart(Math.max(2, String(total).length), "0")}`;
}
