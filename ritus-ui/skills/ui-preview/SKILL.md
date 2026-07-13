---
name: ui-preview
description: Drives the implemented UI change in a real browser via the Playwright MCP - performing the user interactions the change affects, capturing evidence at each meaningful state, watching the console, and assessing whether the feature behaves and renders as the task intends, so the caller can iterate while implementing or gate a visual DONE WHEN while verifying; degrades gracefully when the browser is unavailable
user-invocable: false
---

# UI Preview

## When to use

This skill is exposed by ritus-ui so the ritus workflow can invoke it on tasks touching Frontend/UI paths. It is
visual QA: rather than snapshotting a page, it drives the implemented change in a real browser - performing the user
interactions the change affects - and confirms the feature works and renders as the task intends. The caller applies
the policy:

- During implementation, the workflow uses it to exercise the change and iterate on any issue it surfaces.
- During verification, the workflow uses it to gate a visual DONE WHEN, treating a broken interaction, a visual
  mismatch, or a console error as a failing condition.
- During review, pr-review directs it adversarially - driving the change's loading, error, empty, and edge states to
  hunt for defects, keeping the burden of proof on the code.

The workflow-side wiring that decides when to call it is decided separately.

## Prerequisite and availability check

- This skill requires the Playwright MCP browser tools contributed by the ritus-ui plugin.
- Check availability first: confirm the Playwright MCP tools are present in the session and the Chromium binary is
  installed (the SessionStart hook writes an install marker into the plugin data dir).
- When the Playwright MCP tools or the browser binary are unavailable, skip with a warning and let the work continue,
  mirroring the build/test/lint skip pattern (a missing capability is a skip-with-warning, and stays a soft skip
  rather than a hard failure).
- Report the skip clearly so the parent skill records that the UI preview was not run.

## Steps

1. Read the ritus-ui preview config from `.ritus/ritus-ui.config.yml`, and skip with a warning when the file is
   absent: the dev-server command, the base URL, and the breakpoints (for example, 375px mobile and 1280px desktop).
2. Ensure the app is serving: start the dev server with the configured command when it is not already running, and
   resolve the target page URL from the task under implementation or its visual DONE WHEN. When the page URL is
   unclear or ambiguous, stop and ask the user for it (the base URL points only at the app root). When dispatched and
   unable to reach the user, report BLOCKED naming the page URL needed so the main thread can relay it, rather than
   guessing the route.
3. Build a short interaction plan from the task and the diff: the user-facing behavior the change introduces or
   affects - the actions a user takes (click, type, submit, toggle, navigate the flow) and the result each action
   should produce. When the intended behavior is unclear, ask the user (or report BLOCKED when dispatched) rather
   than assuming it.
4. For each configured breakpoint, navigate to the page and work through the interaction plan via the Playwright MCP,
   driving the feature the way a user would and waiting for each step to settle.
5. Capture a screenshot at each meaningful state - the initial render, after each key interaction, and the resulting
   state - and save each under `.ritus/playwright/<slug>/`, where `<slug>` is the task's ticket id (or the current
   branch name when there is no ticket), so evidence lands grouped per ticket or branch in the gitignored `.ritus/`
   runtime namespace; cite the saved paths in the report.
6. Watch the browser console and failed network requests throughout the interactions, and record any errors together
   with the step that triggered them.
7. Assess whether the change behaves and renders as the task intends across the interactions and breakpoints, against
   the definition-of-done UI checklist (responsive breakpoints covered, states handled, layout matches intent),
   noting where it works and where it diverges.
8. Report the per-state evidence paths, the behavioral and visual assessment (works as expected, or the specific
   interactions and states that failed), and any console or network errors, so the caller can gate the result during
   verification or iterate on it during implementation.

## Handoff

- **Report:** the per-state screenshot evidence paths, the behavioral and visual assessment (whether the change works
  as intended, with the interactions and states that passed or failed), and any console or network errors applied to
  the parent skill's work, or the skip-with-warning notice when the browser capability is unavailable. The caller
  decides whether a failure is a failing gate (verification) or a prompt to iterate (implementation).
