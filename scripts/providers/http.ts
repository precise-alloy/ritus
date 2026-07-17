import { Buffer } from 'node:buffer';
import type { EnvMapping, HttpError, RequestHeaders } from './types.ts';

export const REQUEST_TIMEOUT_MS = 30_000;
export const MAX_RETRIES = 3;
export const RETRY_BASE_DELAY_MS = 500;
export const MAX_REDIRECTS = 5;

export async function readEnvFile(filePath: string): Promise<void> {
  const file = Bun.file(filePath);
  if (!(await file.exists())) {
    return;
  }

  const content = await file.text();
  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) {
      continue;
    }

    const separatorIndex = line.indexOf('=');
    if (separatorIndex === -1) {
      continue;
    }

    const key = line.slice(0, separatorIndex).trim();
    let value = line.slice(separatorIndex + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }

    if (!(key in process.env)) {
      process.env[key] = value;
    }
  }
}

export async function loadLocalEnv(): Promise<void> {
  await readEnvFile(`${process.cwd()}/.ritus/.env.local`);
}

export function basicAuth(value: string): string {
  return `Basic ${Buffer.from(value, 'utf8').toString('base64')}`;
}

export function requireEnv(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) {
    throw new Error(`Missing required environment variable ${name}. Populate it in .ritus/.env.local before using this helper.`);
  }

  return value;
}

export function resolveEnv(envMapping: EnvMapping, logicalKey: string): string {
  const envVarName = envMapping[logicalKey];
  if (!envVarName) {
    throw new Error(`No env var mapping found for logical key "${logicalKey}"`);
  }
  if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(envVarName)) {
    throw new Error(`Invalid env var name "${envVarName}" for key "${logicalKey}": must be alphanumeric and underscores only`);
  }
  const value = process.env[envVarName]?.trim();
  if (!value) {
    throw new Error(`Missing ${envVarName} (mapped from ${logicalKey}). Populate it in .ritus/.env.local before using this helper.`);
  }
  return value;
}

export function parseJson(text: string): unknown {
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export function buildErrorMessage(url: string, statusCode: number, responseBody: unknown): string {
  const responseText = typeof responseBody === 'string' ? responseBody : JSON.stringify(responseBody);

  let detail = responseText;
  if (responseBody && typeof responseBody === 'object') {
    if ('errorMessages' in responseBody && Array.isArray(responseBody.errorMessages) && responseBody.errorMessages.length > 0) {
      detail = responseBody.errorMessages.join(' | ');
    } else if ('message' in responseBody && typeof responseBody.message === 'string') {
      detail = responseBody.message;
    } else if ('error_description' in responseBody && typeof responseBody.error_description === 'string') {
      detail = responseBody.error_description;
    }
  }

  return `Request failed with ${statusCode} for ${url}: ${detail}`;
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function isTransientStatus(status: number): boolean {
  return status === 408 || status === 429 || (status >= 500 && status <= 599);
}

export function isRedirectStatus(status: number): boolean {
  return status === 301 || status === 302 || status === 303 || status === 307 || status === 308;
}

async function requestWithRetry(url: string, headers: RequestHeaders, redirect: 'follow' | 'manual' = 'follow', method: 'GET' | 'POST' = 'GET', body?: string): Promise<Response> {
  let lastError: HttpError | null = null;

  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    let response: Response;
    try {
      response = await fetch(url, {
        method,
        headers,
        body,
        signal: controller.signal,
        redirect,
      });
    } catch (err) {
      clearTimeout(timer);
      const reason = err instanceof Error ? err.message : String(err);
      const aborted = err instanceof Error && err.name === 'AbortError';
      const wrapped: HttpError = new Error(aborted ? `Request to ${url} timed out after ${REQUEST_TIMEOUT_MS}ms` : `Network error calling ${url}: ${reason}`);
      lastError = wrapped;
      if (attempt < MAX_RETRIES) {
        await sleep(RETRY_BASE_DELAY_MS * 2 ** (attempt - 1));
        continue;
      }
      throw wrapped;
    }
    clearTimeout(timer);

    if (response.ok) {
      return response;
    }

    if (redirect === 'manual' && isRedirectStatus(response.status)) {
      return response;
    }

    const bodyText = await response.text();
    const parsedBody = parseJson(bodyText);
    const error: HttpError = new Error(buildErrorMessage(url, response.status, parsedBody));
    error.statusCode = response.status;
    error.responseBody = parsedBody;

    if (attempt < MAX_RETRIES && isTransientStatus(response.status)) {
      lastError = error;
      const retryAfter = Number(response.headers.get('retry-after'));
      const delay = Number.isFinite(retryAfter) && retryAfter > 0 ? retryAfter * 1000 : RETRY_BASE_DELAY_MS * 2 ** (attempt - 1);
      await sleep(delay);
      continue;
    }

    throw error;
  }

  throw lastError ?? new Error(`Request to ${url} failed after ${MAX_RETRIES} attempts`);
}

export async function requestJson(url: string, headers: RequestHeaders): Promise<unknown> {
  const response = await requestWithRetry(url, headers);
  return parseJson(await response.text());
}

export async function requestJsonWithHeaders(url: string, headers: RequestHeaders): Promise<{ body: unknown; headers: Headers }> {
  const response = await requestWithRetry(url, headers);
  return { body: parseJson(await response.text()), headers: response.headers };
}

export async function requestGraphQL(
  endpoint: string,
  headers: RequestHeaders,
  query: string,
  variables: Record<string, unknown>,
): Promise<unknown> {
  const response = await requestWithRetry(
    endpoint,
    { ...headers, 'Content-Type': 'application/json' },
    'follow',
    'POST',
    JSON.stringify({ query, variables }),
  );
  const parsed = parseJson(await response.text());
  if (parsed && typeof parsed === 'object' && 'errors' in parsed) {
    const errors = (parsed as { errors: unknown }).errors;
    if (Array.isArray(errors) && errors.length > 0) {
      const detail = errors
        .map((e) => (e && typeof e === 'object' && 'message' in e ? String((e as { message: unknown }).message) : JSON.stringify(e)))
        .join(' | ');
      const error: HttpError = new Error(`GraphQL request to ${endpoint} failed: ${detail}`);
      error.statusCode = 200;
      error.responseBody = parsed;
      throw error;
    }
  }
  if (parsed && typeof parsed === 'object' && 'data' in parsed) {
    return (parsed as { data: unknown }).data;
  }
  return parsed;
}

/** Wraps decodeURIComponent so invalid percent-encoding (e.g. a literal '%') returns the raw value instead of throwing. */
export function safeDecode(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

export async function requestBinary(url: string, headers: RequestHeaders, outputPath: string, validateUrl?: (url: string) => void): Promise<number> {
  let currentUrl = url;

  for (let redirects = 0; redirects <= MAX_REDIRECTS; redirects++) {
    validateUrl?.(currentUrl);
    const response = await requestWithRetry(currentUrl, headers, 'manual');

    if (isRedirectStatus(response.status)) {
      const location = response.headers.get('location');
      if (!location) {
        throw new Error(`Redirect from ${currentUrl} is missing a Location header`);
      }
      currentUrl = new URL(location, currentUrl).toString();
      continue;
    }

    const buffer = await response.arrayBuffer();
    await Bun.write(outputPath, buffer);
    return buffer.byteLength;
  }

  throw new Error(`Too many redirects (>${MAX_REDIRECTS}) while downloading ${url}`);
}
