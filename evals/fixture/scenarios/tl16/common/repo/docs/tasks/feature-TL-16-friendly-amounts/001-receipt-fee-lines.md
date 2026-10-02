## TASK

Show the fee and the total (amount + fee) on receipts, after the Amount line, in the receipt's currency.
Classification: STANDARD

## PATTERN

none

## CONSTRAINTS

- Must keep amounts as integer cents until they are formatted, and must format them through `src/money.js` (D-001).
- `renderReceipt` must stay a pure function; only `src/cli.js` prints (lint rule `no-console`).

## CONTEXT

- files:
    - src/receipt.js — Modify:3-10 — `renderReceipt` builds the receipt text
    - test/receipt.test.js — Test — receipt lines, zero fee, currency
- docs (read-only references):
    - docs/PROJECT_CONTEXT.md
    - docs/reviews/TL-16-review.md

## INTERFACES

- Consumes: none
- Produces: none

## GOAL

Support staff can read the fee and the total the sender paid straight from the receipt.

## NON-GOALS

- No change to how fees are computed (`src/fees.js`).
- No CLI change - task 003 changes `tl transfer`.

## STEPS

1. In `test/receipt.test.js`, replace the first test with the three tests below and keep the currency test:

   ```js
   test('receipt lists id, parties, amount, fee, and total', () => {
     assert.equal(
       renderReceipt(RECEIPT),
       ['Receipt R-1001', 'From: alice', 'To: bob', 'Amount: $12.50', 'Fee: $0.13', 'Total: $12.63'].join('\n'),
     );
   });

   test('receipt shows a zero fee explicitly', () => {
     const text = renderReceipt({ ...RECEIPT, feeCents: 0 });
     assert.match(text, /^Fee: \$0\.00$/m);
     assert.match(text, /^Total: \$12\.50$/m);
   });
   ```

   and change the currency test to check all three amounts (`Amount: €12.50`, `Fee: €0.13`, `Total: €12.63`).
2. Run `npm test` → expected FAIL: `receipt lists id, parties, amount, fee, and total`.
3. In `src/receipt.js`, after the Amount line add:

   ```js
       `Fee: ${formatAmount(receipt.feeCents, currency)}`,
       `Total: ${formatAmount(receipt.amountCents + receipt.feeCents, currency)}`,
   ```

4. Run `npm test` → expected PASS, 0 failures; `npm run build` → `build ok`; `npm run lint` → `lint ok`.

## DONE WHEN

- [ ] `renderReceipt` lists `Fee: <fee>` and `Total: <amount + fee>` after the Amount line, in the receipt currency
- [ ] A zero fee is shown as `Fee: $0.00`
- [ ] Compiles without errors
- [ ] Unit test passes (new business logic)
- [ ] CONSTRAINTS all satisfied; nothing under NON-GOALS implemented
- [ ] INTERFACES honored: `Produces` signatures exposed as written; `Consumes` used exactly as given in INTERFACES
- [ ] No files outside CONTEXT + DOC UPDATE + related test files modified
- [ ] All PATTERN steps completed or marked N/A
- [ ] No claim made about existing code without citing file:line
- [ ] If interface changed: skill file for affected module updated or rewritten
{{STANDARDS_LINE}}
- [ ] DOC UPDATE completed

## VERIFY

Verified fresh by a verify-task subagent, in a clean context separate from the implementer's. On FAIL, the main thread
owns the fix loop — it appends the fix + re-verify steps and applies the circuit breaker (cap: 3 attempts) from
`skills/shared/dispatch.md`.

Concrete checks (exact command → expected result):

- Build: `npm run build` → exit 0
- Test: `npm test` → 0 failures
- Smoke: `node -e "import('./src/receipt.js').then((m) => console.log(m.renderReceipt({ id: 'R-1', fromId: 'a', toId: 'b', amountCents: 1250, feeCents: 13 }, 'EUR')))"` → prints `Fee: €0.13` and `Total: €12.63`

## DOC UPDATE

none required

## COMMIT

feat(TL-16): show fee and total on receipts

- receipts list Fee and Total (amount + fee) after Amount, in the receipt currency

Breaking: none
Migration: none
