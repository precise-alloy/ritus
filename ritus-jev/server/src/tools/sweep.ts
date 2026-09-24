import type { JsonValue, Questions } from "@typesafe-ai/sdk";
import { isAbsolute, relative } from "node:path";
import { noulOf } from "../answers.ts";
import { blockLabel, blockTokens, estimateTokens, groupQuestions, jsonTokens, packBudget, packBy, padId } from "../budget.ts";
import { describeBlock, sliceWithContext } from "../chunk.ts";
import { evaluate } from "../jev.ts";
import { contains, tempRoots, toPosix } from "../paths.ts";
import { BUDGET, SWEEP } from "../policy.ts";
import { sweepQuestions } from "../questions.ts";
import { round, withJev } from "../run.ts";
import { loadScope, resolveScope } from "../sources.ts";
import { ToolError, type Block, type ToolContext, type ToolResult } from "../types.ts";
import { breakdown, compactSkipped } from "./locate.ts";

export interface SweepInput {
  workspace: string;
  query: string;
  paths?: string[];
  exclude?: string[];
  terms?: string[];
  limit?: number;
}

const STOP = new Set([
  "the", "and", "for", "with", "that", "this", "are", "from", "which", "what", "when", "where", "how", "any", "all",
  "each", "every", "not", "but", "then", "than", "into", "about", "its", "has", "have", "does", "was", "were", "still",
  "describe", "describes", "passage", "passages", "text", "file", "files", "says", "said", "saying", "states", "stating",
]);

/** Crude stem so "dispatched" matches "dispatch" and "workers" matches "worker". */
function stem(word: string): string {
  for (const suffix of ["ing", "ed", "es", "s"]) {
    if (word.length > suffix.length + 3 && word.endsWith(suffix)) return word.slice(0, -suffix.length);
  }
  return word;
}

function queryWords(query: string): string[] {
  return [...new Set((query.toLowerCase().match(/[a-z0-9_]{3,}/g) ?? []).filter((word) => !STOP.has(word)).map(stem))];
}

/** The line of a hit that shares the most words with the query - a pointer inside a block of up to 60 lines. */
function bestLine(block: Block, words: readonly string[]): { line: number; text: string } {
  const wanted = new Set(words);
  const lines = block.text.split("\n");
  let best = -1;
  let bestScore = 0;
  lines.forEach((line, index) => {
    const present = new Set((line.toLowerCase().match(/[a-z0-9_]{3,}/g) ?? []).map(stem).filter((word) => wanted.has(word)));
    if (present.size > bestScore) {
      best = index;
      bestScore = present.size;
    }
  });
  if (best < 0) best = Math.max(0, lines.findIndex((line) => line.trim() !== ""));
  const text = (lines[best] ?? "").trim();
  return { line: block.start + best, text: text.length > 120 ? `${text.slice(0, 117)}...` : text };
}

/** Globs for one `exclude` entry; a plain path also excludes everything under it. */
function excludeGlobs(workspace: string, raw: string): InstanceType<typeof Bun.Glob>[] {
  const trimmed = raw.trim();
  const rel = isAbsolute(trimmed) && contains(workspace, trimmed) ? toPosix(relative(workspace, trimmed)) : trimmed.replaceAll("\\", "/");
  const clean = rel.replace(/^(\.\/)+/, "").replace(/\/+$/, "");
  if (!clean) return [];
  return /[*?[\]{}]/.test(clean) ? [new Bun.Glob(clean)] : [new Bun.Glob(clean), new Bun.Glob(`${clean}/**`)];
}

export async function sweep(input: SweepInput, ctx: ToolContext): Promise<ToolResult> {
  return withJev(input.workspace, ctx, async (p) => {
    const query = input.query?.trim() ?? "";
    if (query.length < 3 || query.length > 600) throw new ToolError("input_error", "`query` must be 3-600 characters.");
    if ((input.paths?.length ?? 0) > 50 || (input.exclude?.length ?? 0) > 50 || (input.terms?.length ?? 0) > 20) {
      throw new ToolError("input_error", "Pass at most 50 `paths`, 50 `exclude` patterns and 20 `terms`.");
    }
    const limit = Math.min(Math.max(1, Math.floor(input.limit ?? SWEEP.DEFAULT_LIMIT)), SWEEP.MAX_LIMIT);
    const scope = await resolveScope(p.ws, input.paths);
    const excludes = (input.exclude ?? []).flatMap((pattern) => excludeGlobs(p.ws.root, pattern));
    const before = scope.files.length;
    scope.files = scope.files.filter((file) => !excludes.some((glob) => glob.match(file.display)));
    const excluded = before - scope.files.length;
    const { loaded, unreadable, denied } = await loadScope(scope, p.secrets, [p.ws.root, ...tempRoots()]);
    const files = new Map(loaded.map((entry) => [entry.file.display, entry]));
    let blocks = loaded.flatMap((entry) => entry.blocks);
    const redactions = loaded.reduce((sum, entry) => sum + entry.redactions, 0);
    const skipped = { ...scope.skipped, denied: scope.skipped.denied + denied, unreadable };
    const scanned = { files: loaded.length, blocks: blocks.length, ...(excluded > 0 ? { excluded } : {}), ...compactSkipped(skipped) };

    const needles = (input.terms ?? []).map((term) => term.trim().toLowerCase()).filter((term) => term.length >= 2);
    if (needles.length > 0) {
      blocks = blocks.filter((block) => {
        const haystack = `${block.path}\n${block.text}`.toLowerCase();
        return needles.some((needle) => haystack.includes(needle));
      });
    }
    if (blocks.length === 0) {
      const hint = loaded.length === 0 ? "No readable text files in scope." : "No block contains any of `terms`; change or drop them.";
      return { status: "ok", exists: false, count: 0, hits: [], scanned, hint };
    }
    const total = blocks.reduce((sum, block) => sum + blockTokens(block), 0);
    if (total > SWEEP.SCOPE_TOKENS) {
      return {
        status: "scope_too_large",
        error: `About ${Math.round(total / 1000)}k tokens in scope (limit ${SWEEP.SCOPE_TOKENS / 1000}k).`,
        hint: "Narrow `paths`, add `exclude` patterns for archives such as old task files, or add `terms`.",
        breakdown: breakdown(blocks),
        scanned,
      };
    }

    // Screen: one Noul per block, many blocks per request (recall-oriented threshold).
    const questionTokens = estimateTokens(JSON.stringify(sweepQuestions.block(padId("B", 0, SWEEP.BATCH_BLOCKS))));
    const budget = packBudget(questionTokens, jsonTokens(query) + BUDGET.BLOCK_OVERHEAD_TOKENS);
    const batches = packBy(blocks, blockTokens, budget, SWEEP.BATCH_BLOCKS);
    const screened: { block: Block; prior: number }[] = [];
    await Promise.all(batches.map(async (batch) => {
      const ids = batch.map((_, index) => padId("B", index, batch.length));
      const state: Record<string, JsonValue> = {
        query,
        blocks: Object.fromEntries(ids.map((id, index) => [id, blockLabel(batch[index] as Block)])),
      };
      const build = (index: number): Questions => ({ [`m${index}`]: sweepQuestions.block(ids[index] as string) });
      for (const group of groupQuestions(batch.map((_, index) => index), build, estimateTokens(JSON.stringify(state)))) {
        const result = await evaluate(p.call, state, Object.assign({}, ...group.map(build)) as Questions);
        for (const index of group) {
          const prior = noulOf(result.answers, `m${index}`);
          if (prior >= SWEEP.SCREEN) screened.push({ block: batch[index] as Block, prior });
        }
      }
    }));

    // Confirm: each screened block alone, with a few lines of context (re-rank shape).
    screened.sort((a, b) => b.prior - a.prior);
    const toConfirm = screened.slice(0, SWEEP.MAX_CONFIRM);
    const confirmed = await Promise.all(toConfirm.map(async ({ block }) => {
      const lines = files.get(block.path)?.lines;
      const passage = lines ? { ...block, ...sliceWithContext(lines, block.start, block.end, SWEEP.CONTEXT_LINES) } : block;
      const result = await evaluate(p.call, { query, passage: blockLabel(passage) }, { match: sweepQuestions.passage() });
      return { block, score: noulOf(result.answers, "match") };
    }));
    const matches = confirmed.filter((entry) => entry.score >= SWEEP.MATCH);
    const shown = [...matches].sort((a, b) => b.score - a.score).slice(0, limit)
      .sort((a, b) => a.block.path.localeCompare(b.block.path) || a.block.start - b.block.start);
    const words = queryWords(query);
    const hits = shown.map(({ block, score }) => {
      const pointer = bestLine(block, words);
      const section = block.kind === "doc" ? describeBlock(block, files.get(block.path)?.lines) : "";
      return {
        path: block.path,
        lines: `${block.start}-${block.end}`,
        score: round(score),
        line: pointer.line,
        excerpt: pointer.text,
        ...(section && section !== pointer.text ? { section: section.length > 80 ? `${section.slice(0, 77)}...` : section } : {}),
      };
    });
    const unconfirmed = screened.length - toConfirm.length;
    return {
      status: "ok",
      exists: matches.length > 0,
      count: matches.length,
      hits,
      ...(matches.length > hits.length ? { more: matches.length - hits.length } : {}),
      ...(unconfirmed > 0
        ? { unconfirmed, hint: "More blocks passed the screen than one call re-checks; narrow `paths` or add `exclude` or `terms` to see them all." }
        : {}),
      note: "Every passage above the threshold is listed in file order; read each hit before changing it.",
      scanned: { ...scanned, searched: blocks.length, screened: screened.length, confirmed: toConfirm.length },
      ...(redactions > 0 ? { redactions } : {}),
    };
  });
}
