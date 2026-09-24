import { fileURLToPath } from "node:url";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { RootsListChangedNotificationSchema, type CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { fitResponse } from "./budget.ts";
import { logError } from "./log.ts";
import { realpathOrNull } from "./paths.ts";
import { askShape, checkShape, classifyShape, locateShape, sweepShape } from "./schemas.ts";
import { ask } from "./tools/ask.ts";
import { check } from "./tools/check.ts";
import { classify } from "./tools/classify.ts";
import { locate } from "./tools/locate.ts";
import { sweep } from "./tools/sweep.ts";
import type { ToolContext, ToolResult } from "./types.ts";
import { VERSION } from "./version.ts";

const INSTRUCTIONS =
  "Jev tools (TypeSafe System One) read files and git diffs server-side and return compact, cited judgments. " +
  "Always pass `workspace` = the absolute path of the repository you are working in. Results are leads: confirm at the " +
  "cited file:line ranges before asserting. Status `disabled` means no usable TYPESAFE_API_KEY is configured - continue " +
  "with ordinary tools for the rest of the session.";

export const DESCRIPTIONS = {
  locate:
    "Semantic code search with TypeSafe Jev. Finds where something is implemented, defined, configured, tested or " +
    "documented - or where a failure is reported in a saved log - and returns ranked file:line ranges plus the text of " +
    "the best hits. Use it when you know what you need but not where, across more than a handful of files; use grep " +
    "or LSP for an exact identifier. One behavior per query; scope large repos with `paths` and optional `terms`.",
  sweep:
    "Finds every passage that states or relies on something, not just the best match: after changing a rule, contract, " +
    "API or term, sweep for text that still describes the old one (stale docs, skills, comments, callers) - wording " +
    "grep cannot enumerate. Returns all hits above the threshold as file:line with the matching line, in file order. " +
    "Describe the passages to find directly (the old wording or behavior), not the new rule.",
  check:
    "Checks atomic claims against files or the git diff with TypeSafe Jev (DONE WHEN items, acceptance criteria, " +
    "'is this review comment already addressed?'). Quoted-phrase, count and changed-file claims are answered exactly " +
    "in code; other claims are judged passage by passage. Returns supported / contradicted / not_found / uncertain / " +
    "use_search per claim with the cited range. Default evidence: working-tree diff vs HEAD plus untracked files and " +
    "files the claims name. Confirm contradicted and uncertain verdicts at the cited lines.",
  classify:
    "Classifies many items (text, file ranges or git diff hunks) with calibrated confidence using TypeSafe Jev. " +
    "Presets: failure_kind (test/build output), review_comment (PR feedback triage), change_risk (security-sensitive " +
    "areas, multi-label), change_scope (each diff hunk vs the task in `context`); or pass custom `labels`. Returns a " +
    "label, confidence and accept/review decision per item.",
  ask:
    "Raw TypeSafe Jev call for a novel, narrow judgment that the other tools do not cover: choice (pick one " +
    "option), score (position on 2-10 ordered levels) or noul (probability of yes) over `state` and/or `sources`. " +
    "Ask one atomic judgment per question; keep arithmetic, counting, dates and exact matching in code.",
} as const;

const READ_ONLY = { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: true } as const;

async function respond(run: () => Promise<ToolResult>): Promise<CallToolResult> {
  try {
    const result = fitResponse(await run());
    return {
      content: [{ type: "text", text: JSON.stringify(result) }],
      ...(result.status === "input_error" ? { isError: true } : {}),
    };
  } catch (error) {
    logError(error instanceof Error ? (error.stack ?? error.message) : String(error));
    const message = error instanceof Error ? error.message : String(error);
    return { content: [{ type: "text", text: JSON.stringify({ status: "unavailable", error: message }) }], isError: true };
  }
}

export function createServer(): McpServer {
  const server = new McpServer({ name: "jev", version: VERSION }, { instructions: INSTRUCTIONS });
  let roots: string[] | null = null;
  let pending: Promise<void> | null = null;

  const refreshRoots = (): Promise<void> => {
    pending = (async () => {
      if (!server.server.getClientCapabilities()?.roots) {
        roots = null;
        return;
      }
      try {
        const listed = await server.server.listRoots();
        roots = listed.roots
          .map((root) => root.uri)
          .filter((uri) => uri.startsWith("file:"))
          .map((uri) => {
            const path = fileURLToPath(uri);
            return realpathOrNull(path) ?? path;
          });
      } catch (error) {
        logError(`roots/list failed: ${error instanceof Error ? error.message : String(error)}`);
        roots = null;
      }
    })();
    return pending;
  };
  server.server.oninitialized = () => {
    void refreshRoots();
  };
  server.server.setNotificationHandler(RootsListChangedNotificationSchema, async () => {
    await refreshRoots();
  });

  const ctx: ToolContext = {
    roots: async () => {
      if (pending) await Promise.race([pending, Bun.sleep(2000)]);
      return roots;
    },
  };

  server.registerTool("locate", { title: "Locate code (Jev)", description: DESCRIPTIONS.locate, inputSchema: locateShape, annotations: READ_ONLY },
    (args) => respond(() => locate(args, ctx)));
  server.registerTool("sweep", { title: "Sweep for every match (Jev)", description: DESCRIPTIONS.sweep, inputSchema: sweepShape, annotations: READ_ONLY },
    (args) => respond(() => sweep(args, ctx)));
  server.registerTool("check", { title: "Check claims (Jev)", description: DESCRIPTIONS.check, inputSchema: checkShape, annotations: READ_ONLY },
    (args) => respond(() => check(args, ctx)));
  server.registerTool("classify", { title: "Classify items (Jev)", description: DESCRIPTIONS.classify, inputSchema: classifyShape, annotations: READ_ONLY },
    (args) => respond(() => classify(args, ctx)));
  server.registerTool("ask", { title: "Ask Jev", description: DESCRIPTIONS.ask, inputSchema: askShape, annotations: READ_ONLY },
    (args) => respond(() => ask(args, ctx)));
  return server;
}

export async function serve(): Promise<void> {
  const server = createServer();
  await server.connect(new StdioServerTransport());
}
