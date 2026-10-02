# Task 001: Add previewFee

Level: STANDARD - Depends on: none - Plan: docs/reviews/TL-15-review.md
Status: verified

## Goal

Quote the fee a transfer or a withdrawal of a typed amount would cost, without touching any balance (TL-15, AC1-AC3).

## Acceptance

- [AC1] `previewFee('10.50', 'transfer')` returns 11 - a test in `test/fee-preview.test.js`
- [AC2] `previewFee('50.25', 'withdraw')` returns 101, and `previewFee('5', 'withdraw')` the 25-cent minimum
- [AC3] An unknown kind throws `Unknown fee kind: <kind>`; text that is not an amount throws `InvalidAmountError`
- [AC5] `npm test` -> 0 failures; `npm run lint` -> `lint ok`

## Interfaces

- Produces: `previewFee(amount: string, kind: 'transfer' | 'withdraw'): number` - the fee in integer cents

## Starting points

- `src/fees.js:5` - `computeFee(amountCents, kind)`; the plan puts `previewFee` next to it
- `src/money.js:24` - `parseAmount(input)`

## Docs

- `docs/ARCHITECTURE.md`: add the preview module to the module diagram, next to `fees.js`
