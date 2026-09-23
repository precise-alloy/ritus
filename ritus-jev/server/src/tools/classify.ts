import type { JsonValue, Questions } from "@typesafe-ai/sdk";
import { choiceOf, noulOf, ranked } from "../answers.ts";
import { clipTokens, estimateTokens, groupQuestions, jsonTokens, packBudget, packBy, padId } from "../budget.ts";
import { evaluate } from "../jev.ts";
import { BUDGET, CLASSIFY } from "../policy.ts";
import { classifyChoice, classifyNoul, CUSTOM_QUESTION, PRESETS, renderQuestion, type PresetName } from "../questions.ts";
import { round, withJev } from "../run.ts";
import { resolveRefs, type SourceRef } from "../sources.ts";
import { ToolError, type Block, type ToolContext, type ToolResult } from "../types.ts";

export interface ClassifyInput {
  workspace: string;
  items?: SourceRef[];
  preset?: PresetName;
  labels?: Record<string, string>;
  multi?: boolean;
  question?: string;
  context?: string;
}

const LABEL = /^[A-Za-z0-9_.:-]{1,48}$/;

function itemId(block: Block): string {
  return block.kind === "inline" ? block.path : `${block.path}:${block.start}-${block.end}`;
}

export async function classify(input: ClassifyInput, ctx: ToolContext): Promise<ToolResult> {
  return withJev(input.workspace, ctx, async (p) => {
    if ((input.preset === undefined) === (input.labels === undefined)) {
      throw new ToolError("input_error", "Pass exactly one of `preset` or `labels`.");
    }
    const preset = input.preset ? PRESETS[input.preset] : undefined;
    const labels = preset?.labels ?? input.labels ?? {};
    const names = Object.keys(labels);
    if (names.length < 2 || names.length > CLASSIFY.MAX_LABELS || names.some((name) => !LABEL.test(name))) {
      throw new ToolError("input_error", `Provide 2-${CLASSIFY.MAX_LABELS} labels named with letters, digits, _ . : or -.`);
    }
    if (Object.values(labels).some((description) => !description.trim() || description.length > 400) || (input.question?.length ?? 0) > 600) {
      throw new ToolError("input_error", "Label descriptions must be 1-400 characters and `question` at most 600.");
    }
    const context = input.context?.trim() || undefined;
    if ((context?.length ?? 0) > BUDGET.CONTEXT_CHARS) {
      throw new ToolError("input_error", `\`context\` is limited to ${BUDGET.CONTEXT_CHARS} characters; summarize it.`);
    }
    if (preset?.needsContext && !context) {
      throw new ToolError("input_error", `Preset ${input.preset} needs \`context\` (the task the items are judged against).`);
    }
    const mode = preset?.mode ?? (input.multi ? "multi" : "single");
    const template = preset?.question ?? input.question?.trim() ?? CUSTOM_QUESTION[mode];
    if (mode === "multi" && !template.includes("{label}")) {
      throw new ToolError("input_error", "With `multi`, `question` must contain {label}; each label's description replaces it in its own yes/no question.");
    }

    if ((input.items?.length ?? 0) > CLASSIFY.MAX_ITEMS) throw new ToolError("input_error", `Pass at most ${CLASSIFY.MAX_ITEMS} items.`);
    const { blocks, redactions } = await resolveRefs(p.ws, input.items ?? [{ diff: {} }], "whole", p.secrets);
    if (blocks.length === 0) throw new ToolError("input_error", "No items to classify: the diff is empty or the references resolved to nothing.");
    if (blocks.length > CLASSIFY.MAX_ITEMS) {
      throw new ToolError("input_error", `${blocks.length} items exceed the limit of ${CLASSIFY.MAX_ITEMS}.`, "Narrow the diff `paths` or split the call.");
    }
    const sampleRef = `\`items.${padId("I", 0, CLASSIFY.ITEMS_PER_REQUEST)}\``;
    const longestQuestion = mode === "single"
      ? estimateTokens(JSON.stringify(classifyChoice(renderQuestion(template, sampleRef), labels)))
      : Math.max(...names.map((name) => estimateTokens(JSON.stringify(classifyNoul(renderQuestion(template, sampleRef, labels[name] as string))))));
    const budget = packBudget(longestQuestion, jsonTokens(context ?? "") + BUDGET.BLOCK_OVERHEAD_TOKENS);
    const itemMax = Math.min(CLASSIFY.ITEM_MAX_TOKENS, budget - BUDGET.BLOCK_OVERHEAD_TOKENS);
    const items = blocks.map((block) => ({ id: itemId(block), text: clipTokens(block.text, itemMax) }));
    const perRequest = mode === "single"
      ? CLASSIFY.ITEMS_PER_REQUEST
      : Math.max(1, Math.min(CLASSIFY.MULTI_ITEMS_PER_REQUEST, Math.floor(BUDGET.QUESTIONS_PER_REQUEST / names.length)));
    const indexed = items.map((item, index) => ({ ...item, index }));
    const batches = packBy(indexed, (item) => jsonTokens(item.text) + BUDGET.BLOCK_OVERHEAD_TOKENS, budget, perRequest);

    const outcomes = new Map<number, Record<string, unknown>>();
    await Promise.all(batches.map(async (batch) => {
      const keys = batch.map((_, position) => padId("I", position, batch.length));
      const itemsState: Record<string, string> = {};
      batch.forEach((item, position) => {
        itemsState[keys[position] as string] = item.text;
      });
      const state: Record<string, JsonValue> = context ? { context, items: itemsState } : { items: itemsState };
      const build = (position: number): Questions => {
        const ref = `\`items.${keys[position]}\``;
        if (mode === "single") return { [`q${position}`]: classifyChoice(renderQuestion(template, ref), labels) };
        const questions: Questions = {};
        names.forEach((name, k) => {
          questions[`q${position}_${k}`] = classifyNoul(renderQuestion(template, ref, labels[name] as string));
        });
        return questions;
      };
      const positions = batch.map((_, position) => position);
      for (const group of groupQuestions(positions, build, estimateTokens(JSON.stringify(state)))) {
        const result = await evaluate(p.call, state, Object.assign({}, ...group.map(build)) as Questions);
        for (const position of group) {
          const item = batch[position] as (typeof indexed)[number];
          if (mode === "single") {
            const answer = choiceOf(result.answers, `q${position}`);
            const order = ranked(answer);
            const accept = answer.confidence >= CLASSIFY.ACCEPT;
            outcomes.set(item.index, {
              id: item.id,
              label: answer.choice,
              confidence: round(answer.confidence),
              decision: accept ? "accept" : "review",
              ...(!accept && order[1] ? { alt: order[1][0] } : {}),
            });
          } else {
            const flagged: string[] = [];
            const review: string[] = [];
            names.forEach((name, k) => {
              const value = noulOf(result.answers, `q${position}_${k}`);
              if (value >= CLASSIFY.MULTI_YES) flagged.push(name);
              else if (value >= CLASSIFY.MULTI_REVIEW) review.push(name);
            });
            outcomes.set(item.index, {
              id: item.id,
              labels: flagged,
              ...(review.length > 0 ? { review } : {}),
              decision: review.length > 0 ? "review" : "accept",
            });
          }
        }
      }
    }));

    const results = items.map((_, index) => outcomes.get(index) as Record<string, unknown>);
    const summary: Record<string, number> = {};
    for (const result of results) {
      const found = mode === "single" ? [result.label as string] : (result.labels as string[]);
      for (const label of found) summary[label] = (summary[label] ?? 0) + 1;
    }
    return {
      status: "ok",
      ...(input.preset ? { preset: input.preset } : {}),
      mode,
      results,
      summary,
      ...(redactions > 0 ? { redactions } : {}),
    };
  });
}
