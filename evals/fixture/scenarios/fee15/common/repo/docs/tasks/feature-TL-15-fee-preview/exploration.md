# Exploration log - feature-TL-15-fee-preview

## {{ago:45}} - plan

- [NONE] TL-15: support staff want to quote the fee for an amount before running a transfer or a withdrawal
- [ARCHITECTURE] Pattern "Add a CLI command" (docs/ARCHITECTURE.md); fees come from `computeFee(amountCents, kind)`
  (src/fees.js:5)

## {{ago:12}} - 001-fee-preview

- [NONE] `main()` builds a `Ledger` for every command, but the constructor does not touch the file
  (src/ledger.js:12-14), so `tl fee` works without a ledger file
- [NONE] The preview lives in a new module, `src/fee-preview.js`, so the CLI stays a thin dispatcher
