# Exploration log - feature-TL-27-refunds

## {{ago:90}} - plan

- [NONE] TL-27: support undoes mistaken transfers; support types the original parties and amount from the receipt
- [DECISIONS] A refund is its own ledger movement, one apply() call; nothing already recorded is edited, so finance
  can reconcile it

## {{ago:15}} - 001-refund

- [NONE] refund() mirrors transfer(): validation first, then one apply() with the reversed entries; the fee entry is
  added only when a fee is refunded (src/refund.js:13-20)
