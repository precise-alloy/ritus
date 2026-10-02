# tinyledger

Wallet balances, transfers, and fees for the support tooling. A library (`src/`) plus a small CLI (`tl`).

```sh
npm test          # node:test suite, JUnit report in .cache/junit.xml
npm run build     # syntax-check and link every module
npm run lint      # project rules, see scripts/lint.mjs
TL_LEDGER=ledger.json node src/cli.js balance alice
```

Amounts are integer cents everywhere. See `docs/DECISIONS.md` before touching money, fees, or the ledger file.
