# Task 001: Add `tl balances`

Level: SIMPLE - Depends on: none - Plan: none
Status: implemented

## Goal

Support staff want every account's balance at once instead of running `tl balance` per account (TL-35). Finance has
mentioned they will eventually want these balances as CSV for their spreadsheets.

## Acceptance

- [ ] [AC1] `tl balances` prints one line per account, `<account> <amount>`, sorted by account id - a test in
  `test/cli.test.js`: with alice 10000, bob 5000 and carol 250 cents it prints `alice $100.00`, `bob $50.00`,
  `carol $2.50`, `fees $0.00`
- [ ] [AC2] `Ledger.listBalances()` resolves to `[{ accountId, balanceCents }]` sorted by account id - a test in
  `test/ledger.test.js`
- [ ] [AC3] USAGE lists `tl balances` - diff: `src/cli.js`
- [ ] [AC4] `npm run build` -> exit 0; `npm test` -> 0 failures; `npm run lint` -> `lint ok`

## Starting points

- `src/ledger.js:8` - `Ledger`, the only code that reads the ledger file (D-003); add the method here
- `src/cli.js:15-26` - `commands`; add `balances` next to `withdraw`
- Pattern: Add a CLI command (`docs/ARCHITECTURE.md`)
