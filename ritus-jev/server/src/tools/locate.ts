import type { Questions } from "@typesafe-ai/sdk";
import { choiceOf, noulOf, probability } from "../answers.ts";
import { blockLabel, blockTokens, packBy, padId } from "../budget.ts";
import { describeBlock, sliceWithContext, truncateLines } from "../chunk.ts";
import { evaluate } from "../jev.ts";
import { BUDGET, CHUNK, foundVerdict, LOCATE } from "../policy.ts";
import { tempRoots } from "../paths.ts";
import { locateQuestions } from "../questions.ts";
import { round, withJev, type Prepared } from "../run.ts";
import { loadScope, resolveScope, type LoadedFile } from "../sources.ts";
import { ToolError, type Block, type ToolContext, type ToolResult } from "../types.ts";

export interface LocateInput {
  workspace: string;
  query: string;
  paths?: string[];
  terms?: string[];
  limit?: number;
  include_text?: "none" | "top" | "all";
}

interface Candidate {
  block: Block;
  prior: number;
  score: number;
}

/** True when a query lists several topics; one behavior per query ranks better. */
export function bundlesTopics(query: string): boolean {
  const separators = (query.match(/,|;|\band\b|\bor\b/gi) ?? []).length;
  return query.length > 80 && separators >= 3;
}

export function breakdown(blocks: readonly Block[]) {
  const dirs = new Map<string, { files: Set<string>; tokens: number }>();
  for (const block of blocks) {
    const parts = block.path.split("/").slice(0, -1);
    const dir = parts.length === 0 ? "." : parts.slice(0, 2).join("/");
    const entry = dirs.get(dir) ?? { files: new Set<string>(), tokens: 0 };
    entry.files.add(block.path);
    entry.tokens += blockTokens(block);
    dirs.set(dir, entry);
  }
  return [...dirs.entries()]
    .sort((a, b) => b[1].tokens - a[1].tokens)
    .slice(0, LOCATE.BREAKDOWN_DIRS)
    .map(([dir, entry]) => ({ dir, files: entry.files.size, tokens_k: Math.round(entry.tokens / 1000) }));
}

function blockMap(ids: readonly string[], blocks: readonly Block[]): Record<string, string> {
  const map: Record<string, string> = {};
  ids.forEach((id, index) => {
    map[id] = blockLabel(blocks[index] as Block);
  });
  return map;
}

/** Everything fits one request: a relative Choice plus one absolute Noul per block, one round trip. */
async function singleRequest(p: Prepared, query: string, blocks: readonly Block[]): Promise<Candidate[]> {
  const ids = blocks.map((_, index) => padId("B", index, blocks.length));
  const questions: Questions = { best: locateQuestions.best(ids) };
  ids.forEach((id, index) => {
    questions[`m${index}`] = locateQuestions.block(id);
  });
  const result = await evaluate(p.call, { query, blocks: blockMap(ids, blocks) }, questions);
  const best = choiceOf(result.answers, "best");
  return blocks.map((block, index) => ({
    block,
    prior: probability(best, ids[index] as string),
    score: noulOf(result.answers, `m${index}`),
  }));
}

/** Skim every batch with a Choice, then re-check each shortlisted block alone with a Noul. */
async function twoStage(p: Prepared, query: string, blocks: readonly Block[], files: ReadonlyMap<string, LoadedFile>, limit: number) {
  const batches = packBy(blocks, blockTokens, BUDGET.STATE_TOKENS, BUDGET.CHOICE_OPTIONS);
  const perBatch = await Promise.all(batches.map(async (batch) => {
    const ids = batch.map((_, index) => padId("B", index, batch.length));
    const result = await evaluate(p.call, { query, blocks: blockMap(ids, batch) }, { best: locateQuestions.best(ids) });
    const best = choiceOf(result.answers, "best");
    const scored = batch
      .map((block, index) => ({ block, prior: probability(best, ids[index] as string), score: 0 }))
      .sort((a, b) => b.prior - a.prior);
    const floor = Math.max(LOCATE.SHORTLIST_MIN_PROB, LOCATE.SHORTLIST_RELATIVE * (scored[0]?.prior ?? 0));
    return scored.filter((candidate) => candidate.prior >= floor).slice(0, LOCATE.SHORTLIST_PER_BATCH);
  }));

  // Priors are relative within a batch, so every batch's leader gets a slot before the rest compete.
  const cap = Math.min(LOCATE.MAX_CANDIDATES, Math.max(limit * 2, 8));
  const leaders = perBatch.flatMap((list) => list.slice(0, 1)).sort((a, b) => b.prior - a.prior).slice(0, cap);
  const rest = perBatch.flatMap((list) => list.slice(1)).sort((a, b) => b.prior - a.prior);
  const shortlist = [...leaders, ...rest].slice(0, cap);

  return Promise.all(shortlist.map(async (candidate): Promise<Candidate> => {
    const lines = files.get(candidate.block.path)?.lines;
    const block: Block = lines
      ? { ...candidate.block, ...sliceWithContext(lines, candidate.block.start, candidate.block.end, CHUNK.CONTEXT_LINES) }
      : candidate.block;
    const result = await evaluate(p.call, { query, candidate: blockLabel(block) }, { match: locateQuestions.candidate() });
    return { block, prior: candidate.prior, score: noulOf(result.answers, "match") };
  }));
}

export async function locate(input: LocateInput, ctx: ToolContext): Promise<ToolResult> {
  return withJev(input.workspace, ctx, async (p) => {
    const query = input.query?.trim() ?? "";
    if (query.length < 3 || query.length > 600) throw new ToolError("input_error", "`query` must be 3-600 characters.");
    if ((input.paths?.length ?? 0) > 50 || (input.terms?.length ?? 0) > 20) {
      throw new ToolError("input_error", "Pass at most 50 `paths` and 20 `terms`.");
    }
    const limit = Math.min(Math.max(1, Math.floor(input.limit ?? LOCATE.DEFAULT_LIMIT)), LOCATE.MAX_LIMIT);
    const scope = await resolveScope(p.ws, input.paths);
    const { loaded, unreadable, denied } = await loadScope(scope, p.secrets, [p.ws.root, ...tempRoots()]);
    const files = new Map(loaded.map((entry) => [entry.file.display, entry]));
    let blocks = loaded.flatMap((entry) => entry.blocks);
    const redactions = loaded.reduce((sum, entry) => sum + entry.redactions, 0);
    const skipped = { ...scope.skipped, denied: scope.skipped.denied + denied, unreadable };
    const scanned = { files: loaded.length, blocks: blocks.length, ...compactSkipped(skipped) };

    const needles = (input.terms ?? []).map((term) => term.trim().toLowerCase()).filter((term) => term.length >= 2);
    if (needles.length > 0) {
      blocks = blocks.filter((block) => {
        const haystack = `${block.path}\n${block.text}`.toLowerCase();
        return needles.some((needle) => haystack.includes(needle));
      });
    }
    if (blocks.length === 0) {
      const hint = loaded.length === 0
        ? scope.skipped.missing.length > 0 ? `Nothing matched: ${scope.skipped.missing.join(", ")}` : "No readable text files in scope."
        : "No block contains any of `terms`; change or drop them.";
      return { status: "ok", found: "not_found", results: [], scanned, hint };
    }

    const total = blocks.reduce((sum, block) => sum + blockTokens(block), 0);
    if (total > LOCATE.SCOPE_TOKENS) {
      return {
        status: "scope_too_large",
        error: `About ${Math.round(total / 1000)}k tokens in scope (limit ${LOCATE.SCOPE_TOKENS / 1000}k).`,
        hint: "Narrow `paths` to the relevant directories below, or add `terms` to prefilter.",
        breakdown: breakdown(blocks),
        scanned,
      };
    }

    const single = blocks.length <= LOCATE.SINGLE_REQUEST_MAX_BLOCKS && total <= BUDGET.STATE_TOKENS;
    const candidates = single ? await singleRequest(p, query, blocks) : await twoStage(p, query, blocks, files, limit);
    const ranking = candidates.sort((a, b) => b.score - a.score || b.prior - a.prior);
    const found = foundVerdict(ranking[0]?.score ?? 0);
    let results = ranking.filter((candidate) => candidate.score >= LOCATE.MIN_SCORE).slice(0, limit);
    const closest = results.length === 0 && ranking[0] ? [ranking[0]] : [];
    results = results.length > 0 ? results : closest;

    const mode = input.include_text ?? "top";
    let budget = LOCATE.TEXT_ALL_MAX_LINES;
    let withText = 0;
    const shaped = results.map((candidate) => {
      let text: string | undefined;
      if (mode === "top" && candidate.score >= LOCATE.FOUND && withText < LOCATE.TEXT_TOP) {
        text = truncateLines(candidate.block.text, LOCATE.TEXT_MAX_LINES);
        withText++;
      } else if (mode === "all" && budget > 0) {
        text = truncateLines(candidate.block.text, Math.min(LOCATE.TEXT_MAX_LINES, budget));
        budget -= text.split("\n").length;
      }
      return {
        path: candidate.block.path,
        lines: `${candidate.block.start}-${candidate.block.end}`,
        score: round(candidate.score),
        preview: describeBlock(candidate.block, files.get(candidate.block.path)?.lines),
        ...(text !== undefined ? { text } : {}),
      };
    });

    return {
      status: "ok",
      found,
      results: shaped,
      ...(closest.length > 0 ? { note: "Nothing in scope clearly addresses the query; the closest block is shown." } : {}),
      scanned: { ...scanned, searched: blocks.length, mode: single ? "single" : "two_stage" },
      ...(bundlesTopics(query)
        ? { warnings: ["The query bundles several topics; one behavior per query ranks better - run separate queries in parallel."] }
        : {}),
      ...(redactions > 0 ? { redactions } : {}),
    };
  });
}

export function compactSkipped(skipped: { denied: number; noise: number; missing: string[]; unreadable: number }) {
  const out: Record<string, number | string[]> = {};
  if (skipped.denied) out.denied = skipped.denied;
  if (skipped.noise) out.noise = skipped.noise;
  if (skipped.unreadable) out.unreadable = skipped.unreadable;
  if (skipped.missing.length) out.missing = skipped.missing;
  return Object.keys(out).length > 0 ? { skipped: out } : {};
}
