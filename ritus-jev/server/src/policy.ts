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
  SUPPORTED: 0.75,
  SUPPORTED_MAX_CONTRADICTED: 0.35,
  CONTRADICTED: 0.7,
  CONTRADICTED_MAX_SUPPORTED: 0.5,
  NOT_FOUND_MAX: 0.3,
  /** Minimum `where` probability for a citation. */
  CITE_MIN: 0.3,
  SHORTLIST: 4,
  SHORTLIST_MIN_PROB: 0.05,
  EVIDENCE_MAX_LINES: 40,
  EVIDENCE_TOTAL_MAX_LINES: 240,
} as const;

export const CLASSIFY = {
  MAX_ITEMS: 200,
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
export type Verdict = "supported" | "contradicted" | "not_found" | "uncertain";

export function foundVerdict(topScore: number): Found {
  if (topScore >= LOCATE.FOUND) return "found";
  return topScore >= LOCATE.PARTIAL ? "partial" : "not_found";
}

/** Supported and contradicted are separate Nouls; they are combined here, never assumed to sum to 1. */
export function claimVerdict(supported: number, contradicted: number): Verdict {
  if (supported >= CHECK.SUPPORTED && contradicted < CHECK.SUPPORTED_MAX_CONTRADICTED) return "supported";
  if (contradicted >= CHECK.CONTRADICTED && supported < CHECK.CONTRADICTED_MAX_SUPPORTED) return "contradicted";
  if (supported < CHECK.NOT_FOUND_MAX && contradicted < CHECK.NOT_FOUND_MAX) return "not_found";
  return "uncertain";
}

export function noulBand(p: number): "yes" | "no" | "uncertain" {
  if (p >= ASK.YES) return "yes";
  return p <= ASK.NO ? "no" : "uncertain";
}
