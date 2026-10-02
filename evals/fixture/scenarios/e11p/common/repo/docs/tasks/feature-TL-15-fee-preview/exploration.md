# Exploration Log - feature-TL-15-fee-preview

## {{ago:45}} - triage

- [NONE] TL-15: support staff want to quote the fee for an amount before running a transfer or a withdrawal
- [ARCHITECTURE] Pattern "Add a CLI command" (docs/ARCHITECTURE.md); fees come from `computeFee(amountCents, kind)`
  (src/fees.js:5)

## {{ago:12}} - execute-task 001

- [NONE] `main()` builds a `Ledger` for every command, but the constructor does not touch the file
  (src/ledger.js:12-14), so `tl fee` works without a ledger file
