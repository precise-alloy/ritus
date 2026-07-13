# ritus-ui

`ritus-ui` is an opt-in companion plugin for the ritus workflow that adds frontend/UI capabilities. It contributes a
bundled Playwright MCP and browser-driven skills that the ritus workflow invokes when available, and skips with a
warning when they are not. It is independent from core ritus and lives in its own `ritus-ui/` folder.

## Install and enable

- `ritus-ui` is opt-in and stays disabled until you enable it, so core ritus sessions carry none of its browser
  tooling by default.
- Enable the plugin in your host to load its skills and the bundled Playwright MCP.
- Once enabled, the Playwright MCP tools appear in the session and the SessionStart hook prepares the browser binary.

## Browser prerequisite

- bunx is required to install the browser binary used for visual verification.
- On session start, a hook installs Chromium once into the plugin data dir using
  `bunx playwright install chromium` with `PLAYWRIGHT_BROWSERS_PATH` set to that dir.
- The install is idempotent: a marker file guards the download so later sessions skip it.
- The install runs synchronously during the SessionStart hook and streams Playwright's install output. It is
  time-bounded, so a slow or stalled install is capped and degrades to a warning. When `bunx` is missing, the install
  fails, or the cap is reached, the hook prints a warning and lets the session continue.

## Capabilities

`ritus-ui` provides these skills; the ritus workflow invokes each when available and skips with a warning otherwise:

- `ui-preview` - visual QA: drive the change's user interactions in a real browser at each breakpoint, capture
  evidence at every meaningful state, watch the console, and confirm it behaves and renders as intended. The workflow
  iterates on issues while implementing and gates a visual DONE WHEN while verifying.
- `e2e-generator` - derive a user journey from acceptance criteria, write committed Playwright end-to-end specs, run
  them via `bunx playwright test`, and report the results.
- `visual-regression` - compare a route against stored baselines with Playwright `toHaveScreenshot` to catch visual
  drift, with an explicit reviewed baseline-update path.
- `a11y-audit` - run an axe-core accessibility audit against the rendered route, mapped to the a11y items in the
  ritus definition-of-done.
- `design-context` - pull Figma design references in as visual acceptance criteria for the workflow.

## Preview config

The visual skills read a per-project config file, `.ritus/ritus-ui.config.yml`. It describes how to
render your app:

- `dev_server` - the command that starts the local dev server.
- `base_url` - the URL where the dev server serves the app (for example, `http://localhost:3000`).
- `breakpoints` - the viewport widths, in px, to render and verify at (for example, 375 mobile and 1280 desktop).

Copy the shipped example (`ritus-ui.config.example.yml`) to `.ritus/ritus-ui.config.yml` in your project root and fill it in:

```yaml
dev_server: "npm run dev"
base_url: "http://localhost:3000"
breakpoints:
  - 375
  - 1280
```

This config is owned by ritus-ui and lives in your project, not in the core ritus profile. When the file is absent,
the visual skills skip with a warning.

## Evidence output

`ui-preview` saves the screenshots it captures under `.ritus/playwright/<slug>/`, where `<slug>` is the task's ticket
id (or the current branch name when there is no ticket). Evidence stays grouped per ticket or branch in the gitignored
`.ritus/` runtime namespace. Playwright's own baseline and report artifacts (from `visual-regression` and
`e2e-generator`) stay in their Playwright-configured locations.

## Graceful degradation

Every ritus-ui capability checks availability first. When the plugin is disabled, the Playwright MCP tools are
absent, or the browser binary is not installed, the workflow skips the capability with a warning and continues,
matching the build/test/lint skip pattern. A missing capability stays a soft skip rather than a hard failure.
