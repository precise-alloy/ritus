# Exploration log - feature-TL-40-refunds

## {{ago:90}} - plan

- [DECISIONS] A refund is its own ledger movement, one apply() call; nothing already recorded is edited
- [DECISIONS] Every applied movement is recorded in the ledger file with its receipt id, kind, memo and time (005)
