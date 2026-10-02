## TASK

Round transfer fees half-up: a 1050-cent transfer must charge an 11-cent fee, not 10 (D-002). The fee is computed in
`src/transfer.js` via `computeFee(amountCents, 'transfer')`.

## DONE WHEN

- [ ] `computeFee(1050, 'transfer')` → `11`, covered by a regression test
- [ ] `npm test` → 0 failures; `npm run lint` → `lint ok`
- [ ] Compiles without errors
- [ ] No files outside stated scope modified

## VERIFY

Verified fresh by a verify-task subagent.

Concrete check (exact command → expected result):

- `node -e "import('./src/fees.js').then((m) => console.log(m.computeFee(1050, 'transfer')))"` → `11`
