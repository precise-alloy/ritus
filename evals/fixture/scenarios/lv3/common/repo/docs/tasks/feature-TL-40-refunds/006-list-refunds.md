# Task 006: List an account's refunds

Level: EPIC - Depends on: 005 - Plan: docs/reviews/TL-40-review.md
Status: verified

## Goal

Support looks up the refunds an account took part in (TL-40), whichever side of the refund it was on.

## Acceptance

- [ ] [AC1] `listRefunds(ledger, { accountId })` resolves to every refund the account took part in - as the account
  the money went back to (`fromId`) or the account it came from (`toId`) - newest first - a test in
  `test/refunds.test.js`
- [ ] [AC2] Each item is `{ id, at, fromId, toId, amountCents, feeCents }`, taken from the refund's movement - a test
- [ ] [AC3] Transfers and withdrawals are not listed; an account without refunds gets `[]` - a test
- [ ] [AC4] An unknown account is refused with `AccountNotFoundError` - a test
- [ ] [AC5] `npm run build` -> exit 0; `npm test` -> 0 failures; `npm run lint` -> `lint ok`

## Interfaces

- Produces: `listRefunds(ledger, { accountId }): Promise<Array<{ id, at, fromId, toId, amountCents, feeCents }>>` in
  `src/refunds.js`
- Consumes: `ledger.movements()` (005)

## Starting points

- `src/ledger.js` - `movements()`, and `getBalance()`, which throws `AccountNotFoundError`
