// Every threshold, budget and cap the tools apply. Tune here; question wording lives in questions.ts.
// Starting thresholds follow the TypeSafe cookbooks (semantic find, re-ranking, confidence routing).

export const DEFAULT_MODEL = "jev-1.13.0";

export const BUDGET = {
  /** Conservative characters-per-token estimate for code-heavy text. */
  CHARS_PER_TOKEN: 3.2,
  /** Target state size per request (API limit: 32k tokens for state plus the longest question). */
  STATE_TOKENS: 22_000,
  STATE_PLUS_QUESTION_TOKENS: 30_000,
  /** Whole request (API limit: 64k tokens). */
  REQUEST_TOKENS: 56_000,
  QUESTIONS_PER_REQUEST: 150,
  /** API maximum is 255 options per Choice; one slot is kept for `none`. */
  CHOICE_OPTIONS: 250,
  /** Per-block JSON overhead added to size estimates. */
  BLOCK_OVERHEAD_TOKENS: 8,
  /** Smallest evidence budget worth a request once context and questions are accounted for. */
  MIN_PACK_TOKENS: 4_000,
  /** Maximum `context` length accepted by check and classify. */
  CONTEXT_CHARS: 4_000,
} as const;

export const RESPONSE = {
  /** Serialized size cap for every tool result; hosts truncate or divert larger outputs (Copilot CLI at about 20 KB). */
  MAX_BYTES: 15_000,
} as const;

export const LIMITS = {
  MAX_FILE_BYTES: 512 * 1024,
  MAX_EXPLICIT_FILE_BYTES: 2 * 1024 * 1024,
  MAX_FILES: 6_000,
  MAX_READ_BYTES: 24 * 1024 * 1024,
  MAX_DIFF_BYTES: 16 * 1024 * 1024,
  MAX_LINE_CHARS: 400,
  READ_CONCURRENCY: 16,
  REQUEST_CONCURRENCY: 6,
  REQUEST_TIMEOUT_MS: 15_000,
  MAX_RETRIES: 2,
  TOOL_DEADLINE_MS: 45_000,
  GIT_TIMEOUT_MS: 20_000,
  CACHE_ENTRIES: 256,
  CACHE_TTL_MS: 10 * 60_000,
} as const;

export const CHUNK = {
  /** A declaration (code) or heading (docs) starts a new block once the current one has this many lines. */
  UNIT_MIN_LINES: 12,
  DOC_UNIT_MIN_LINES: 6,
  MAX_LINES: 60,
  WINDOW_LINES: 20,
  CONTEXT_LINES: 3,
} as const;

export const LOCATE = {
  DEFAULT_LIMIT: 6,
  MAX_LIMIT: 20,
  /** `found` when the best stage-2 score reaches this; `partial` from PARTIAL. */
  FOUND: 0.7,
  PARTIAL: 0.35,
  /** Results below this score are dropped. */
  MIN_SCORE: 0.2,
  /** Candidate-generation cap for the whole scope, in estimated tokens. */
  SCOPE_TOKENS: 350_000,
  SINGLE_REQUEST_MAX_BLOCKS: 60,
  SHORTLIST_PER_BATCH: 5,
  SHORTLIST_MIN_PROB: 0.02,
  SHORTLIST_RELATIVE: 0.1,
  MAX_CANDIDATES: 18,
  TEXT_TOP: 2,
  TEXT_MAX_LINES: 80,
  TEXT_ALL_MAX_LINES: 240,
  BREAKDOWN_DIRS: 12,
} as const;

export const CHECK = {
  MAX_CLAIMS: 20,
  /** Evidence cap for one call, in estimated tokens; above it the call returns scope_too_large. */
  SCOPE_TOKENS: 300_000,
  /** Claim routing below this confidence falls back to the semantic (evidence) path. */
  ROUTE_ACCEPT: 0.6,
  /** A compound-claim Noul at or above this adds a hint to split the claim. */
  COMPOUND: 0.7,
  /** Relation confidence at which a supports / contradicts / says_nothing verdict stands; below it the claim is uncertain. */
  ACCEPT: 0.7,
  /** Candidate passages judged per semantic claim, and the minimum shortlist probability. */
  SHORTLIST: 4,
  SHORTLIST_MIN_PROB: 0.05,
  /** Excerpts are returned for contradicted and uncertain claims only (unless include_evidence is "all"). */
  EXCERPT_LINES: 20,
  EXCERPT_TOTAL_LINES: 120,
  /** Files named in claims that are added to default evidence. */
  NAMED_FILES_MAX: 5,
  /** Files searched for a literal or counted phrase, and the cited occurrences returned. */
  LITERAL_FILES_MAX: 400,
  LITERAL_AT_MAX: 8,
} as const;

export const SWEEP = {
  /** Scope cap in estimated tokens; above it the call returns scope_too_large with a breakdown. */
  SCOPE_TOKENS: 400_000,
  /** Blocks screened per request (one Noul each). */
  BATCH_BLOCKS: 120,
  /** Screen threshold (recall-oriented); blocks at or above it are re-checked alone. */
  SCREEN: 0.3,
  /** Final threshold on the solo re-check. */
  MATCH: 0.6,
  /** Most screened blocks re-checked in one call; the rest are reported as `more`. */
  MAX_CONFIRM: 80,
  DEFAULT_LIMIT: 30,
  MAX_LIMIT: 100,
  CONTEXT_LINES: 2,
} as const;

export const CLASSIFY = {
  MAX_ITEMS: 120,
  ITEMS_PER_REQUEST: 40,
  MULTI_ITEMS_PER_REQUEST: 16,
  ITEM_MAX_TOKENS: 3_000,
  MAX_LABELS: 64,
  /** Single-label answers at or above this confidence are `accept`, below are `review`. */
  ACCEPT: 0.6,
  /** Multi-label: flagged at or above YES, `review` between REVIEW and YES. */
  MULTI_YES: 0.7,
  MULTI_REVIEW: 0.35,
} as const;

export const ASK = {
  MAX_QUESTIONS: 32,
  YES: 0.7,
  NO: 0.3,
} as const;

export type Found = "found" | "partial" | "not_found";
export type Verdict = "supported" | "contradicted" | "not_found" | "uncertain" | "use_search";

export function foundVerdict(topScore: number): Found {
  if (topScore >= LOCATE.FOUND) return "found";
  return topScore >= LOCATE.PARTIAL ? "partial" : "not_found";
}

export function noulBand(p: number): "yes" | "no" | "uncertain" {
  if (p >= ASK.YES) return "yes";
  return p <= ASK.NO ? "no" : "uncertain";
}
