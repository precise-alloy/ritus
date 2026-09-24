import type { JsonValue, Questions } from "@typesafe-ai/sdk";
import { isAbsolute } from "node:path";
import { choiceOf, noulOf, probability } from "../answers.ts";
import { blockLabel, blockTokens, estimateTokens, groupQuestions, jsonTokens, packBudget, packBy, padId } from "../budget.ts";
import { truncateLines } from "../chunk.ts";
import { redactText } from "../files.ts";
import { evaluate } from "../jev.ts";
import { IS_WINDOWS } from "../paths.ts";
import { BUDGET, CHECK, type Verdict } from "../policy.ts";
import { checkQuestions } from "../questions.ts";
import { round, withJev, type Prepared } from "../run.ts";
import { filesInDir, findPhrase, listFiles, namedPaths, resolveRefs, type NamedPaths, type PhraseHit, type SourceRef } from "../sources.ts";
import { ToolError, type Block, type ToolContext, type ToolResult } from "../types.ts";
import { breakdown } from "./locate.ts";

export interface CheckInput {
  workspace: string;
  claims: string[];
  evidence?: SourceRef[];
  context?: string;
  include_evidence?: boolean | "auto" | "all" | "none";
}

type Kind = "semantic" | "literal" | "count" | "files" | "format";

interface Route {
  kind: Kind;
  compound: boolean;
  absent: boolean;
  fileForm: "only_these" | "includes" | "excludes";
}

interface Outcome {
  verdict: Verdict;
  method: "jev" | "code" | "none";
  confidence?: number;
  cited?: Block;
  hits?: PhraseHit[];
  detail?: string;
  hint?: string;
}

const KINDS = new Set<string>(["semantic", "literal", "count", "files", "format"]);
const fold = (path: string): string => (IS_WINDOWS ? path.toLowerCase() : path);
const normalize = (path: string): string => fold(path.replaceAll("\\", "/").replace(/^(\.\/)+/, "").replace(/\/+$/, ""));
const cite = (block: Block): string => `${block.path}:${block.start}-${block.end}`;

/** Phrases a claim quotes in backticks, double quotes or single quotes. */
export function quotedPhrases(claim: string): string[] {
  const phrases: string[] = [];
  for (const pattern of [/`([^`\n]{2,200})`/g, /"([^"\n]{2,200})"/g, /“([^”\n]{2,200})”/g, /(?<!\w)'([^'\n]{3,200})'(?!\w)/g]) {
    for (const match of claim.matchAll(pattern)) {
      const phrase = (match[1] as string).trim();
      if (phrase && !phrases.includes(phrase)) phrases.push(phrase);
    }
  }
  return phrases;
}

type Comparison = { op: "eq" | "ge" | "le" | "gt" | "lt"; n: number };
const NUMBERS: Record<string, number> = {
  zero: 0, none: 0, one: 1, single: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10,
};
const NUMBER = "(\\d+|zero|none|one|single|two|three|four|five|six|seven|eight|nine|ten)";

/** The count a claim asserts ("exactly one", "at least 2", "no matches"), or null when it cannot be read reliably. */
export function assertedCount(claim: string): Comparison | null {
  const text = claim.toLowerCase();
  const value = (token: string): number | null => (/^\d+$/.test(token) ? Number(token) : (NUMBERS[token] ?? null));
  const compared = new RegExp(`\\b(exactly|only|precisely|at least|no fewer than|no less than|at most|no more than|more than|fewer than|less than)\\s+(?:a\\s+)?${NUMBER}\\b`).exec(text);
  if (compared) {
    const n = value(compared[2] as string);
    if (n === null) return null;
    const word = compared[1] as string;
    const op = ["at least", "no fewer than", "no less than"].includes(word) ? "ge"
      : ["at most", "no more than"].includes(word) ? "le"
      : word === "more than" ? "gt"
      : ["fewer than", "less than"].includes(word) ? "lt"
      : "eq";
    return { op, n };
  }
  if (/\bno (?:matches|occurrences|instances|results|hits)\b/.test(text)) return { op: "eq", n: 0 };
  const counted = new RegExp(`\\b${NUMBER}\\s+(?:\\S+\\s+){0,4}?(?:occurrences?|matches|match|times?|headings?|sections?|lines?|entries|entry|instances?|references?|items?|tests?|files?)\\b`).exec(text);
  if (!counted) return null;
  const n = value(counted[1] as string);
  return n === null ? null : { op: "eq", n };
}

function holds(actual: number, expected: Comparison): boolean {
  switch (expected.op) {
    case "ge":
      return actual >= expected.n;
    case "le":
      return actual <= expected.n;
    case "gt":
      return actual > expected.n;
    case "lt":
      return actual < expected.n;
    default:
      return actual === expected.n;
  }
}

/** One small request: what kind of statement each claim is, plus the details code needs for exact checks. */
async function route(p: Prepared, claims: readonly string[]): Promise<Route[]> {
  const ids = claims.map((_, i) => padId("C", i, claims.length));
  const state: Record<string, JsonValue> = { claims: Object.fromEntries(ids.map((id, i) => [id, claims[i] as string])) };
  const build = (i: number): Questions => ({
    [`k${i}`]: checkQuestions.kind(ids[i] as string),
    [`x${i}`]: checkQuestions.compound(ids[i] as string),
    [`p${i}`]: checkQuestions.polarity(ids[i] as string),
    [`f${i}`]: checkQuestions.fileForm(ids[i] as string),
  });
  const routes: Route[] = [];
  const groups = groupQuestions(claims.map((_, i) => i), build, estimateTokens(JSON.stringify(state)));
  await Promise.all(groups.map(async (group) => {
    const result = await evaluate(p.call, state, Object.assign({}, ...group.map(build)) as Questions);
    for (const i of group) {
      const kind = choiceOf(result.answers, `k${i}`);
      routes[i] = {
        kind: kind.confidence >= CHECK.ROUTE_ACCEPT && KINDS.has(kind.choice) ? (kind.choice as Kind) : "semantic",
        compound: noulOf(result.answers, `x${i}`) >= CHECK.COMPOUND,
        absent: choiceOf(result.answers, `p${i}`).choice === "absent",
        fileForm: choiceOf(result.answers, `f${i}`).choice as Route["fileForm"],
      };
    }
  }));
  return routes;
}

const USE_SEARCH = {
  scope: "Name the files or directory to search in the claim, or pass them as `evidence`.",
  count: "Counts are checked exactly only for one quoted phrase and a stated number (for example \"exactly one\"); otherwise count with rg -c.",
  format: "Formatting and character rules are exact: check them with a search, for example rg -n on the changed files.",
  files: "Pass diff evidence, or list the changed files with git diff --name-only.",
  filesNamed: "Name the files in the claim to compare them with the changed files.",
};

function literal(route: Route, found: { phrase: string; count: number; hits: PhraseHit[] }[], scopeSize: number): Outcome {
  const where = `${scopeSize} file${scopeSize === 1 ? "" : "s"}`;
  if (route.absent) {
    const present = found.filter((entry) => entry.count > 0);
    if (present.length === 0) return { verdict: "supported", method: "code", detail: `No occurrences in ${where}.` };
    return {
      verdict: "contradicted",
      method: "code",
      hits: present.flatMap((entry) => entry.hits),
      detail: present.map((entry) => `"${entry.phrase}" occurs ${entry.count} time${entry.count === 1 ? "" : "s"}`).join("; ") + ` in ${where}.`,
    };
  }
  const missing = found.filter((entry) => entry.count === 0);
  if (missing.length === 0) {
    return { verdict: "supported", method: "code", hits: found.flatMap((entry) => entry.hits), detail: `Found in ${where}.` };
  }
  return { verdict: "contradicted", method: "code", detail: `Not found in ${where}: ${missing.map((entry) => `"${entry.phrase}"`).join(", ")}.` };
}

function files(route: Route, named: NamedPaths, changed: readonly string[]): Outcome {
  const namedFiles = new Set(named.files.map(normalize));
  const dirs = named.dirs.map((dir) => `${normalize(dir)}/`);
  if (namedFiles.size === 0 && dirs.length === 0) return { verdict: "use_search", method: "none", hint: USE_SEARCH.filesNamed };
  const isNamed = (path: string) => namedFiles.has(normalize(path)) || dirs.some((dir) => normalize(path).startsWith(dir));
  const list = (paths: readonly string[]) => `${paths.slice(0, 10).join(", ")}${paths.length > 10 ? ` and ${paths.length - 10} more` : ""}`;
  if (route.fileForm === "only_these") {
    const extra = changed.filter((path) => !isNamed(path));
    return extra.length === 0
      ? { verdict: "supported", method: "code", detail: `Changed: ${changed.length > 0 ? list(changed) : "nothing"}.` }
      : { verdict: "contradicted", method: "code", detail: `Also changed: ${list(extra)}.` };
  }
  const changedSet = new Set(changed.map(normalize));
  const touched = (target: string, isDir: boolean) =>
    isDir ? changed.some((path) => normalize(path).startsWith(`${normalize(target)}/`)) : changedSet.has(normalize(target));
  const targets = [...named.files.map((path) => ({ path, isDir: false })), ...named.dirs.map((path) => ({ path, isDir: true }))];
  if (route.fileForm === "excludes") {
    const hit = targets.filter((target) => touched(target.path, target.isDir)).map((target) => target.path);
    return hit.length === 0
      ? { verdict: "supported", method: "code", detail: "None of the named files changed." }
      : { verdict: "contradicted", method: "code", detail: `Changed: ${list(hit)}.` };
  }
  const untouched = targets.filter((target) => !touched(target.path, target.isDir)).map((target) => target.path);
  return untouched.length === 0
    ? { verdict: "supported", method: "code", detail: "Every named file changed." }
    : { verdict: "contradicted", method: "code", detail: `Not changed: ${list(untouched)}.` };
}

function evidenceState(context: string | undefined, ids: readonly string[], blocks: readonly Block[]): Record<string, JsonValue> {
  const evidence: Record<string, string> = {};
  ids.forEach((id, index) => {
    evidence[id] = blockLabel(blocks[index] as Block);
  });
  return context ? { task: context, evidence } : { evidence };
}

/** Per semantic claim, the few evidence blocks most related to it (Choice skims over batches of the evidence). */
async function shortlist(p: Prepared, claims: readonly string[], indexes: readonly number[], context: string | undefined, blocks: readonly Block[]) {
  const sampleIds = Array.from({ length: Math.min(blocks.length, BUDGET.CHOICE_OPTIONS) }, (_, i) => padId("E", i, BUDGET.CHOICE_OPTIONS));
  const longest = Math.max(...indexes.map((i) => estimateTokens(JSON.stringify(checkQuestions.where(claims[i] as string, sampleIds)))));
  const budget = packBudget(longest, jsonTokens(context ?? "") + BUDGET.BLOCK_OVERHEAD_TOKENS);
  const found = new Map<number, { block: Block; prior: number }[]>(indexes.map((i) => [i, []]));
  const batches = packBy(blocks, blockTokens, budget, BUDGET.CHOICE_OPTIONS);
  await Promise.all(batches.map(async (batch) => {
    const ids = batch.map((_, index) => padId("E", index, batch.length));
    const state = evidenceState(context, ids, batch);
    const build = (i: number): Questions => ({ [`w${i}`]: checkQuestions.where(claims[i] as string, ids) });
    for (const group of groupQuestions(indexes, build, estimateTokens(JSON.stringify(state)))) {
      const result = await evaluate(p.call, state, Object.assign({}, ...group.map(build)) as Questions);
      for (const i of group) {
        const where = choiceOf(result.answers, `w${i}`);
        batch.forEach((block, index) => {
          const prior = probability(where, ids[index] as string);
          if (prior >= CHECK.SHORTLIST_MIN_PROB) found.get(i)?.push({ block, prior });
        });
      }
    }
  }));
  const lists = new Map<number, Block[]>();
  for (const [i, entries] of found) {
    const ranked = entries.sort((a, b) => b.prior - a.prior).slice(0, CHECK.SHORTLIST).map((entry) => entry.block);
    lists.set(i, packBy(ranked, blockTokens, budget, CHECK.SHORTLIST)[0] ?? []);
  }
  return lists;
}

/** Citation-check shape: one small request per claim, one relation Choice per shortlisted passage. */
async function relate(p: Prepared, claim: string, context: string | undefined, passages: readonly Block[]): Promise<Outcome> {
  if (passages.length === 0) return { verdict: "not_found", method: "jev" };
  const ids = passages.map((_, k) => `P${k + 1}`);
  const state: Record<string, JsonValue> = {
    claim,
    passages: Object.fromEntries(ids.map((id, k) => [id, blockLabel(passages[k] as Block)])),
    ...(context ? { task: context } : {}),
  };
  const questions: Questions = Object.fromEntries(ids.map((id, k) => [`r${k}`, checkQuestions.relation(`passages.${id}`)]));
  const result = await evaluate(p.call, state, questions);
  const judged = passages.map((block, k) => {
    const answer = choiceOf(result.answers, `r${k}`);
    return { block, relation: answer.choice, confidence: answer.confidence };
  });
  const strong = (relation: string) =>
    judged.filter((entry) => entry.relation === relation && entry.confidence >= CHECK.ACCEPT).sort((a, b) => b.confidence - a.confidence);
  const supports = strong("supports");
  const contradicts = strong("contradicts");
  if (supports[0] && contradicts[0]) {
    return {
      verdict: "uncertain",
      method: "jev",
      cited: contradicts[0].block,
      hint: `The evidence disagrees: ${cite(supports[0].block)} supports the claim and ${cite(contradicts[0].block)} contradicts it.`,
    };
  }
  if (contradicts[0]) return { verdict: "contradicted", method: "jev", confidence: contradicts[0].confidence, cited: contradicts[0].block };
  if (supports[0]) return { verdict: "supported", method: "jev", confidence: supports[0].confidence, cited: supports[0].block };
  if (judged.every((entry) => entry.relation === "says_nothing" && entry.confidence >= CHECK.ACCEPT)) return { verdict: "not_found", method: "jev" };
  const lead = judged.filter((entry) => entry.relation !== "says_nothing").sort((a, b) => b.confidence - a.confidence)[0] ?? judged[0];
  return { verdict: "uncertain", method: "jev", ...(lead ? { confidence: lead.confidence, cited: lead.block } : {}) };
}

export async function check(input: CheckInput, ctx: ToolContext): Promise<ToolResult> {
  return withJev(input.workspace, ctx, async (p) => {
    const claims = input.claims.map((claim) => claim.trim()).filter(Boolean);
    if (claims.length === 0 || claims.length > CHECK.MAX_CLAIMS || claims.some((claim) => claim.length > 600)) {
      throw new ToolError("input_error", `Provide 1-${CHECK.MAX_CLAIMS} non-empty claims of at most 600 characters.`);
    }
    const context = input.context?.trim() || undefined;
    if ((context?.length ?? 0) > BUDGET.CONTEXT_CHARS) {
      throw new ToolError("input_error", `\`context\` is limited to ${BUDGET.CONTEXT_CHARS} characters; summarize it.`);
    }
    if ((input.evidence?.length ?? 0) > 50) throw new ToolError("input_error", "Pass at most 50 `evidence` entries.");

    const refs = input.evidence ?? [{ diff: {} }];
    const resolved = await resolveRefs(p.ws, refs, "blocks", p.secrets);
    const blocks = [...resolved.blocks];
    const warnings = [...resolved.warnings];
    let redactions = resolved.redactions;

    let listing: Promise<string[]> | null = null;
    const list = () => (listing ??= listFiles(p.ws));
    const named = await Promise.all(claims.map((claim) => namedPaths(p.ws, claim, list)));
    const inEvidence = new Set(blocks.filter((block) => block.kind !== "inline").map((block) => normalize(block.path)));
    const namedMissing = [...new Map(named.flatMap((entry) => entry.files).map((path) => [normalize(path), path])).values()]
      .filter((path) => !inEvidence.has(normalize(path)));
    const added: string[] = [];
    if (namedMissing.length > 0 && input.evidence === undefined) {
      for (const path of namedMissing.slice(0, CHECK.NAMED_FILES_MAX)) {
        try {
          const extra = await resolveRefs(p.ws, [{ path }], "blocks", p.secrets);
          blocks.push(...extra.blocks);
          redactions += extra.redactions;
          added.push(path);
        } catch (error) {
          if (!(error instanceof ToolError)) throw error;
        }
      }
    } else if (namedMissing.length > 0) {
      warnings.push(`Claims name files that are not in \`evidence\`: ${namedMissing.join(", ")}. Add them as {"path": ...} evidence to check what they say.`);
    }

    const routes = await route(p, claims);
    const phrasesOf = claims.map((claim, index) => {
      const namedHere = named[index] as NamedPaths;
      return quotedPhrases(claim).filter((phrase) =>
        !namedHere.files.some((path) => normalize(path) === normalize(phrase)) && !namedHere.dirs.some((dir) => normalize(dir) === normalize(phrase)));
    });
    // A literal claim with nothing quoted cannot be searched exactly: judge it on meaning and say how to make it exact.
    const quoteHint = new Set<number>();
    for (const [index, entry] of routes.entries()) {
      if (entry.kind === "literal" && (phrasesOf[index] as string[]).length === 0) {
        entry.kind = "semantic";
        quoteHint.add(index);
      }
    }
    const semantic = routes.flatMap((entry, index) => (entry.kind === "semantic" ? [index] : []));
    if (semantic.length === claims.length && blocks.length === 0) {
      throw new ToolError("input_error", "No evidence to check: the diff is empty or the references resolved to nothing.",
        warnings[0] ?? "Pass `evidence` with file paths, or a diff `base`.");
    }
    if (semantic.length > 0 && blocks.length > 0) {
      const total = blocks.reduce((sum, block) => sum + blockTokens(block), 0);
      if (total > CHECK.SCOPE_TOKENS) {
        return {
          status: "scope_too_large",
          error: `About ${Math.round(total / 1000)}k tokens of evidence (limit ${CHECK.SCOPE_TOKENS / 1000}k).`,
          hint: "Narrow `evidence`: pass `diff.paths`, specific files or line ranges.",
          breakdown: breakdown(blocks),
        };
      }
    }

    const outcomes = new Map<number, Outcome>();
    const hasDiff = refs.some((ref) => ref.diff !== undefined);
    const changed = [...new Map(blocks.filter((block) => block.kind === "hunk").map((block) => [normalize(block.path), block.path])).values()];
    const evidenceFiles = [...new Map(blocks.filter((block) => block.kind !== "inline" && !isAbsolute(block.path)).map((block) => [normalize(block.path), block.path])).values()];
    for (const [index, entry] of routes.entries()) {
      if (entry.kind === "semantic") continue;
      if (entry.kind === "format") {
        outcomes.set(index, { verdict: "use_search", method: "none", hint: USE_SEARCH.format });
        continue;
      }
      if (entry.kind === "files") {
        outcomes.set(index, hasDiff ? files(entry, named[index] as NamedPaths, changed) : { verdict: "use_search", method: "none", hint: USE_SEARCH.files });
        continue;
      }
      const namedHere = named[index] as NamedPaths;
      const phrases = phrasesOf[index] as string[];
      const scope = new Map<string, string>();
      for (const path of namedHere.files) scope.set(normalize(path), path);
      for (const dir of namedHere.dirs) for (const path of await filesInDir(p.ws, dir, list)) scope.set(normalize(path), path);
      if (scope.size === 0) for (const path of evidenceFiles) scope.set(normalize(path), path);
      const scopeFiles = [...scope.values()].slice(0, CHECK.LITERAL_FILES_MAX);
      if (entry.kind === "count" && phrases.length !== 1) {
        outcomes.set(index, { verdict: "use_search", method: "none", hint: USE_SEARCH.count });
        continue;
      }
      if (scopeFiles.length === 0) {
        outcomes.set(index, { verdict: "use_search", method: "none", hint: USE_SEARCH.scope });
        continue;
      }
      if (entry.kind === "count") {
        const expected = assertedCount(claims[index] as string);
        if (!expected) {
          outcomes.set(index, { verdict: "use_search", method: "none", hint: USE_SEARCH.count });
          continue;
        }
        const found = await findPhrase(p.ws, phrases[0] as string, scopeFiles);
        const ok = holds(found.count, expected);
        outcomes.set(index, {
          verdict: ok ? "supported" : "contradicted",
          method: "code",
          hits: found.hits,
          detail: `"${phrases[0]}" occurs ${found.count} time${found.count === 1 ? "" : "s"} in ${scopeFiles.length} file${scopeFiles.length === 1 ? "" : "s"}.`,
        });
        continue;
      }
      const found = [];
      for (const phrase of phrases) found.push({ phrase, ...(await findPhrase(p.ws, phrase, scopeFiles)) });
      outcomes.set(index, literal(entry, found, scopeFiles.length));
    }

    if (semantic.length > 0 && blocks.length > 0) {
      const lists = await shortlist(p, claims, semantic, context, blocks);
      await Promise.all(semantic.map(async (index) => {
        outcomes.set(index, await relate(p, claims[index] as string, context, lists.get(index) ?? []));
      }));
    }
    for (const index of semantic) {
      if (!outcomes.has(index)) outcomes.set(index, { verdict: "not_found", method: "none", hint: "No evidence to check this claim against." });
    }

    const mode = input.include_evidence === true ? "all" : input.include_evidence === false ? "none" : (input.include_evidence ?? "auto");
    let linesLeft = CHECK.EXCERPT_TOTAL_LINES;
    const results = claims.map((claim, index) => {
      const outcome = outcomes.get(index) as Outcome;
      const routeHint = routes[index]?.compound && outcome.method === "jev"
        ? "This claim combines several assertions; split it into one claim each for a reliable verdict."
        : undefined;
      const exactHint = quoteHint.has(index) ? "Quote the exact phrase in backticks to have it checked exactly." : undefined;
      const hint = [outcome.hint, routeHint, exactHint].filter(Boolean).join(" ") || undefined;
      const wantsExcerpt = mode === "all" || (mode === "auto" && (outcome.verdict === "contradicted" || outcome.verdict === "uncertain"));
      let excerpt: string | undefined;
      if (wantsExcerpt && linesLeft > 0) {
        if (outcome.cited) {
          excerpt = truncateLines(outcome.cited.text, Math.min(CHECK.EXCERPT_LINES, linesLeft));
        } else if (outcome.hits?.[0] && outcome.verdict === "contradicted") {
          excerpt = outcome.hits.slice(0, 3).map((hit) => `${hit.path}:${hit.line}: ${redactText(hit.text, p.secrets).text}`).join("\n");
        }
        if (excerpt !== undefined) linesLeft -= excerpt.split("\n").length;
      }
      const at = outcome.hits?.slice(0, CHECK.LITERAL_AT_MAX).map((hit) => `${hit.path}:${hit.line}`);
      return {
        claim,
        verdict: outcome.verdict,
        method: outcome.method,
        ...(outcome.confidence !== undefined ? { confidence: round(outcome.confidence) } : {}),
        evidence: outcome.cited ? cite(outcome.cited) : (at?.[0] ?? null),
        ...(at && at.length > 1 ? { at } : {}),
        ...(outcome.detail ? { detail: outcome.detail } : {}),
        ...(hint ? { hint } : {}),
        ...(excerpt !== undefined ? { excerpt } : {}),
      };
    });
    const count = (method: Outcome["method"]) => [...outcomes.values()].filter((outcome) => outcome.method === method).length;
    return {
      status: "ok",
      results,
      note: "Leads, not proof: confirm contradicted and uncertain claims at their cited lines. Method \"code\" verdicts come from exact search.",
      scanned: { blocks: blocks.length, jev: count("jev"), code: count("code"), unchecked: count("none") },
      ...(added.length > 0 ? { added_evidence: added } : {}),
      ...(warnings.length > 0 ? { warnings } : {}),
      ...(redactions > 0 ? { redactions } : {}),
    };
  });
}
