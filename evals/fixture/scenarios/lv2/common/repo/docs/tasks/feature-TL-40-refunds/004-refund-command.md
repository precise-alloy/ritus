# Task 004: Add `tl refund`

Level: EPIC - Depends on: 002, 003 - Plan: docs/reviews/TL-40-review.md
Status: verified

## Goal

Support staff run `tl refund <from> <to> <amount> [--fee]` and get the refund receipt (TL-40).

## Acceptance

- [ ] [AC1] `tl refund alice bob 10.50 --fee` prints the refund receipt from `renderRefundReceipt`, exit 0 - a test in
  `test/cli.test.js`
- [ ] [AC2] Above the limit: `tl refund alice bob 600.00` prints
  `Error: Refunds above $500.00 need a second approver (TL-31)`, exit 1 - a test
- [ ] [AC3] USAGE lists `tl refund <from> <to> <amount> [--fee]` - diff: `src/cli.js`
- [ ] [AC4] `npm run build` -> exit 0; `npm test` -> 0 failures; `npm run lint` -> `lint ok`

## Interfaces

- Consumes: `refund()` (001, with the 002 limit) and `renderRefundReceipt()` (003)

## Starting points

- `src/cli.js:15-26` - `commands`; add `refund` next to `withdraw`
