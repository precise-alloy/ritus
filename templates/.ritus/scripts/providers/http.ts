import { Buffer } from 'node:buffer';
import type { HttpError, RequestHeaders } from './types.ts';

export const REQUEST_TIMEOUT_MS = 30_000;
export const MAX_RETRIES = 3;
export const RETRY_BASE_DELAY_MS = 500;

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
  await readEnvFile(`${process.cwd()}/.env.local`);
}

export function basicAuth(value: string): string {
  return `Basic ${Buffer.from(value, 'utf8').toString('base64')}`;
}

export function requireEnv(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) {
    throw new Error(`Missing required environment variable ${name}. Populate it in .env.local before using this helper.`);
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

async function requestWithRetry(url: string, headers: RequestHeaders): Promise<Response> {
  let lastError: HttpError | null = null;

  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    let response: Response;
    try {
      response = await fetch(url, {
        method: 'GET',
        headers,
        signal: controller.signal,
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

export async function requestBinary(url: string, headers: RequestHeaders, outputPath: string): Promise<number> {
  const response = await requestWithRetry(url, headers);
  const buffer = await response.arrayBuffer();
  await Bun.write(outputPath, buffer);
  return buffer.byteLength;
}
