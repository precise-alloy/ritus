---
name: e2e-generator
description: Generates committed Playwright *.spec.ts tests from a task's acceptance criteria, runs them via bunx playwright test, and reads the artifacts, degrading gracefully when Playwright is unavailable
user-invocable: false
---

# E2E Generator

## When to use

This skill is exposed by ritus-ui so the ritus workflow can invoke it when available, for tasks that need end-to-end
coverage of a user journey. It complements the testing-policy test-type matrix by producing durable Playwright specs
for a full user flow (the e2e-row wiring into testing-policy is decided separately). The workflow-side wiring that
decides when to call it is decided separately.

## Prerequisite and availability check

- This skill requires Playwright installed as a project dependency, providing the `bunx playwright test` runner.
- Check availability first: confirm Playwright is present in the project (for example, a `@playwright/test`
  dependency and a Playwright config), and that the browser binary is installed.
- When Playwright or its browser binary is unavailable, skip with a warning and let the work continue, mirroring the
  build/test/lint skip pattern (a missing capability is a skip-with-warning, and stays a soft skip rather than a hard
  failure).
- Report the skip clearly so the parent skill records that e2e generation was not run.

## Steps

1. Read the ritus-ui preview config from `.ritus/ritus-ui.config.yml`, and skip with a warning when the file is absent: the dev-server command, the base URL, and
   the breakpoints.
2. Derive the user journey from the task's behavior and acceptance criteria: the entry route, the steps a user
   takes, and the observable outcome that proves the criteria are met. When the entry page URL is unclear or
   ambiguous, stop and ask the user for it (the base URL points only at the app root). When dispatched and unable to
   reach the user, report BLOCKED naming the page URL needed, rather than guessing the route.
3. Write committed Playwright `*.spec.ts` tests at the project's e2e test location, encoding the journey as
   navigation, interaction, and assertion steps against the configured base URL.
4. Run the specs via `bunx playwright test`, starting the dev server with the configured command when it is not
   already running.
5. Read the run results and artifacts (the report, traces, and screenshots) and summarize pass or fail with the
   failing test names and artifact paths.
6. Report the committed spec paths, the run outcome, and the artifact paths.

## Handoff

- **Report:** the committed `*.spec.ts` paths, pass or fail with failing test names, and the artifact paths applied
  to the parent skill's work, or the skip-with-warning notice when Playwright is unavailable.
