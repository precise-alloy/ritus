# Task 005: Record every movement in the ledger

Level: EPIC - Depends on: 001 - Plan: docs/reviews/TL-40-review.md
Status: verified

## Goal

Support needs an account's refund history (TL-40), and the ledger keeps only balances. From now on every applied
movement is recorded with its receipt id, kind, details and time; task 006 reads them.

## Acceptance

- [ ] [AC1] `ledger.apply(entries, { kind, memo })` records `{ id: 'R-<receipt number>', kind, at, memo }`, where `at`
  is the ledger clock's time as an ISO string; `ledger.movements()` resolves to every recorded movement, oldest first.
  Without options the kind is `adjustment` and the memo `{}` - a test in `test/ledger.test.js`
- [ ] [AC2] A refused `apply()` records nothing - a test
- [ ] [AC3] `transfer()`, `withdraw()` and `refund()` record their movement with kind `transfer`, `withdraw` and
  `refund`; the memo is `{ fromId, toId, amountCents, feeCents }` (withdraw: `{ accountId, amountCents, feeCents }`) -
  a test for each
- [ ] [AC4] A ledger file written before this change (no `movements`) still loads: `movements()` resolves to `[]` and
  the next `apply()` records normally - a test
- [ ] [AC5] `new Ledger(path, { now })` and `Ledger.create(path, balances, { now })` take the clock, a function
  returning a `Date`; the default is the system time - a test
- [ ] [AC6] `npm run build` -> exit 0; `npm test` -> 0 failures; `npm run lint` -> `lint ok`

## Constraints

- The movement is saved in the same write as the balances, inside `apply()`, so the two can't disagree (D-003).
- `tempLedger()` in `test/helpers.js` passes the options through; existing callers keep working.

## Interfaces

- Produces: `apply(entries, { kind = 'adjustment', memo = {} } = {})`, `movements(): Promise<Array<{ id, kind, at,
  memo }>>` and the `now` option, in `src/ledger.js`
- Consumes: `refund()` (001)

## Starting points

- `src/ledger.js:35-57` - `apply()`; the receipt number is taken just before the save
- `src/transfer.js`, `src/withdraw.js`, `src/refund.js` - the three callers of `apply()`
- `test/helpers.js` - `tempLedger()`
