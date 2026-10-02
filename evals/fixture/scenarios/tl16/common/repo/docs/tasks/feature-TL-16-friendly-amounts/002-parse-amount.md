## TASK

Add `parseAmount(input)`: turn an amount typed by support staff ("12.34", "1,234.50", " 7 ") into integer cents, and
refuse anything that is not an amount greater than zero.
Classification: STANDARD

## PATTERN

none

## CONSTRAINTS

- Must convert to integer cents without float arithmetic (D-001).
- Every refusal must throw `InvalidAmountError` (`src/errors.js:26-31`), so the CLI prints `Error: Invalid amount ...`
  and exits 1.
- Only amounts greater than zero are valid: "0" and "0.00" are refused (docs/reviews/TL-16-review.md, Decisions).

## CONTEXT

- files:
    - src/money.js — Modify — add `parseAmount` next to `formatAmount`
    - test/money.test.js — Test — valid forms and every refusal
- docs (read-only references):
    - docs/PROJECT_CONTEXT.md
    - docs/DECISIONS.md
    - docs/reviews/TL-16-review.md

## INTERFACES

- Consumes: `InvalidAmountError(input: unknown, reason: string)` (src/errors.js:26-31)
- Produces: `parseAmount(input: string): number` - integer cents, always greater than zero. Task 003 passes the result
  straight to `transfer()`.

## GOAL

Support staff type the amounts they see on the ticket instead of counting cents.

## NON-GOALS

- No CLI change - task 003 switches `tl transfer` to `parseAmount`.
- No other locales: "1.234,50" is refused, not read as 1234.50.

## STEPS

1. In `test/money.test.js`, import `InvalidAmountError` from `../src/errors.js` and `parseAmount` from
   `../src/money.js`, then add:

   ```js
   test('parseAmount reads dollars and cents', () => {
     assert.equal(parseAmount('12.34'), 1234);
     assert.equal(parseAmount('0.5'), 50);
     assert.equal(parseAmount('7'), 700);
   });

   test('parseAmount accepts thousands separators and surrounding spaces', () => {
     assert.equal(parseAmount('1,234.50'), 123450);
     assert.equal(parseAmount(' 7 '), 700);
   });

   test('parseAmount refuses text that is not an amount', () => {
     for (const input of ['abc', '', '   ', '-5', '1.234', '1,23', '12.']) {
       assert.throws(() => parseAmount(input), InvalidAmountError, input);
     }
   });

   test('parseAmount refuses zero', () => {
     assert.throws(() => parseAmount('0'), InvalidAmountError);
     assert.throws(() => parseAmount('0.00'), InvalidAmountError);
   });

   test('parseAmount refuses non-text and amounts too large to count in cents', () => {
     assert.throws(() => parseAmount(12), InvalidAmountError);
     assert.throws(() => parseAmount('90071992547410'), InvalidAmountError);
   });
   ```

2. Run `npm test` → expected FAIL: `parseAmount` is not exported by `src/money.js`.
3. In `src/money.js`, add `import { InvalidAmountError } from './errors.js';` at the top and
   `const AMOUNT_PATTERN = /^(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?$/;` after `SYMBOLS`, then add after
   `formatAmount`:

   ```js
   // Parse an amount typed by support staff ("12.34", "1,234.50", " 7 ") into integer cents. Only amounts greater than
   // zero are valid.
   export function parseAmount(input) {
     if (typeof input !== 'string') {
       throw new InvalidAmountError(input, 'expected text');
     }
     const match = AMOUNT_PATTERN.exec(input.trim());
     if (!match) {
       throw new InvalidAmountError(input, 'expected an amount like 12.34');
     }
     const [, units, fraction = ''] = match;
     const cents = Number(units.replaceAll(',', '')) * 100 + Number(fraction.padEnd(2, '0'));
     if (!Number.isSafeInteger(cents)) {
       throw new InvalidAmountError(input, 'amount is too large');
     }
     if (cents === 0) {
       throw new InvalidAmountError(input, 'amount must be greater than zero');
     }
     return cents;
   }
   ```

4. Run `npm test` → expected PASS, 0 failures; `npm run build` → `build ok`; `npm run lint` → `lint ok`.

## DONE WHEN

- [ ] `parseAmount` returns integer cents: "12.34" → 1234, "0.5" → 50, "7" → 700, "1,234.50" → 123450, " 7 " → 700
- [ ] Refused with `InvalidAmountError`: "abc", "", "   ", "-5", "1.234", "1,23", "12.", "0", "0.00"
- [ ] Refused with `InvalidAmountError`: non-text input, and amounts too large to count in cents ("90071992547410")
- [ ] Tests cover each case above
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
- Smoke: `node -e "import('./src/money.js').then((m) => console.log(m.parseAmount('1,234.50')))"` → `123450`

## DOC UPDATE

none required

## COMMIT

feat(TL-16): parseAmount reads typed amounts into integer cents

- strict US-style pattern, integer math only, refuses zero and amounts too large to count in cents

Breaking: none
Migration: none
