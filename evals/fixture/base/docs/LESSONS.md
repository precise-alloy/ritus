# Lessons

## L-001 - A second writer corrupted balances (2025-11)

A support script read `ledger.json` with `readFileSync`, adjusted a balance, and wrote it back while a transfer was in
flight. The transfer's write was lost and two accounts disagreed with the bank statement for a week. Since then every
read and write goes through `Ledger`, and lint rejects synchronous file I/O in `src/` (D-003).

## L-002 - Tests that computed their own expected fee

An early fee test asserted `computeFee(x) === x * rate`, repeating the production formula, so it passed while both
were wrong. Fee and money tests now spell out the expected cents as literals.
