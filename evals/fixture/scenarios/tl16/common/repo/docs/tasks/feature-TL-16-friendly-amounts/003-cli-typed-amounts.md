## TASK

Switch `tl transfer` to typed amounts: parse `<amount>` with `parseAmount` instead of counting cents.
Classification: STANDARD

## PATTERN

none

## CONSTRAINTS

- Must parse the typed amount with `parseAmount` (task 002), never `Number()` (D-001).
- Only `src/cli.js` prints (lint rule `no-console`).

## CONTEXT

- files:
    - src/cli.js — Modify:8-20 — USAGE and the `transfer` command
    - test/cli.test.js — Test — typed amount; an invalid amount prints the error and exits 1
- docs (read-only references):
    - docs/PROJECT_CONTEXT.md
    - docs/reviews/TL-16-review.md

## INTERFACES

- Consumes: `parseAmount(input: string): number` (task 002)
- Produces: none

## GOAL

`tl transfer alice bob 12.50` moves $12.50 and prints the receipt with its fee and total.

## NON-GOALS

- No change to `parseAmount` or to receipts (tasks 001 and 002).

## STEPS

1. In `src/cli.js`, import `parseAmount` next to `formatAmount`, change the USAGE line to
   `tl transfer <from> <to> <amount>`, and pass `parseAmount(amount)` to `transfer()` instead of `Number(cents)`.
2. In `test/cli.test.js`, change the transfer test to `['transfer', 'alice', 'bob', '12.50']`, expecting the receipt
   with `Fee: $0.13` and `Total: $12.63`, and add a test that `['transfer', 'alice', 'bob', '0.00']` returns code 1 and
   `Error: Invalid amount "0.00": amount must be greater than zero`.
3. Run `npm test` → expected PASS, 0 failures; `npm run build` → `build ok`; `npm run lint` → `lint ok`.

## DONE WHEN

- [ ] `tl transfer alice bob 12.50` on a fresh ledger prints a receipt with `Amount: $12.50`, `Fee: $0.13`, `Total: $12.63`
- [ ] `tl transfer alice bob 0.00` prints `Error: Invalid amount "0.00": amount must be greater than zero` and exits 1
- [ ] Compiles without errors
- [ ] CONSTRAINTS all satisfied; nothing under NON-GOALS implemented
- [ ] INTERFACES honored: `Produces` signatures exposed as written; `Consumes` used exactly as given in INTERFACES
- [ ] No files outside CONTEXT + DOC UPDATE + related test files modified
- [ ] All PATTERN steps completed or marked N/A
- [ ] No claim made about existing code without citing file:line
- [ ] If interface changed: skill file for affected module updated or rewritten
{{STANDARDS_LINE}}
- [ ] DOC UPDATE completed

## VERIFY

Verified fresh by a verify-task subagent, in a clean context separate from the implementer's. On FAIL, the main thread
owns the fix loop — it appends the fix + re-verify steps and applies the circuit breaker (cap: 3 attempts) from
`skills/shared/dispatch.md`.

Concrete checks (exact command → expected result):

- Build: `npm run build` → exit 0
- Test: `npm test` → 0 failures

## DOC UPDATE

- README.md — the `tl transfer` example uses a typed amount

## COMMIT

feat(TL-16): tl transfer accepts typed amounts

- tl transfer parses <amount> with parseAmount; invalid amounts print the error and exit 1

Breaking: tl transfer no longer reads its amount as cents
Migration: none
