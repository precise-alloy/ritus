import { resolve } from "node:path";
import { loadConfig, maskKey, resolveWorkspace } from "./config.ts";
import { gitAvailable } from "./git.ts";
import { listModels } from "./jev.ts";
import { ToolError } from "./types.ts";
import { VERSION } from "./version.ts";

export function usesSystemCa(): boolean {
  return process.execArgv.includes("--use-system-ca") || process.env.NODE_USE_SYSTEM_CA === "1";
}

/** Local configuration report; `ping` makes one free GET /v1/models call to validate the key. */
export async function doctor(workspaceArg: string | undefined, ping: boolean): Promise<Record<string, unknown>> {
  const ws = await resolveWorkspace(resolve(workspaceArg ?? process.cwd()), null);
  const base: Record<string, unknown> = {
    version: VERSION,
    bun: Bun.version,
    platform: `${process.platform}-${process.arch}`,
    workspace: ws.root,
    git: gitAvailable() ? (ws.gitTop ?? "not a repository") : "git not found on PATH",
    tls: usesSystemCa() ? "OS trust store (--use-system-ca)" : "Bun bundled roots (run with bun --use-system-ca behind TLS-inspecting proxies)",
  };
  let config;
  try {
    config = await loadConfig(ws);
  } catch (error) {
    if (!(error instanceof ToolError)) throw error;
    return { ...base, config_error: { status: error.status, error: error.message, ...(error.hint ? { hint: error.hint } : {}) } };
  }
  const report: Record<string, unknown> = {
    ...base,
    key: config.apiKey
      ? { configured: true, source: config.keySource, file: config.keyFile, masked: maskKey(config.apiKey) }
      : { configured: false, setup: `add TYPESAFE_API_KEY=<key> to ${config.setupFile}` },
    ...(config.ignoredKeyFile ? { ignored_key_file: `${config.ignoredKeyFile} (tracked by git)` } : {}),
    model: config.model,
    base_url: config.baseURL ?? "https://api.typesafe.ai",
    proxy: config.proxy ? "configured" : "none",
  };
  if (ping) {
    if (!config.apiKey) {
      report.ping = { ok: false, error: "no TYPESAFE_API_KEY configured" };
    } else {
      try {
        report.ping = { ok: true, models: await listModels(config) };
      } catch (error) {
        const message = error instanceof ToolError ? `${error.status}: ${error.message}` : error instanceof Error ? error.message : String(error);
        report.ping = { ok: false, error: message };
      }
    }
  }
  return report;
}
