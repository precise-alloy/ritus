# Task 002: Add `tl refund`

Level: STANDARD - Depends on: 001 - Plan: docs/reviews/TL-27-review.md
Status: implemented

## Goal

Support staff run `tl refund <from> <to> <amount> [--fee]` to undo a mistaken transfer (TL-27).

## Acceptance

- [ ] [AC1] `tl refund alice bob 20.00` prints `Refund R-1001: $20.00 back to alice`, exit 0 - a test in
  `test/cli.test.js`
- [ ] [AC2] `tl refund alice bob 10.50 --fee` prints `Refund R-<n>: $10.50 and $0.11 fee back to alice` - a test
- [ ] [AC3] Above the limit: `tl refund alice bob 600.00` prints
  `Error: Refunds above $500.00 need a second approver (TL-31)`, exit 1 - a test
- [ ] [AC4] USAGE lists `tl refund <from> <to> <amount> [--fee]` - diff: `src/cli.js`
- [ ] [AC5] `npm run build` -> exit 0; `npm test` -> 0 failures; `npm run lint` -> `lint ok`

## Interfaces

- Consumes: `refund(ledger, fromId, toId, amountCents, { refundFee })` from `src/refund.js` (task 001)

## Starting points

- `src/cli.js:15-26` - `commands`; add `refund` next to `withdraw`
- Pattern: Add a CLI command (`docs/ARCHITECTURE.md`)
