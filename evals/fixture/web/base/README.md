# TinyLedger Web

TinyLedger Web is a small browser app for viewing account balances and reviewing a transfer before it is submitted.

```sh
npm run dev      # serves http://localhost:4173/
npm test         # node:test suite, JUnit report in .cache/junit.xml
npm run build    # syntax-checks scripts and browser modules
npm run lint     # project lint rules, report in .cache/lint-report.json
```

The app has no runtime dependencies. It serves ES modules directly and stores seed account data in `data/accounts.json`.
