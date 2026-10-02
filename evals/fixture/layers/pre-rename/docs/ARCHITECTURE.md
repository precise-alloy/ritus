# Architecture - tinyledger

```text
src/cli.js ──> transfer.js ──> fees.js
    │              │
    │              └──> ledger.js (Ledger: the only reader/writer of the ledger file)
    └──> receipt.js ──> money.js
```

- Library functions take a `Ledger` as their first argument; they never open the ledger file themselves.
- `Ledger` methods return promises and run one at a time (see D-003).
- Text output is built by pure functions (`renderReceipt`, `formatCents`) and printed only by `src/cli.js`.

## Patterns

### Add a CLI command

1. Add an async function to `commands` in `src/cli.js`: `(ledger, args) => text`.
2. Add a line for it to `USAGE`.
3. Test it through `main()` in `test/cli.test.js`, with `tempLedger()` when it touches balances.
4. Throw domain errors; `main()` prints them and exits 1.

### Add a money-moving operation

1. Compute fees with `computeFee(amountCents, kind)`; add the kind to `FEE_RATES_BPS` if it is new.
2. Build the ledger entries (the fee goes to `FEES_ACCOUNT`) and pass them to one `ledger.apply()` call, so the whole
   operation is atomic.
3. Test the balances after success and after an `InsufficientFundsError`.
