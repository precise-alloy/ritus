# Exploration Log - feature-TL-16-friendly-amounts

## {{ts:2:15:35}} - requirement-analysis

- [NONE] `formatAmount(cents, currency)` (src/money.js:4) formats every amount; `renderReceipt` already takes the
  currency (src/receipt.js:3)
- [NONE] `transfer()` returns `feeCents` on the receipt (src/transfer.js:18), so receipts need no fee math
- [ARCHITECTURE] Only `src/cli.js` prints; domain modules return values or throw `LedgerError`s (lint rule
  `no-console`)

## {{ts:1:09:50}} - execute-task 001

- [NONE] Receipt fee and total lines added after Amount; `Total` is `amountCents + feeCents`, formatted in the
  receipt currency

## {{ago:20}} - execute-task 002

- [NONE] `InvalidAmountError(input, reason)` already exists (src/errors.js:26-31); reused, no new error class
- [NONE] `AMOUNT_PATTERN` accepts `1,234.50` and `1234.50` but not `1,23` or `12.`; units and cents are joined with
  integer math
