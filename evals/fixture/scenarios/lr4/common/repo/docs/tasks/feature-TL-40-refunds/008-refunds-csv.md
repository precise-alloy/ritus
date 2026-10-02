# Task 008: Add `tl refunds --csv`

Level: EPIC - Depends on: 007 - Plan: docs/reviews/TL-40-review.md
Status: verified

## Goal

Finance imports an account's refunds into a spreadsheet (TL-40).

## Acceptance

- [ ] [AC1] `renderRefundsCsv(refunds)` returns the header `id,date,back_to,from,amount,fee`, then one row per refund
  in the order given, amounts as plain decimals: `R-1004,2026-09-02,alice,bob,20.00,0.20`; no fee is `0.00` - a test
  in `test/report.test.js`
- [ ] [AC2] A field holding a comma or a double quote is wrapped in double quotes, with inner quotes doubled
  (RFC 4180): `acme, inc` -> `"acme, inc"` - a test
- [ ] [AC3] Without refunds it is the header line alone - a test
- [ ] [AC4] `tl refunds <account> --csv` prints that CSV, exit 0; USAGE shows `tl refunds <account> [--csv]` - a test
  in `test/cli.test.js`
- [ ] [AC5] `npm run build` -> exit 0; `npm test` -> 0 failures; `npm run lint` -> `lint ok`

## Interfaces

- Produces: `renderRefundsCsv(refunds): string` in `src/report.js`

## Starting points

- `src/report.js` - `renderRefundReport()`, from 007
- `src/cli.js` - the `refunds` command, from 007
