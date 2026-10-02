# Exploration Log - feature-TL-14-withdrawals

## {{ts:1:16:25}} - requirement-analysis

- [NONE] The `withdraw` fee kind is already in the schedule (src/fees.js:2-3): 200 bps, 25-cent minimum
- [ARCHITECTURE] Money-moving operations build their entries and call `ledger.apply()` once (src/transfer.js:10-17)
- [NONE] `parseAmount` (src/money.js:24) turns typed amounts into integer cents for the CLI (TL-9)
