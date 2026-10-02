# Fix: review round 1 on PR #7

Level: STANDARD - Depends on: none - Plan: docs/reviews/TL-27-review.md
Status: implemented

## Goal

Address the two comments kept from round 1 of the review of PR #7 (TL-27 refunds):

- `src/refund.js:9` @mai.tran: "The fees account may go negative by design, so `refund(ledger, 'alice', 'fees', 2000)`
  pays alice money the fees account never had. A refund shouldn't have the fees account on either side."
- `src/cli.js:28` @quan.le: "`tl refund alice bob 10.50 --fees` quietly refunds without the fee. Reject an option you
  don't know instead of guessing."

## Acceptance

- [ ] [AC1] `refund()` refuses the fees account on either side: `refund(ledger, 'alice', 'fees', 2000)` and
  `refund(ledger, 'fees', 'bob', 2000)` both throw `RangeError` `The fees account cannot be a refund party` and change nothing - a test
  in `test/refund.test.js`
- [ ] [AC2] `tl refund` rejects an option it doesn't know: `tl refund alice bob 10.50 --fees` prints
  `Error: Unknown option --fees`, exits 1, and moves nothing; `--fee` and no option keep working - a test in
  `test/cli.test.js`
- [ ] [AC3] `npm run build` -> exit 0; `npm test` -> 0 failures; `npm run lint` -> `lint ok`

## Starting points

- `src/refund.js:9-18` - `refund()`'s checks, all before its one `ledger.apply()` call
- `src/cli.js:28-32` - the `refund` command
