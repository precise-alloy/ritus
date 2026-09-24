import { resolve } from "node:path";
import { z } from "zod";
import { fitResponse } from "./budget.ts";
import { doctor } from "./doctor.ts";
import { logError } from "./log.ts";
import { SHAPES, type ToolName } from "./schemas.ts";
import { serve } from "./server.ts";
import { ask, type AskInput } from "./tools/ask.ts";
import { check, type CheckInput } from "./tools/check.ts";
import { classify, type ClassifyInput } from "./tools/classify.ts";
import { locate, type LocateInput } from "./tools/locate.ts";
import { sweep, type SweepInput } from "./tools/sweep.ts";
import type { ToolContext, ToolResult } from "./types.ts";
import { VERSION } from "./version.ts";

const HELP = `ritus-jev ${VERSION} - TypeSafe Jev tools for coding agents

Usage (run with: bun --use-system-ca <plugin-root>/dist/jev.js ...)
  serve                          MCP stdio server (default; started by the plugin)
  doctor [--workspace <dir>] [--ping]
                                 Show workspace, key source, model and TLS mode; --ping validates the key
  locate|sweep|check|classify|ask [--workspace <dir>] (--args-file <file.json> | --json '<json>')
                                 Run one tool with the same arguments and output as the MCP tool; prints JSON

The key is read from TYPESAFE_API_KEY in <repo>/.ritus/.env.local (then the main worktree, then the environment).`;

const RUNNERS: Record<ToolName, (input: never, ctx: ToolContext) => Promise<ToolResult>> = {
  locate: (input: LocateInput, ctx) => locate(input, ctx),
  sweep: (input: SweepInput, ctx) => sweep(input, ctx),
  check: (input: CheckInput, ctx) => check(input, ctx),
  classify: (input: ClassifyInput, ctx) => classify(input, ctx),
  ask: (input: AskInput, ctx) => ask(input, ctx),
};

function flag(args: readonly string[], name: string): string | undefined {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : undefined;
}

async function runTool(name: ToolName, args: readonly string[]): Promise<number> {
  let payload: Record<string, unknown> = {};
  const file = flag(args, "--args-file");
  const json = flag(args, "--json");
  if (file) payload = JSON.parse(await Bun.file(file).text()) as Record<string, unknown>;
  if (json) payload = { ...payload, ...(JSON.parse(json) as Record<string, unknown>) };
  const workspace = flag(args, "--workspace");
  if (workspace || payload.workspace === undefined) payload.workspace = resolve(workspace ?? process.cwd());
  const parsed = z.object(SHAPES[name]).strict().safeParse(payload);
  if (!parsed.success) {
    console.error(parsed.error.issues.map((issue) => `${issue.path.join(".") || "(root)"}: ${issue.message}`).join("\n"));
    return 2;
  }
  const result = fitResponse(await RUNNERS[name](parsed.data as never, { roots: async () => null }));
  console.log(JSON.stringify(result, null, 2));
  return result.status === "ok" ? 0 : 1;
}

async function main(argv: readonly string[]): Promise<number> {
  const [command = "serve", ...rest] = argv;
  switch (command) {
    case "serve":
      await serve();
      return -1;
    case "doctor":
      console.log(JSON.stringify(await doctor(flag(rest, "--workspace"), rest.includes("--ping")), null, 2));
      return 0;
    case "locate":
    case "sweep":
    case "check":
    case "classify":
    case "ask":
      return runTool(command, rest);
    case "--version":
    case "version":
      console.log(VERSION);
      return 0;
    case "--help":
    case "help":
      console.log(HELP);
      return 0;
    default:
      console.error(HELP);
      return 2;
  }
}

main(process.argv.slice(2))
  .then((code) => {
    if (code >= 0) process.exitCode = code;
  })
  .catch((error: unknown) => {
    logError(error instanceof Error ? (error.stack ?? error.message) : String(error));
    process.exitCode = 1;
  });
