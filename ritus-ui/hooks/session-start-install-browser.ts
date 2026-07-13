#!/usr/bin/env bun
// SessionStart hook: install the Chromium browser binary once per environment
// into the ritus-ui plugin data dir. The session always continues, even when
// the install is slow or fails - every path degrades to a warning and exits 0.

import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const MARKER_NAME = ".ritus-ui-chromium-installed";

// Cap the Chromium install so a network-stalled download degrades to a warning
// rather than blocking session start.
const INSTALL_TIMEOUT_MS = 120000;

function warn(message: string): void {
  console.error(`[ritus-ui] ${message}`);
}

function info(message: string): void {
  console.log(`[ritus-ui] ${message}`);
}

// Prerequisite: bunx must be available (mirrors the Bun check in
// skills/shared/remote-api-access.md - declare the requirement, verify
// presence, stop-and-ask on absence). Here the stop is a skip-with-warning so
// the session always continues.
function bunxAvailable(): boolean {
  const probe = spawnSync("bunx", ["--version"], {
    stdio: "ignore",
    shell: process.platform === "win32",
  });
  return probe.status === 0;
}

function resolveDataDir(): string | undefined {
  return process.env.CLAUDE_PLUGIN_DATA ?? process.env.COPILOT_PLUGIN_DATA;
}

function main(): void {
  if (!bunxAvailable()) {
    warn(
      "bunx (Node.js) is required to install the browser for visual verification. " +
        "Install Node.js, then reopen the session to enable ritus-ui browser tools. Skipping browser install.",
    );
    process.exit(0);
  }

  const dataDir = resolveDataDir();
  if (!dataDir) {
    warn(
      "No plugin data dir found (CLAUDE_PLUGIN_DATA / COPILOT_PLUGIN_DATA unset). Skipping browser install.",
    );
    process.exit(0);
  }

  const marker = join(dataDir, MARKER_NAME);
  if (existsSync(marker)) {
    info("Chromium already installed for ritus-ui. Skipping download.");
    process.exit(0);
  }

  try {
    mkdirSync(dataDir, { recursive: true });

    info("Installing Chromium for ritus-ui visual verification (one-time)...");
    const result = spawnSync("bunx", ["playwright", "install", "chromium"], {
      stdio: "inherit",
      shell: process.platform === "win32",
      env: { ...process.env, PLAYWRIGHT_BROWSERS_PATH: dataDir },
      timeout: INSTALL_TIMEOUT_MS,
      killSignal: "SIGTERM",
    });

    // A timeout leaves result.error set (code ETIMEDOUT) and/or a null status
    // because the process was killed. Treat that the same as any other failure.
    const timedOut =
      result.error !== undefined ||
      (result.signal === "SIGTERM" && result.status === null);

    if (timedOut) {
      warn(
        `Chromium install exceeded ${INSTALL_TIMEOUT_MS / 1000}s and was stopped. ` +
          "Continuing session; visual verification will skip-with-warning until the install succeeds.",
      );
    } else if (result.status === 0) {
      writeFileSync(marker, `installed ${new Date().toISOString()}\n`, "utf8");
      info("Chromium install complete.");
    } else {
      warn(
        "Chromium install did not complete successfully. Visual verification will skip-with-warning until it succeeds.",
      );
    }
  } catch (error) {
    warn(
      `Chromium install failed: ${error instanceof Error ? error.message : String(error)}. ` +
        "Continuing session; visual verification will skip-with-warning.",
    );
  }

  // Always continue the session, regardless of install outcome.
  process.exit(0);
}

main();
