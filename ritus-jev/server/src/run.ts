import { loadConfig, resolveWorkspace, type JevConfig, type Workspace } from "./config.ts";
import { Call } from "./jev.ts";
import { ToolError, type ToolContext, type ToolResult } from "./types.ts";

export interface Prepared {
  ws: Workspace;
  config: JevConfig;
  call: Call;
  /** Literal secrets to redact from anything sent (the TypeSafe key itself). */
  secrets: string[];
}

export const round = (value: number): number => Math.round(value * 100) / 100;

/** Resolves workspace + key, runs the tool, and attaches usage; ToolErrors become structured results. */
export async function withJev(workspace: string, ctx: ToolContext, run: (prepared: Prepared) => Promise<ToolResult>): Promise<ToolResult> {
  let call: Call | null = null;
  try {
    const ws = await resolveWorkspace(workspace, await ctx.roots());
    const config = await loadConfig(ws);
    if (!config.apiKey) {
      return {
        status: "disabled",
        hint: `Jev tools are off: add TYPESAFE_API_KEY=<key> to ${config.setupFile}, then call again. Continue with ordinary search and read tools.`,
      };
    }
    call = new Call(config);
    const result = await run({ ws, config, call, secrets: [config.apiKey] });
    const warning = config.ignoredKeyFile
      ? { warning: `${config.ignoredKeyFile} is tracked by git, so its key and settings were ignored; untrack it.` }
      : {};
    return { ...result, ...warning, usage: call.usage, model: config.model };
  } catch (error) {
    if (!(error instanceof ToolError)) throw error;
    return {
      status: error.status,
      error: error.message,
      ...(error.hint ? { hint: error.hint } : {}),
      ...(call ? { usage: call.usage, model: call.config.model } : {}),
    };
  } finally {
    call?.dispose();
  }
}
