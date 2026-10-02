# Task 003: Switch tl transfer to typed amounts

Level: STANDARD - Depends on: 002 - Plan: docs/reviews/TL-16-review.md
Status: todo

## Goal

`tl transfer alice bob 12.50` moves $12.50 and prints the receipt with its fee and total.

## Acceptance

- [ ] Typed amount - on a fresh ledger, `tl transfer alice bob 12.50` prints a receipt with `Amount: $12.50`,
  `Fee: $0.13`, `Total: $12.63` - `npm test` (cli tests)
- [ ] Zero refused - `tl transfer alice bob 0.00` prints `Error: Invalid amount "0.00": amount must be greater than
  zero` and exits 1 - `npm test` (cli tests)
- [ ] USAGE shows `tl transfer <from> <to> <amount>` - diff: the USAGE text in `src/cli.js`
- [ ] `npm run build` -> exit 0; `npm test` -> 0 failures; `npm run lint` -> `lint ok`

## Constraints

- Parse the amount with `parseAmount` (task 002), never `Number()` - D-001

## Interfaces

- Consumes: `parseAmount(input: string): number` (from task 002)

## Non-goals

- `parseAmount` and receipts - tasks 002 and 001

## Starting points

- `src/cli.js:8-20` - USAGE and the `transfer` command, which reads `Number(cents)` today
- `test/cli.test.js:15-25` - the transfer test to switch to a typed amount
- Pattern: Add a CLI command (`docs/ARCHITECTURE.md`)

## Docs

- `README.md` - add a `tl transfer` example with a typed amount
