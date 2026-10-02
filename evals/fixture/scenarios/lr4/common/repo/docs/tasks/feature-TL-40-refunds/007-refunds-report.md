# Task 007: Add `tl refunds`

Level: EPIC - Depends on: 004, 006 - Plan: docs/reviews/TL-40-review.md
Status: verified

## Goal

Support staff run `tl refunds <account>` to see an account's refunds with totals (TL-40).

## Acceptance

- [ ] [AC1] `renderRefundReport(accountId, refunds)` returns `Refunds for <account>`, then one line per refund in the
  order given: `<id>  <date>  <back to> <- <from>  <amount>`, plus `  fee <fee>` when a fee was returned; `<date>` is
  the refund's UTC day (`YYYY-MM-DD`) - a test in `test/report.test.js`
- [ ] [AC2] The last line counts the refunds and totals their amounts and returned fees:
  `2 refunds, $25.00 back, $0.20 fees`; one refund reads `1 refund, ...` - a test
- [ ] [AC3] An account without refunds gets `No refunds for <account>` - a test
- [ ] [AC4] `tl refunds <account>` prints that report for `listRefunds()`'s result, exit 0; USAGE lists
  `tl refunds <account>` - a test in `test/cli.test.js`
- [ ] [AC5] `npm run build` -> exit 0; `npm test` -> 0 failures; `npm run lint` -> `lint ok`

## Interfaces

- Produces: `renderRefundReport(accountId, refunds): string` in `src/report.js`
- Consumes: `listRefunds()` (006)

## Starting points

- `src/cli.js` - `commands`; add `refunds` next to `refund`
- `src/money.js` - `formatAmount()`
