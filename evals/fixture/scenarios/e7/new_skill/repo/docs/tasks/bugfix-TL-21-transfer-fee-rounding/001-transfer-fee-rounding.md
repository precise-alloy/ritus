# Task 001: Round transfer fees half-up

Level: SIMPLE - Depends on: none - Plan: none

## Goal

A 1050-cent transfer charges a 10-cent fee; it must charge 11 (TL-21). Fees round half-up to the cent (D-002), and
finance reconciles against that rule at month end.

## Acceptance

- [ ] A 1050-cent transfer charges an 11-cent fee - `node -e "import('./src/fees.js').then((m) => console.log(m.computeFee(1050, 'transfer')))"` -> `11`
- [ ] Regression test - `npm test` fails before the change, passes after
- [ ] `npm run build` -> exit 0; `npm test` -> 0 failures; `npm run lint` -> `lint ok`

## Starting points

- `src/transfer.js:9` - the transfer fee: `computeFee(amountCents, 'transfer')`
- `docs/DECISIONS.md` D-002 - the rounding rule
