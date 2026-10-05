# TLW-23: Transactions polish

Level: STANDARD - one frontend task - Last reviewed: 2026-10-05 04:48 UTC
Sources: TLW-23 (In Progress), product request for TinyLedger Web

## Summary

Polish account transaction lists with newest-first ordering, signed amounts and a useful empty state.

## Decisions to confirm

| # | Decision | Recommendation | Alternatives | Why |
|---|---|---|---|---|
| D1 | Implementation scope | One task on branch `feature/TLW-23-transactions-polish` | Split by tests and UI | The change is contained to the existing route and shared helpers. |

## Acceptance criteria

- AC1: Transaction lists are readable and the empty account state has copy and a transfer link. - check: the task acceptance and the browser checks pass [TLW-23]
- AC2: Existing build, test and lint commands stay green - check: `npm run build`; `npm test`; `npm run lint` [Project context]

Test data and setup: the seed accounts in `data/accounts.json`; TinyLedger Web supports widths from 375px through 1440px with breakpoints at 640px and 1024px.

## Approach

Reuse the existing browser modules, components and design tokens. Validate behavior with the project commands and browser checks at 375px, 768px and 1280px.

## Scope

- In: Implement TLW-23 transaction-list polish and empty state.
- Non-goals: unrelated routes, backend persistence, authentication and changes outside TinyLedger Web.
- Constraints: follow `docs/PROJECT_CONTEXT.md` frontend conventions: tokens for colors/spacing/type, component reuse, WCAG 2.2 AA and no console noise.

## Affected areas

- `src/main.js` - route rendering and page state.
- `src/components/` - reuse existing components before adding markup.
- `src/styles/tokens.css`, `src/styles/app.css` - design tokens and layout styles.

## Task breakdown

| # | Task | Serves | Depends on | Produces |
|---|---|---|---|---|
| 001 | Implement TLW-23 transaction-list polish and empty state. | AC1, AC2 | none | `feature-TLW-23-transactions-polish/001-transactions-polish.md` |
