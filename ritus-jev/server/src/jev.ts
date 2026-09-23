import { createHash } from "node:crypto";
import {
  APIConnectionError,
  APIError,
  APIUserAbortError,
  AuthenticationError,
  BadRequestError,
  NotFoundError,
  PermissionDeniedError,
  RateLimitError,
  TypeSafeClient,
  UnprocessableEntityError,
  type EntryType,
  type Fetch,
  type Questions,
  type SystemOneResult,
} from "@typesafe-ai/sdk";
import type { JevConfig } from "./config.ts";
import { logDebug } from "./log.ts";
import { LIMITS } from "./policy.ts";
import { ToolError, type Usage } from "./types.ts";

class Semaphore {
  private active = 0;
  private readonly waiting: (() => void)[] = [];
  constructor(private readonly limit: number) {}

  async acquire(): Promise<() => void> {
    if (this.active >= this.limit) await new Promise<void>((resolve) => this.waiting.push(resolve));
    this.active++;
    return () => {
      this.active--;
      this.waiting.shift()?.();
    };
  }
}

const gate = new Semaphore(LIMITS.REQUEST_CONCURRENCY);
const clients = new Map<string, TypeSafeClient>();
const cache = new Map<string, { at: number; value: SystemOneResult<Questions> }>();

function clientFor(config: JevConfig): TypeSafeClient {
  const key = JSON.stringify([config.apiKey, config.baseURL, config.model, config.proxy]);
  let client = clients.get(key);
  if (!client) {
    const proxy = config.proxy;
    const fetchWithProxy: Fetch | undefined = proxy
      ? (input, init) => fetch(input, { ...init, proxy } as RequestInit)
      : undefined;
    client = new TypeSafeClient({
      apiKey: config.apiKey ?? "",
      ...(config.baseURL ? { baseURL: config.baseURL } : {}),
      defaultModel: config.model,
      logLevel: "off",
      timeout: LIMITS.REQUEST_TIMEOUT_MS,
      retry: { maxRetries: LIMITS.MAX_RETRIES },
      ...(fetchWithProxy ? { fetch: fetchWithProxy } : {}),
    });
    clients.set(key, client);
  }
  return client;
}

/** One tool invocation: shared deadline, usage accounting and the resolved configuration. */
export class Call {
  readonly usage: Usage = { requests: 0, cached: 0, input_tokens: 0 };
  private readonly controller = new AbortController();
  private readonly timer: ReturnType<typeof setTimeout>;

  constructor(readonly config: JevConfig, deadlineMs: number = LIMITS.TOOL_DEADLINE_MS) {
    this.timer = setTimeout(() => this.controller.abort(), deadlineMs);
  }

  get signal(): AbortSignal {
    return this.controller.signal;
  }

  /** Ends the call: stops the deadline and cancels requests still running or queued (for example after a sibling failed). */
  dispose(): void {
    clearTimeout(this.timer);
    this.controller.abort();
  }
}

function summarizeBody(body: unknown): string {
  const text = typeof body === "string" ? body : JSON.stringify(body ?? "");
  return text.length > 300 ? `${text.slice(0, 300)}...` : text;
}

function mapError(error: unknown, call: Call): never {
  if (error instanceof ToolError) throw error;
  if (error instanceof AuthenticationError || error instanceof PermissionDeniedError) {
    throw new ToolError("auth_error", `TypeSafe rejected the API key (HTTP ${error.status}).`,
      "Check TYPESAFE_API_KEY in .ritus/.env.local, then run the doctor with --ping.");
  }
  if (error instanceof RateLimitError) {
    throw new ToolError("rate_limited", "TypeSafe rate limit reached after retries.",
      "Retry shortly or narrow the request; continue with ordinary tools meanwhile.");
  }
  if (error instanceof UnprocessableEntityError || error instanceof BadRequestError) {
    throw new ToolError("input_error", `TypeSafe rejected the request: ${summarizeBody(error.body)}`);
  }
  if (error instanceof NotFoundError) {
    throw new ToolError("input_error", `TypeSafe returned 404 for model ${call.config.model}.`, "Check TYPESAFE_DEFAULT_MODEL.");
  }
  if (error instanceof APIUserAbortError || call.signal.aborted) {
    throw new ToolError("unavailable", "The Jev call exceeded the tool deadline.", "Narrow the request or retry.");
  }
  if (error instanceof APIConnectionError) {
    throw new ToolError("unavailable", `Cannot reach TypeSafe: ${error.message}`,
      "Check network access to api.typesafe.ai (proxy: HTTPS_PROXY in .ritus/.env.local).");
  }
  if (error instanceof APIError) {
    throw new ToolError(error.status >= 500 ? "unavailable" : "input_error", `TypeSafe error HTTP ${error.status}: ${summarizeBody(error.body)}`);
  }
  throw error;
}

function cacheKey(model: string, state: EntryType, questions: Questions): string {
  return createHash("sha256").update(JSON.stringify([model, state, questions])).digest("hex");
}

/** Sends one System One request (cached, rate-limited) and checks every question came back with its type. */
export async function evaluate<Q extends Questions>(call: Call, state: EntryType, questions: Q): Promise<SystemOneResult<Q>> {
  const key = cacheKey(call.config.model, state, questions);
  const hit = cache.get(key);
  if (hit && Date.now() - hit.at < LIMITS.CACHE_TTL_MS) {
    call.usage.cached++;
    return hit.value as SystemOneResult<Q>;
  }
  if (call.signal.aborted) mapError(new APIUserAbortError(), call);
  const release = await gate.acquire();
  try {
    if (call.signal.aborted) mapError(new APIUserAbortError(), call);
    const started = performance.now();
    const result = await clientFor(call.config).systemOne({ state, questions, model: call.config.model }, { signal: call.signal });
    call.usage.requests++;
    call.usage.input_tokens += result.usage?.input_tokens ?? 0;
    logDebug(`systemOne ${Object.keys(questions).length} questions, ${result.usage?.input_tokens ?? 0} tokens, ${Math.round(performance.now() - started)} ms`);
    for (const [id, question] of Object.entries(questions)) {
      const answer = (result.answers as Record<string, { type?: string } | undefined>)[id];
      if (!answer || answer.type !== question.type) {
        throw new ToolError("unavailable", `TypeSafe returned an unexpected answer for ${id}.`);
      }
    }
    if (cache.size >= LIMITS.CACHE_ENTRIES) cache.delete(cache.keys().next().value as string);
    cache.set(key, { at: Date.now(), value: result as SystemOneResult<Questions> });
    return result;
  } catch (error) {
    return mapError(error, call);
  } finally {
    release();
  }
}

export async function listModels(config: JevConfig): Promise<string[]> {
  const models = await clientFor(config).models.list();
  return models.map((model) => model.name);
}
