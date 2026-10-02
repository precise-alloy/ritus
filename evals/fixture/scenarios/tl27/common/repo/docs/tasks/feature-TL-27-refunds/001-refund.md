# Task 001: Add refund()

Level: STANDARD - Depends on: none - Plan: docs/reviews/TL-27-review.md
Status: todo

## Goal

Support staff can undo a mistaken transfer (TL-27): the transferred amount goes back to the sender, and when the
mistake was ours the sender also gets the transfer fee back. The `tl refund` command comes in task 002.

## Acceptance

- [ ] [AC1] `refund(ledger, 'alice', 'bob', 2000)` moves 2000 cents from bob back to alice and leaves the fees account
  unchanged - a test in `test/refund.test.js`
- [ ] [AC2] With `{ refundFee: true }`, alice also gets back the fee `computeFee(amountCents, 'transfer')` charges
  (20 cents for 2000), taken from the fees account - a test
- [ ] [AC3] All or nothing: when bob's balance is below the amount, it throws `InsufficientFundsError` and no balance
  changes - a test
- [ ] [AC4] It refuses `fromId === toId`, and an amount that is not a positive whole number of cents, with
  `RangeError`, changing nothing - a test
- [ ] [AC5] It resolves to `{ id: 'R-<receipt number>', fromId, toId, amountCents, feeCents }`, where `feeCents` is the
  fee refunded (0 without `refundFee`) - a test
- [ ] [AC6] `npm run build` -> exit 0; `npm test` -> 0 failures; `npm run lint` -> `lint ok`

## Constraints

- All balance changes of a refund go through one `ledger.apply()` call, so a refund is all or nothing (D-003,
  `docs/ARCHITECTURE.md` "Add a money-moving operation").
- Fees round half-up to the cent (D-002): the refunded fee is exactly what `computeFee` charges for that amount.
- Expected values in tests are literals, not the fee formula written out again (L-002).

## Interfaces

- Produces: `refund(ledger, fromId, toId, amountCents, { refundFee = false } = {}): Promise<{ id, fromId, toId,
  amountCents, feeCents }>` in `src/refund.js`. `fromId` and `toId` name the original transfer's sender and recipient.

## Non-goals

- The `tl refund` command (task 002), partial refunds, and looking up the original transfer: support types the parties
  and the amount from the receipt.
- Any change to the fee schedule or to `transfer()`.

## Starting points

- `src/transfer.js:5-19` - the operation a refund reverses; mirror its shape
- `src/ledger.js:35-57` - `apply(entries)` is all or nothing; the fees account may go negative (`src/ledger.js:44`)
- `test/transfer.test.js`, `test/helpers.js` - `tempLedger()` for tests that touch balances
- Pattern: Add a money-moving operation (`docs/ARCHITECTURE.md`)
