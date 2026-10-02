# Task 003: Render a refund receipt

Level: EPIC - Depends on: 001 - Plan: docs/reviews/TL-27-review.md
Status: todo

## Goal

Support hands the customer a receipt for a refund, like the one for a transfer (TL-27).

## Acceptance

- [ ] [AC1] `renderRefundReceipt({ id: 'R-1002', fromId: 'alice', toId: 'bob', amountCents: 1050, feeCents: 11 })`
  returns the lines `Refund R-1002`, `Back to: alice`, `From: bob`, `Amount: $10.50`, `Fee returned: $0.11` - a test in
  `test/receipt.test.js`
- [ ] [AC2] Without a refunded fee (`feeCents: 0`) there is no `Fee returned` line - a test
- [ ] [AC3] An optional currency renders amounts like `renderReceipt` does (`EUR` -> `€10.50`) - a test
- [ ] [AC4] `npm run build` -> exit 0; `npm test` -> 0 failures; `npm run lint` -> `lint ok`

## Interfaces

- Produces: `renderRefundReceipt(refund, currency = 'USD'): string` in `src/receipt.js`

## Starting points

- `src/receipt.js:3-10` - `renderReceipt`, the transfer receipt to mirror
