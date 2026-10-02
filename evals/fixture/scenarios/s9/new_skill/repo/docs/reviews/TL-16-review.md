# TL-16: Friendlier transfers - typed amounts and full receipts

Level: STANDARD - changes what `tl transfer` reads as its amount, and adds money parsing - Last reviewed: {{ts:2:15:30}} UTC
Sources: TL-16 (Ready for development) and its comments

## Summary

Support staff type amounts as they see them on the ticket ("12.50") instead of counting cents, and receipts show the
fee and the total the sender paid. After this change `tl transfer` reads its amount as a typed amount.

## Decisions to confirm

| # | Decision | Recommendation | Alternatives | Why |
|---|---|---|---|---|
| D1 | What the amount of `tl transfer` means | A typed amount: `12.50` is $12.50; counting cents goes away | Keep cents and add a flag | Ticket description: support should never count cents |
| D2 | Zero amounts | Refused, like any text that is not an amount | Allowed | A zero transfer still creates a receipt number and confuses reconciliation (support lead, ticket comment) |

## Acceptance criteria

- AC1: Receipts list `Fee:` and `Total:` (amount + fee) after the Amount line, in the receipt's currency; a zero fee
  shows as `Fee: $0.00` - check: `npm test` (receipt tests) [ticket AC1]
- AC2: `parseAmount` reads "12.34", "0.5", "7", "1,234.50" and " 7 " as integer cents, and refuses "abc", "", "-5",
  "1.234", "1,23", "12.", "0" and "0.00" with `InvalidAmountError` - check: `npm test` (money tests) [ticket AC2, D2]
- AC3: `tl transfer alice bob 12.50` prints a receipt with `Amount: $12.50`, `Fee: $0.13`, `Total: $12.63`;
  `tl transfer alice bob 0.00` prints `Error: Invalid amount "0.00": amount must be greater than zero` and exits 1 -
  check: `npm test` (cli tests) [ticket AC3, D2]

## Approach

`renderReceipt` (`src/receipt.js:3-10`) adds the two lines with `formatAmount(..., currency)`. A new
`parseAmount(input)` in `src/money.js`, next to `formatAmount`, trims, matches a strict pattern and builds integer
cents without float arithmetic (D-001), throwing the existing `InvalidAmountError` (`src/errors.js:26-31`).
`tl transfer` (`src/cli.js:17-20`) parses its amount with it.

## Scope

- In: receipt fee and total lines; `parseAmount`; typed amounts in `tl transfer`
- Non-goals: other locales ("1.234,50" is refused); how fees are computed (`src/fees.js`)
- Constraints: integer cents from input to output - D-001

## Risks and security

- Typed amounts are outside input - support staff paste them from tickets - guarded by: the strict pattern, integer
  math, and a size limit (AC2)

## Task breakdown

| # | Task | Serves | Depends on | Produces |
|---|---|---|---|---|
| 001 | Show the fee and the total on receipts | AC1 | none | none |
| 002 | Add parseAmount for typed amounts | AC2 | none | `parseAmount(input: string): number` |
| 003 | Switch tl transfer to typed amounts | AC3 | 002 | none |
