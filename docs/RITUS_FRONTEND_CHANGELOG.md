# Ritus Frontend changelog

All notable changes to the `ritus-frontend` plugin, newest first. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).
The user guide is [RITUS_FRONTEND.md](./RITUS_FRONTEND.md).

## [1.0.0]

A rewrite. Ritus Frontend is now a standard that Ritus loads into the steps it already runs, instead of its own planning
steps and gates. It ships from the Ritus marketplace, `precise-alloy/ritus`, at `plugins/ritus-frontend`. Before this
release both marketplaces served 0.1.0. If you are coming from it, you also get everything 0.2.0 changed, and you no
longer need the Playwright MCP server that 0.1.0 bundled.

**Breaking:** the 0.1.0 and 0.2.0 skill names are removed, and `e2e-spec.md` and the gates before `pr-review` are
replaced by Acceptance checks inside `verify-task` and `pr-review`.

**Migration:** see [Migrating from 0.2.0](./RITUS_FRONTEND.md#migrating-from-020), which also applies to 0.1.0. Install
`ritus-frontend@precise-alloy-marketplace` from `precise-alloy/ritus` in place of
`ritus-frontend@ritus-frontend-marketplace`, and put the UI contract in task Acceptance.

### Added

- `frontend` skill, the standard Ritus loads for UI work. It covers UI Acceptance (route or component x viewport x
  state, each line checked in a browser: the widths in `docs/FRONTEND.md`, both sides of each touched breakpoint,
  WCAG 2.2 AA contrast, visible labels, keyboard, axe with its scope, design tokens), design-system and Figma use,
  browser evidence, and what counts as a UI defect. Its references are `plan.md`, `design-system.md`, `figma.md`,
  `browser.md`, and `verify.md`.
- `ui-verify` skill: a standalone, read-only check of a running page or component - layout at a width, accessibility,
  console errors, network failures, or design match. It reports and changes no files.
- Five `load` integrations in `ritus-companion.json`, all for `frontend`: `ticket-review` task generation, `execute-task`,
  `verify-task`, `pr-review`, and `wrap-up`. The wrap-up review with the user in a host browser is advisory, not a gate.
  These use the companion load points of Ritus 3.0.0 ([COMPANION_PLUGINS.md](./COMPANION_PLUGINS.md)).
- Two browser roles. `playwright-cli` (`npx playwright cli` with Playwright 1.63 or newer, or `@playwright/cli`) runs
  independent checks, including from subagents. Host browsers - VS Code browser tools, the GitHub Copilot app's browser
  canvas, Claude in Chrome - serve work with the user.
- axe-core 4.13.0 (MPL-2.0), vendored in the `frontend` skill's `assets/` as a fallback when the project has no axe.
- `docs/FRONTEND.md` in the consuming project: dev command, base URL, widths, breakpoints, design-system sources, login
  or storage-state setup, and browser notes. `frontend` creates it only from facts the user confirms.
- The user guide, [RITUS_FRONTEND.md](./RITUS_FRONTEND.md): install, supported hosts, browsers, command approvals,
  Figma, and migration from 0.2.0.

### Changed

- UI defects that `verify-task` or `pr-review` find go through Ritus's normal fix loop. The main thread shows the user
  the findings with evidence before it dispatches a fix.
- Figma: a node-scoped Figma URL in the task replaces `CONTEXT` `figma:` markers. `frontend` uses the official Figma
  plugin, Figma MCP, or the REST API when available, and the project design system when none is.
- `precise-alloy/ritus-frontend` now points to the Ritus marketplace.

### Removed

- The `e2e-plan`, `figma-intake`, `figma-implement`, `visual-verify`, and `a11y-verify` skills.
- `e2e-spec.md`, the `CONTEXT` `figma:` markers, and the blocking `VERIFY: PASS` and `A11Y: PASS` gates before
  `pr-review`.
- The Playwright MCP requirement and its `.ritus/screenshot` output folder.
- Copilot CLI as a supported host.

## [0.2.0] - unreleased

Never published to a marketplace; it was developed on a branch of `precise-alloy/ritus-frontend` and is the baseline
1.0.0 was measured against.

**Breaking:** MCP servers are no longer bundled with the plugin. The bundled `playwright` server is removed; add
`playwright` (and `figma`, for the Figma skills) to your project's own `.mcp.json`. The 0.2.0 README's "MCP server
setup" section described the expected configuration.

### Added

- `figma-intake`, `figma-implement`, and `a11y-verify` skills, with Figma MCP use.

### Changed

- Consistent skill verdicts: `figma-intake` reports `DONE` on success, and `e2e-plan` reports `DONE` with the spec path.

## [0.1.0] - 2026-08-04

Initial release: the `e2e-plan` and `visual-verify` skills, with a bundled Playwright MCP server writing to
`.ritus/screenshot`.
