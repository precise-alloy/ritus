# Task 001: Show the fee and the total on receipts

Level: STANDARD - Depends on: none - Plan: docs/reviews/TL-16-review.md
Status: verified

## Goal

Support staff can read the fee and the total the sender paid straight from the receipt.

## Acceptance

- [ ] Receipts list `Fee: <fee>` and `Total: <amount + fee>` after the Amount line, in the receipt currency -
  `npm test` -> the receipt tests pass
- [ ] A zero fee shows as `Fee: $0.00` - `npm test` -> the zero-fee receipt test passes
- [ ] Currency - `node -e "import('./src/receipt.js').then((m) => console.log(m.renderReceipt({ id: 'R-1', fromId: 'a', toId: 'b', amountCents: 1250, feeCents: 13 }, 'EUR')))"`
  -> prints `Fee: €0.13` and `Total: €12.63`
- [ ] `npm run build` -> exit 0; `npm test` -> 0 failures; `npm run lint` -> `lint ok`

## Constraints

- Amounts stay integer cents until they are formatted, and are formatted through `src/money.js` - D-001
- `renderReceipt` stays a pure function - only `src/cli.js` prints (lint rule `no-console`)

## Non-goals

- How fees are computed (`src/fees.js`) - unchanged
- The CLI - task 003 changes `tl transfer`

## Starting points

- `src/receipt.js:3-10` - `renderReceipt` builds the receipt lines; the two new lines go after Amount
- `src/transfer.js:18` - the receipt already carries `feeCents`
- `test/receipt.test.js` - receipt lines, zero fee, currency
