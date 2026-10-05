# Task 001: Implement the TLW-21 summary card on `/accounts`.

Level: STANDARD - Depends on: none - Plan: docs/reviews/TLW-21-review.md
Status: implemented

## Goal

Staff can see the portfolio total before the account list. The card uses the shared card component and the design tokens so it stays consistent with the rest of TinyLedger Web.

## Acceptance

- [ ] [AC1] `/accounts` shows a summary card for the Figma design `https://www.figma.com/design/TLWEB0001/TinyLedger-Web?node-id=12-34` - browser check at 375px, 768px and 1280px
- [ ] [AC2] The card has 16px padding, 16px label-value gap, 8px radius, `var(--color-surface)` fill and a 1px `var(--color-border)` border - browser/computed-style check
- [ ] [AC3] The label is `Total balance` at 14px/20px, regular, `var(--color-text-muted)`; the value is 24px/32px, semibold, `var(--color-text)` - browser/computed-style check
- [ ] [AC4] With the seed data, the value is exactly `$12,345.67` - browser text check
- [ ] [AC5] The card has the accessible name `Total balance` - accessibility tree or locator check
- [ ] [AC6] The implementation reuses `card()` from `src/components/card.js`, adds no raw color literals, and uses tokens only - code review plus browser probe
- [ ] [AC7] The card fills the content column and creates no horizontal overflow from 375px through desktop widths - browser check
- [ ] [AC8] `npm run build`, `npm test` and `npm run lint` exit 0

## Constraints

- Follow `docs/PROJECT_CONTEXT.md`: runtime dependency-free browser modules, design tokens, accessible labels and the documented breakpoints.
- Expected values in tests and browser checks come from the ticket, seed data or design values, not from re-running the production code.

## Interfaces

- Consumes: existing TinyLedger Web routes and seed data.
- Produces: the UI behavior described in the acceptance lines for TLW-21.

## Non-goals

- Authentication, long-term data storage, account settings and unrelated route behavior.

## Starting points

- `docs/PROJECT_CONTEXT.md` - commands, breakpoints and frontend conventions.
- `src/main.js` - route rendering.
- `src/components/card.js` - shared card component.
- `src/styles/tokens.css`, `src/styles/app.css` - tokens and layout styles.
