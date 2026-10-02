# Investigation: fees round down instead of half-up

Level: STANDARD - Date: {{date:1}} - Ticket: TL-21
Status: implemented

## Symptom

`tl transfer alice bob 10.50` charges a $0.10 fee. D-002 says fees round half-up to the cent, so 10.5 cents is 11, and
finance reconciles against that rule at month end.

## Root cause

Grade: Confirmed

`computeFee` floors the fee (`src/fees.js:18`: `Math.floor((amountCents * rule.rateBps) / 10000)`). The table-driven
refactor ("refactor(fees): table-driven fee schedule") dropped the `+ 5000` that made it round half-up.

## Evidence

- `computeFee(1050, 'transfer')` -> 10 - Confirmed - `node -e "import('./src/fees.js').then((m) => console.log(m.computeFee(1050, 'transfer')))"`
- `computeFee(5025, 'withdraw')` -> 100, where D-002 gives 101 - Confirmed - the same command for withdraw
- The refactor's diff removes `+ 5000` from the fee formula - Confirmed - `git log -p -- src/fees.js`
- The existing fee tests use amounts whose fee is a whole number of cents, so they pass either way - Deduced

## Affected paths

- Transfers - `src/transfer.js:9` - the sender is charged the floored fee (the ticket's case)
- Withdrawals - `src/withdraw.js:5` - the floored 2% fee; the 25-cent minimum still applies on top

## Proposed Fix

Round half-up once, in `computeFee`, as before the refactor: `Math.floor((amountCents * rule.rateBps + 5000) / 10000)`,
then the kind's minimum. Both paths go through it, so neither caller changes.

## Regression Test

- `test/fees.test.js`: `computeFee(1050, 'transfer')` is 11 and `computeFee(5025, 'withdraw')` is 101 - one per affected
  path; both fail on the current code - `npm test -- test/fees.test.js`
