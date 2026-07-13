---
name: visual-regression
description: Compares changed routes at the configured breakpoints against stored Playwright screenshot baselines via toHaveScreenshot and reports diffs with an explicit reviewed baseline-update path, degrading gracefully when the browser is unavailable
user-invocable: false
---

# Visual Regression

## When to use

This skill is exposed by ritus-ui so the ritus workflow can invoke it when available, on Frontend/UI changes where
visual stability matters. It compares the rendered routes against stored screenshot baselines to catch unintended
visual changes. The workflow-side wiring that decides when to call it is decided separately.

## Prerequisite and availability check

- This skill requires Playwright installed as a project dependency (providing `toHaveScreenshot`) together with the
  Playwright MCP browser tools contributed by the ritus-ui plugin.
- Check availability first: confirm Playwright is present in the project, the Playwright MCP tools are in the session,
  and the Chromium binary is installed (the SessionStart hook writes an install marker into the plugin data dir).
- When Playwright, the MCP tools, or the browser binary is unavailable, skip with a warning and let the work
  continue, mirroring the build/test/lint skip pattern (a missing capability is a skip-with-warning, and stays a soft
  skip rather than a hard failure).
- Report the skip clearly so the parent skill records that the visual regression check was not run.

## Steps

1. Read the ritus-ui preview config from `.ritus/ritus-ui.config.yml`, and skip with a warning when the file is absent: the dev-server command, the base URL, and
   the breakpoints.
2. Resolve the changed routes from the diff, and ensure the app is serving with the configured command. When a
   changed route's page URL is unclear or ambiguous, stop and ask the user for it (the base URL points only at the
   app root). When dispatched and unable to reach the user, report BLOCKED naming the page URL needed, rather than
   guessing the route.
3. For each changed route, render it at every configured breakpoint and compare against the stored baseline via
   Playwright `toHaveScreenshot`.
4. Report each diff with its route, breakpoint, and the diff-image evidence path, and mark the routes that match
   their baseline.
5. Provide an explicit, reviewed baseline-update path: when a diff reflects an intended change, a reviewer approves
   it, then the baseline is refreshed by running the Playwright suite with `--update-snapshots` and committing the
   updated baseline images.
6. Report the pass or fail summary with the diff evidence paths and whether a baseline update was approved.

## Handoff

- **Report:** the pass or fail summary with per-route diff evidence paths and any approved baseline update applied to
  the parent skill's work, or the skip-with-warning notice when the browser capability is unavailable.
