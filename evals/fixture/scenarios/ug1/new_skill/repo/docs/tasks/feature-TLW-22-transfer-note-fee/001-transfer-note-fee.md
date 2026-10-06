# Task 001: Implement the TLW-22 transfer note and fee preview.

Level: STANDARD - Depends on: none - Plan: docs/reviews/TLW-22-review.md
Status: verified

## Goal

Staff can write an optional note before submitting a transfer and see the fee rule next to the form on wide screens.

## Acceptance

- [ ] [AC1] `/transfer` has a note field with a visible label and a maximum length of 140 characters - browser and DOM check
- [ ] [AC2] `transferFee(2550)` returns 26, `transferFee(2549)` returns 25, and the minimum fee is 25 cents - unit tests with literal expected values
- [ ] [AC3] The fee preview panel sits beside the form from 1024px and below the form under 1024px - browser geometry check at 375px, 768px and 1280px
- [ ] [AC4] `/transfer` has no horizontal scrolling at 375px - browser check
- [ ] [AC5] The transfer page meets WCAG 2.2 AA for the changed controls - axe/browser check
- [ ] [AC6] `npm run build`, `npm test` and `npm run lint` exit 0
- [ ] [AC7] At `/transfer`, viewports 375px, 639px, 640px, 1023px, 1024px, 1280px and 1440px, default state: the form and fee preview use the documented breakpoints and maintain no document-level horizontal overflow - check: browser geometry and document scroll width at each width
- [ ] [AC8] At `/transfer`, viewport 375px, keyboard state: the note field has a visible programmatic label, focus remains visible, and tab order follows the form before submit - check: browser keyboard and accessibility snapshot
- [ ] [AC9] At `/transfer`, viewports 375px and 1280px, default state: changed controls and fee-preview text meet WCAG 2.2 AA contrast and axe reports no violations for `main` - check: browser contrast measurement and axe scope `main`
- [ ] [AC10] The note field and fee preview use the project's tokens from `src/styles/tokens.css` for colour, spacing, radius and type, with no raw values where a token exists; check by browser computed styles against the token values, and by the diff

## Constraints

- Follow `docs/PROJECT_CONTEXT.md`: runtime dependency-free browser modules, design tokens, accessible labels and the documented breakpoints.
- Expected values in tests and browser checks come from the ticket, seed data or design values, not from re-running the production code.

## Interfaces

- Consumes: existing TinyLedger Web routes and seed data.
- Produces: the UI behavior described in the acceptance lines for TLW-22.

## Non-goals

- Authentication, long-term data storage, account settings and unrelated route behavior.

## Starting points

- `docs/PROJECT_CONTEXT.md` - commands, breakpoints and frontend conventions.
- `src/main.js` - route rendering.
- `src/components/card.js` - shared card component.
- `src/styles/tokens.css`, `src/styles/app.css` - tokens and layout styles.
