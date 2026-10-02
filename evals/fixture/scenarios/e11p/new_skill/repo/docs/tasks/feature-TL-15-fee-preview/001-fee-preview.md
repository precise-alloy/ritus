# Task 001: Add a fee preview command

Level: SIMPLE - Depends on: none - Plan: none

## Goal

Support staff can quote what a transfer or a withdrawal will cost before running it (TL-15):
`tl fee <amount> <transfer|withdraw>` prints the fee and changes no balance.

## Acceptance

- [ ] Transfer fee - `node src/cli.js fee 10.50 transfer` -> `Fee: $0.11`, exit 0
- [ ] Withdrawal fee - `node src/cli.js fee 50.25 withdraw` -> `Fee: $1.01`, exit 0
- [ ] Unknown kind - `node src/cli.js fee 10 foo` -> `Error: Unknown fee kind: foo`, exit 1
- [ ] USAGE lists `tl fee <amount> <transfer|withdraw>` - diff: the USAGE text in `src/cli.js`
- [ ] `npm run build` -> exit 0; `npm test` -> 0 failures; `npm run lint` -> `lint ok`

## Starting points

- `src/cli.js:15-26` - `commands`; add `fee` next to `withdraw`
- `src/fees.js:5` - `computeFee(amountCents, kind)`
- Pattern: Add a CLI command
