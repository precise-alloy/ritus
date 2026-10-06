# Task 001: Implement TLW-23 transaction-list polish and empty state.

Level: STANDARD - Depends on: none - Plan: docs/reviews/TLW-23-review.md
Status: implemented

## Goal

Staff can scan account activity quickly, and an account with no transactions gets a clear next step instead of an empty table.

## Acceptance

- [ ] [AC1] Account transaction rows are newest first - browser check on `/accounts/checking` with seed data
- [ ] [AC2] Amounts are signed and colored by direction: incoming positive, outgoing negative - browser/computed-style check
- [ ] [AC3] An account with no transactions shows the text `No transactions yet` and a link to `/transfer`, with no table rendered - browser check on `/accounts/travel`
- [ ] [AC4] `npm run build`, `npm test` and `npm run lint` exit 0
- [ ] [AC5] At `/accounts/checking`, viewports 375px, 639px, 640px, 1023px, 1024px, 1280px and 1440px, default state: transaction rows remain readable, use the documented breakpoints, and create no document-level horizontal overflow - check: browser geometry and document scroll width at each width
- [ ] [AC6] At `/accounts/checking`, viewports 375px and 1280px, default state: signed amount colors meet WCAG 2.2 AA contrast and use project tokens - check: browser computed styles and contrast measurement
- [ ] [AC7] At `/accounts/travel`, viewports 375px and 1280px, empty state: the message and transfer link are visible, the link's focus indicator is visible by keyboard, and axe reports no violations for `main` - check: browser keyboard, accessibility snapshot and axe scope `main`
- [ ] [AC8] The list and the empty state use the project's tokens from `src/styles/tokens.css` for colour, spacing, radius and type, with no raw values where a token exists; check by browser computed styles against the token values, and by the diff

## Constraints

- Follow `docs/PROJECT_CONTEXT.md`: runtime dependency-free browser modules, design tokens, accessible labels and the documented breakpoints.
- Expected values in tests and browser checks come from the ticket, seed data or design values, not from re-running the production code.

## Interfaces

- Consumes: existing TinyLedger Web routes and seed data.
- Produces: the UI behavior described in the acceptance lines for TLW-23.

## Non-goals

- Authentication, long-term data storage, account settings and unrelated route behavior.

## Starting points

- `docs/PROJECT_CONTEXT.md` - commands, breakpoints and frontend conventions.
- `src/main.js` - route rendering.
- `src/components/card.js` - shared card component.
- `src/styles/tokens.css`, `src/styles/app.css` - tokens and layout styles.
