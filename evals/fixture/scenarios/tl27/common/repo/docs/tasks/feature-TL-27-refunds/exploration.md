# Exploration log - feature-TL-27-refunds

## {{ago:90}} - plan

- [NONE] TL-27: support undoes mistaken transfers; support types the original parties and amount from the receipt
- [DECISIONS] A refund is its own ledger movement, one apply() call; nothing already recorded is edited, so finance
  can reconcile it
