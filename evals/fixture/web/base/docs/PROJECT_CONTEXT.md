# Project Context - TinyLedger Web

## Identity

| Field | Value |
|---|---|
| Project | `tinyledger-web` |
| Language | `JavaScript (Node.js 22+, ESM)` |
| Framework | `none (browser ES modules, node:test)` |
| Team size | `3` |

## Source layout

| Area | Paths |
|---|---|
| Browser entry | `src/main.js` |
| Components | `src/components/` |
| Shared library | `src/lib/` |
| Styles | `src/styles/tokens.css`, `src/styles/app.css` |
| Static shells | `public/` |
| Seed data | `data/accounts.json` |
| Scripts | `scripts/` |
| Tests | `test/` |
| Generated/ignored | `.cache/`, `dist/`, `.playwright-cli/`, `.ritus/` |

## Build commands

| Command | What |
|---|---|
| `npm run dev` | Serve the app at the configured URL, `http://localhost:4173/` |
| `npm run build` | Syntax-check scripts and browser modules, then write `dist/build-info.json` |
| `N/A` | Typecheck |
| `npm test` | Run the node:test suite and write `.cache/junit.xml` |
| `npm run lint` | Run project lint rules and write `.cache/lint-report.json` |

## Authentication

Auth pattern: `none - internal staff demo, read-only seed data`.

## Frontend conventions

- Colors, spacing, radius and type values come only from `src/styles/tokens.css`.
- Reuse components from `src/components/` before adding page-specific markup.
- Responsive breakpoints are 640px and 1024px; supported widths are 375px through 1440px.
- Accessibility target is WCAG 2.2 AA.
- Browser support covers current Chromium, Firefox and Safari.
- Browser code does not write to the console in normal operation.

## Testing

`node:test` with `node:assert/strict`. Test files live in `test/` and are named `<area>.test.js`.

## Team conventions

| Field | Value |
|---|---|
| Git platform | `GitHub` |
| Git workflow | `PR-based` |
| Workflow owner | `developer` |
| Ticket format | `TLW-123` |
| QA mode | `browser smoke plus automated tests` |
| EPIC memory expiry | `30` days |

Branch format:

`feature/TLW-<number>-<slug>` or `bugfix/TLW-<number>-<slug>`

Tasks path convention:

`docs/tasks/{branch-slug}/NNN-<name>.md`

PR reviewers: `@mai.tran`
Default base branch: `main`
Traceability policy: `ticket key as the commit scope, e.g. feat(TLW-12): ...`

## Documentation layout

| Purpose | Path |
|---|---|
| Ticket reviews | `docs/reviews/` |
| Architecture | `docs/ARCHITECTURE.md` |
| Decisions | `docs/DECISIONS.md` |
| Lessons | `docs/LESSONS.md` |
| Module docs | `docs/modules/` |
| Task files | `docs/tasks/` |

## Requirement source precedence

1. Explicit user instruction in the current conversation
2. Latest authoritative ticket comments or discussion notes
3. Ticket acceptance criteria
4. Ticket description
5. Existing review/task files

## AI tools

`Claude Code, GitHub Copilot CLI`

## Model routing

`model_routing: session` - project work uses the session's configured model routing.

## Module map

| Module | Responsibility |
|---|---|
| `src/main.js` | Page rendering and transfer form validation |
| `src/components/card.js` | Reusable card component for summary content |
| `src/lib/money.js` | Integer-cent amount formatting |
| `src/lib/accounts.js` | Account lookup and balance totals |
| `scripts/serve.mjs` | Local HTTP server and JSON endpoints |

## Project-specific constraints

- Money is integer cents in data and shared logic; presentation uses `formatAmount()`.
- The app is dependency-free at runtime and serves browser modules as files.
- Keep layout values tied to the token file and the documented breakpoints.
