---
name: a11y-audit
description: Runs an axe-core accessibility audit against rendered routes and maps violations to the definition-of-done a11y checklist with severity and location, degrading gracefully when the browser is unavailable
user-invocable: false
---

# A11y Audit

## When to use

This skill is exposed by ritus-ui so the ritus workflow can invoke it when available, on Frontend/UI changes. It runs
an axe-core accessibility audit against the rendered routes and complements the definition-of-done a11y items by
grounding them in measured violations. The workflow-side wiring that decides when to call it is decided separately.

## Prerequisite and availability check

- This skill requires the Playwright MCP browser tools contributed by the ritus-ui plugin, together with axe-core to
  run the accessibility checks.
- Check availability first: confirm the Playwright MCP tools are present in the session, the Chromium binary is
  installed (the SessionStart hook writes an install marker into the plugin data dir), and axe-core can be injected
  into the rendered page.
- When the Playwright MCP tools, the browser binary, or axe-core is unavailable, skip with a warning and let the work
  continue, mirroring the build/test/lint skip pattern (a missing capability is a skip-with-warning, and stays a soft
  skip rather than a hard failure).
- Report the skip clearly so the parent skill records that the accessibility audit was not run.

## Steps

1. Read the ritus-ui preview config from `.ritus/ritus-ui.config.yml`, and skip with a warning when the file is absent: the dev-server command, the base URL, and
   the breakpoints.
2. Resolve the changed routes, and ensure the app is serving with the configured command. When a changed route's
   page URL is unclear or ambiguous, stop and ask the user for it (the base URL points only at the app root). When
   dispatched and unable to reach the user, report BLOCKED naming the page URL needed, rather than guessing the route.
3. For each route, render it via the Playwright MCP and run an axe-core audit against the rendered page.
4. Map each violation to the definition-of-done a11y items: images carry `alt` text, icon-only controls carry an
   `aria-label`, interactive elements expose the correct `role`, and every input has an associated label.
5. Record each finding with its severity, the mapped a11y item, and the element location on the route.
6. Report the findings grouped by severity with their locations, alongside the a11y items that passed clean.

## Handoff

- **Report:** the accessibility findings mapped to the definition-of-done a11y items, with severity and location,
  applied to the parent skill's work, or the skip-with-warning notice when the browser capability is unavailable.
