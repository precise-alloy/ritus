# Task 002: Refuse refunds above $500.00

Level: EPIC - Depends on: 001 - Plan: docs/reviews/TL-40-review.md
Status: todo

## Goal

Refunds above $500.00 need a second approver, which TL-31 adds; until then `refund()` refuses them (TL-40).

## Acceptance

- [ ] [AC1] Refunds above $500.00 are refused with `RangeError` `Refunds above $500.00 need a second approver (TL-31)`
  until TL-31: exactly 50000 cents goes through, and 50001 cents is refused and changes nothing - a test
- [ ] [AC2] `npm run build` -> exit 0; `npm test` -> 0 failures; `npm run lint` -> `lint ok`

## Interfaces

- Produces: `REFUND_LIMIT_CENTS = 50000` in `src/refund.js`

## Starting points

- `src/refund.js` - `refund()`, from task 001; validate before any ledger call
