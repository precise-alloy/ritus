# Code Conventions

## Modules

- One module per concern in `src/`, named after it (`fees.js`, `money.js`); `src/cli.js` only dispatches commands.
- Library functions that touch balances take a `Ledger` as their first argument.

## Errors

- Domain errors extend `LedgerError` (`src/errors.js`) and carry a stable `code`.
