## TASK

Add `tl fee <amount> <transfer|withdraw>` to `src/cli.js`: print the fee a transfer or withdrawal of that amount
would pay, without touching balances (TL-15).

## DONE WHEN

- [ ] `node src/cli.js fee 10.50 transfer` → `Fee: $0.11`, exit 0
- [ ] `node src/cli.js fee 50.25 withdraw` → `Fee: $1.01`, exit 0
- [ ] `node src/cli.js fee 10 foo` → `Error: Unknown fee kind: foo`, exit 1
- [ ] USAGE lists `tl fee <amount> <transfer|withdraw>`
- [ ] `npm test` → 0 failures; `npm run lint` → `lint ok`
- [ ] Compiles without errors
- [ ] No files outside stated scope modified

## VERIFY

Verified fresh by a verify-task subagent.

Concrete check (exact command → expected result):

- `node src/cli.js fee 10.50 transfer` → `Fee: $0.11`
