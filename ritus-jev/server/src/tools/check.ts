import type { ChoiceResponse, JsonValue, Questions } from "@typesafe-ai/sdk";
import { choiceOf, noulOf, probability } from "../answers.ts";
import { blockLabel, blockTokens, estimateTokens, groupQuestions, jsonTokens, packBudget, packBy, padId } from "../budget.ts";
import { evaluate } from "../jev.ts";
import { BUDGET, CHECK, claimVerdict, type Verdict } from "../policy.ts";
import { checkQuestions } from "../questions.ts";
import { round, withJev, type Prepared } from "../run.ts";
import { resolveRefs, type SourceRef } from "../sources.ts";
import { ToolError, type Block, type ToolContext, type ToolResult } from "../types.ts";
import { breakdown, truncateLines } from "./locate.ts";

export interface CheckInput {
  workspace: string;
  claims: string[];
  evidence?: SourceRef[];
  context?: string;
  include_evidence?: boolean;
}

interface Judgment {
  index: number;
  supported: number;
  contradicted: number;
  cited: Block | null;
}

function evidenceState(context: string | undefined, ids: readonly string[], blocks: readonly Block[]): Record<string, JsonValue> {
  const evidence: Record<string, string> = {};
  ids.forEach((id, index) => {
    evidence[id] = blockLabel(blocks[index] as Block);
  });
  return context ? { task: context, evidence } : { evidence };
}

function citation(where: ChoiceResponse, ids: readonly string[], blocks: readonly Block[]): Block | null {
  if (where.choice === "none" || probability(where, where.choice) < CHECK.CITE_MIN) return null;
  const index = ids.indexOf(where.choice);
  return index >= 0 ? (blocks[index] ?? null) : null;
}

/** Asks where/supported/contradicted for each claim against one evidence set, splitting claims across requests to fit. */
async function judge(p: Prepared, claims: readonly string[], indexes: readonly number[], context: string | undefined, blocks: readonly Block[]) {
  const ids = blocks.map((_, index) => padId("E", index, blocks.length));
  const state = evidenceState(context, ids, blocks);
  const build = (i: number): Questions => ({
    [`w${i}`]: checkQuestions.where(claims[i] as string, ids),
    [`s${i}`]: checkQuestions.supported(claims[i] as string),
    [`c${i}`]: checkQuestions.contradicted(claims[i] as string),
  });
  const groups = groupQuestions(indexes, build, estimateTokens(JSON.stringify(state)));
  const judged = await Promise.all(groups.map(async (group) => {
    const questions: Questions = Object.assign({}, ...group.map(build));
    const result = await evaluate(p.call, state, questions);
    return group.map((i): Judgment => ({
      index: i,
      supported: noulOf(result.answers, `s${i}`),
      contradicted: noulOf(result.answers, `c${i}`),
      cited: citation(choiceOf(result.answers, `w${i}`), ids, blocks),
    }));
  }));
  return judged.flat();
}

/** Large evidence: shortlist blocks per claim with Choice skims, then judge each claim on its own shortlist. */
async function judgeLarge(p: Prepared, claims: readonly string[], context: string | undefined, blocks: readonly Block[], budget: number) {
  const indexes = claims.map((_, index) => index);
  const shortlists = new Map<number, { block: Block; prior: number }[]>(indexes.map((i) => [i, []]));
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
          if (prior >= CHECK.SHORTLIST_MIN_PROB) shortlists.get(i)?.push({ block, prior });
        });
      }
    }
  }));
  const judged = await Promise.all(indexes.map(async (i): Promise<Judgment> => {
    const ranked = (shortlists.get(i) ?? []).sort((a, b) => b.prior - a.prior).slice(0, CHECK.SHORTLIST).map((entry) => entry.block);
    const shortlist = packBy(ranked, blockTokens, budget, CHECK.SHORTLIST)[0] ?? [];
    if (shortlist.length === 0) return { index: i, supported: 0, contradicted: 0, cited: null };
    const [single] = await judge(p, claims, [i], context, shortlist);
    return single as Judgment;
  }));
  return judged;
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
    const { blocks, redactions } = await resolveRefs(p.ws, input.evidence ?? [{ diff: {} }], "blocks", p.secrets);
    if (blocks.length === 0) {
      throw new ToolError("input_error", "No evidence to check: the diff is empty or the references resolved to nothing.",
        "Pass `evidence` with file paths, or a diff `base`/`head`.");
    }
    const total = blocks.reduce((sum, block) => sum + blockTokens(block), 0);
    if (total > CHECK.SCOPE_TOKENS) {
      return {
        status: "scope_too_large",
        error: `About ${Math.round(total / 1000)}k tokens of evidence (limit ${CHECK.SCOPE_TOKENS / 1000}k).`,
        hint: "Narrow `evidence`: pass `diff.paths`, specific files or line ranges.",
        breakdown: breakdown(blocks),
      };
    }
    const sampleIds = Array.from({ length: Math.min(blocks.length, BUDGET.CHOICE_OPTIONS) }, (_, i) => padId("E", i, BUDGET.CHOICE_OPTIONS));
    const longestQuestion = Math.max(...claims.flatMap((claim) =>
      [checkQuestions.where(claim, sampleIds), checkQuestions.supported(claim), checkQuestions.contradicted(claim)]
        .map((question) => estimateTokens(JSON.stringify(question)))));
    const budget = packBudget(longestQuestion, jsonTokens(context ?? "") + BUDGET.BLOCK_OVERHEAD_TOKENS);
    const fitsOne = total <= budget && blocks.length <= BUDGET.CHOICE_OPTIONS;
    const judgments = fitsOne
      ? await judge(p, claims, claims.map((_, index) => index), context, blocks)
      : await judgeLarge(p, claims, context, blocks, budget);

    const includeEvidence = input.include_evidence ?? true;
    let linesLeft = CHECK.EVIDENCE_TOTAL_MAX_LINES;
    const results = judgments.sort((a, b) => a.index - b.index).map((judgment) => {
      const verdict: Verdict = claimVerdict(judgment.supported, judgment.contradicted);
      const cited = verdict === "not_found" ? null : judgment.cited;
      let text: string | undefined;
      if (includeEvidence && cited && linesLeft > 0) {
        text = truncateLines(cited.text, Math.min(CHECK.EVIDENCE_MAX_LINES, linesLeft));
        linesLeft -= text.split("\n").length;
      }
      return {
        claim: claims[judgment.index],
        verdict,
        supported: round(judgment.supported),
        contradicted: round(judgment.contradicted),
        evidence: cited ? `${cited.path}:${cited.start}-${cited.end}` : null,
        ...(text !== undefined ? { text } : {}),
      };
    });
    return {
      status: "ok",
      results,
      note: "Leads, not proof: confirm each verdict at its cited lines before asserting it.",
      scanned: { blocks: blocks.length, mode: fitsOne ? "single" : "two_stage" },
      ...(redactions > 0 ? { redactions } : {}),
    };
  });
}
