# Exploration Log - feature-TL-12-receipt-fees

## {{ts:16:14:10}} - requirement-analysis

- [NONE] `transfer()` already returns `feeCents` on the receipt object (src/transfer.js:18); display only, no fee math
- [CODE_CONVENTIONS] Receipt lines format money with `formatCents` from src/money.js; never divide by 100 inline
- [NONE] `tl transfer` prints `renderReceipt(receipt)` as is (src/cli.js:19), so the CLI needs no change
