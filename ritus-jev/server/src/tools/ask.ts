import type { EntryType, JsonValue, Question, Questions } from "@typesafe-ai/sdk";
import { choiceOf, noulOf, ranked, scoreOf } from "../answers.ts";
import { blockLabel, estimateTokens, fitsRequest } from "../budget.ts";
import { redactText } from "../files.ts";
import { evaluate } from "../jev.ts";
import { ASK, noulBand } from "../policy.ts";
import { round, withJev } from "../run.ts";
import { resolveRefs, type SourceRef } from "../sources.ts";
import { ToolError, type ToolContext, type ToolResult } from "../types.ts";

export interface AskQuestion {
  type: "noul" | "choice" | "score";
  instructions: string | Record<string, unknown>;
  criteria?: Record<string, string | null> | string[];
}

export interface AskInput {
  workspace: string;
  state?: string | Record<string, unknown>;
  sources?: SourceRef[];
  questions: Record<string, AskQuestion>;
}

const ID = /^[A-Za-z0-9_-]{1,64}$/;

function toQuestion(id: string, question: AskQuestion): Question {
  const instructions = question.instructions as EntryType;
  if (question.type === "noul") {
    const criteria = question.criteria;
    if (criteria !== undefined && (Array.isArray(criteria) || Object.keys(criteria).some((key) => key !== "true" && key !== "false"))) {
      throw new ToolError("input_error", `Question ${id}: noul criteria may only have \`true\` and \`false\`.`);
    }
    return criteria ? { type: "noul", instructions, criteria: criteria as { true?: string; false?: string } } : { type: "noul", instructions };
  }
  if (question.type === "choice") {
    const criteria = question.criteria;
    const size = criteria && !Array.isArray(criteria) ? Object.keys(criteria).length : 0;
    if (size < 2 || size > 255) throw new ToolError("input_error", `Question ${id}: choice needs 2-255 options in \`criteria\`.`);
    return { type: "choice", instructions, criteria: criteria as Record<string, string | null> };
  }
  const levels = question.criteria;
  if (!Array.isArray(levels) || levels.length < 2 || levels.length > 10) {
    throw new ToolError("input_error", `Question ${id}: score needs 2-10 ordered levels in \`criteria\`.`);
  }
  return { type: "score", instructions, criteria: levels as [string, string, ...string[]] };
}

function redactValue(value: unknown, secrets: readonly string[], counter: { count: number }): JsonValue {
  if (typeof value === "string") {
    const redacted = redactText(value, secrets);
    counter.count += redacted.count;
    return redacted.text;
  }
  if (Array.isArray(value)) return value.map((entry) => redactValue(entry, secrets, counter));
  if (value && typeof value === "object") {
    const out: Record<string, JsonValue> = {};
    for (const [key, entry] of Object.entries(value)) out[key] = redactValue(entry, secrets, counter);
    return out;
  }
  return (value ?? null) as JsonValue;
}

export async function ask(input: AskInput, ctx: ToolContext): Promise<ToolResult> {
  return withJev(input.workspace, ctx, async (p) => {
    const entries = Object.entries(input.questions ?? {});
    if (entries.length === 0 || entries.length > ASK.MAX_QUESTIONS) {
      throw new ToolError("input_error", `Provide 1-${ASK.MAX_QUESTIONS} questions.`);
    }
    const questions: Questions = {};
    for (const [id, question] of entries) {
      if (!ID.test(id)) throw new ToolError("input_error", `Question id ${JSON.stringify(id)} must match ${ID.source}.`);
      questions[id] = toQuestion(id, question);
    }
    if (input.state === undefined && (input.sources ?? []).length === 0) {
      throw new ToolError("input_error", "Provide `state`, `sources`, or both.");
    }
    if ((input.sources?.length ?? 0) > 20) throw new ToolError("input_error", "Pass at most 20 `sources`.");
    const counter = { count: 0 };
    const base = input.state === undefined ? undefined : (redactValue(input.state, p.secrets, counter) as EntryType);
    let state: EntryType = base ?? null;
    let legend: Record<string, string> | undefined;
    if (input.sources && input.sources.length > 0) {
      const { blocks, redactions } = await resolveRefs(p.ws, input.sources, "whole", p.secrets);
      counter.count += redactions;
      const sources: Record<string, string> = {};
      legend = {};
      blocks.forEach((block, index) => {
        const id = block.kind === "inline" ? block.path : `S${index + 1}`;
        sources[id] = blockLabel(block);
        legend![id] = block.kind === "inline" ? "inline text" : `${block.path}:${block.start}-${block.end}`;
      });
      state = base === undefined ? { sources } : { input: base, sources };
    }
    if (!fitsRequest(estimateTokens(JSON.stringify(state)), questions)) {
      throw new ToolError("input_error", "The request exceeds Jev's context budget (about 32k tokens of state plus the longest question).",
        "Send less state (narrow line ranges) or fewer questions.");
    }
    const result = await evaluate(p.call, state, questions);
    const answers: Record<string, unknown> = {};
    for (const [id, question] of Object.entries(questions)) {
      if (question.type === "noul") {
        const value = noulOf(result.answers, id);
        answers[id] = { type: "noul", p: round(value), band: noulBand(value) };
      } else if (question.type === "choice") {
        const answer = choiceOf(result.answers, id);
        answers[id] = {
          type: "choice",
          choice: answer.choice,
          confidence: round(answer.confidence),
          top: Object.fromEntries(ranked(answer).slice(0, 3).map(([option, value]) => [option, round(value)])),
        };
      } else {
        const answer = scoreOf(result.answers, id);
        const legendEntries = answer.legend as Record<string, unknown>;
        answers[id] = {
          type: "score",
          score: round(answer.score),
          confidence: round(answer.confidence),
          level: legendEntries[String(Math.round(answer.score))] ?? null,
        };
      }
    }
    return {
      status: "ok",
      answers,
      ...(legend ? { sources: legend } : {}),
      ...(counter.count > 0 ? { redactions: counter.count } : {}),
    };
  });
}
