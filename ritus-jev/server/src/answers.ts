import type { ChoiceResponse, NoulResponse, ScoreResponse } from "@typesafe-ai/sdk";
import { ToolError } from "./types.ts";

type Answers = Readonly<Record<string, unknown>>;

function answer(answers: Answers, id: string, type: string): unknown {
  const value = answers[id] as { type?: string } | undefined;
  if (!value || value.type !== type) throw new ToolError("unavailable", `TypeSafe returned no ${type} answer for ${id}.`);
  return value;
}

export function choiceOf(answers: Answers, id: string): ChoiceResponse {
  return answer(answers, id, "choice") as ChoiceResponse;
}

export function noulOf(answers: Answers, id: string): number {
  return (answer(answers, id, "noul") as NoulResponse).noul;
}

export function scoreOf(answers: Answers, id: string): ScoreResponse {
  return answer(answers, id, "score") as ScoreResponse;
}

/** Probability of `option`, 0 when absent. */
export function probability(response: ChoiceResponse, option: string): number {
  return (response.probabilities as Record<string, number>)[option] ?? 0;
}

/** Options sorted by probability, highest first. */
export function ranked(response: ChoiceResponse): [string, number][] {
  return Object.entries(response.probabilities as Record<string, number>).sort((a, b) => b[1] - a[1]);
}
