# Decisions

## D-001 - Integer cents everywhere

Amounts are integers in cents from parsing to rendering. Floats produced wrong fees in the prototype
(`0.29 * 100 === 28.999999999999996`). Convert to text only at the edges, through `src/money.js`.

## D-002 - Fees round half-up to the cent

Every fee kind rounds half-up to the nearest cent (1050 cents at 1% is 10.5 cents, charged as 11). Finance reconciles
against this rule; any other rounding shows up as a mismatch at month end.

## D-003 - One writer for the ledger file

All balance reads and writes go through `Ledger` (`src/ledger.js`), which runs operations one at a time and writes
atomically (temp file + rename). Nothing else opens the ledger file. See L-001 for why.
