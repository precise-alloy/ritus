import { fileURLToPath } from "node:url";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { RootsListChangedNotificationSchema, type CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { logError } from "./log.ts";
import { realpathOrNull } from "./paths.ts";
import { askShape, checkShape, classifyShape, locateShape } from "./schemas.ts";
import { ask } from "./tools/ask.ts";
import { check } from "./tools/check.ts";
import { classify } from "./tools/classify.ts";
import { locate } from "./tools/locate.ts";
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
    "the best hits. Use it instead of reading whole files or chaining grep/view calls when you know what you need but " +
    "not where; use grep or LSP for an exact identifier. Scope large repos with `paths` and optional `terms`.",
  check:
    "Checks specific claims against code, files or the git diff with TypeSafe Jev: DONE WHEN conditions, acceptance " +
    "criteria, 'is this review comment already addressed?', 'does a test cover X?'. Returns supported / contradicted / " +
    "not_found / uncertain per claim with the cited file:line range and its lines. Default evidence: working-tree diff " +
    "vs HEAD plus untracked files. Treat verdicts as leads and confirm them at the cited lines.",
  classify:
    "Classifies many items (text, file ranges or git diff hunks) with calibrated confidence using TypeSafe Jev. " +
    "Presets: failure_kind (test/build output), review_comment (PR feedback triage), change_risk (security-sensitive " +
    "areas, multi-label), change_scope (each diff hunk vs the task in `context`); or pass custom `labels`. Returns a " +
    "label, confidence and accept/review decision per item.",
  ask:
    "Raw TypeSafe Jev call for a novel, narrow judgment that locate/check/classify do not cover: choice (pick one " +
    "option), score (position on 2-10 ordered levels) or noul (probability of yes) over `state` and/or `sources`. " +
    "Ask one atomic judgment per question; keep arithmetic, counting, dates and exact matching in code.",
} as const;

const READ_ONLY = { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: true } as const;

async function respond(run: () => Promise<ToolResult>): Promise<CallToolResult> {
  try {
    const result = await run();
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
