## TASK

Add `withdraw()`: take an amount plus a 2% withdrawal fee (25-cent minimum) out of an account and return its new
balance.
Classification: STANDARD

## PATTERN

Add a money-moving operation

## CONSTRAINTS

- Must read and write balances only through `Ledger`; must not open the ledger file (D-003, L-001).
- Code in `src/` must use async file I/O only (lint rule `async-io`).
- Amounts must stay integer cents (D-001).
- The debit and the fee must go through one `ledger.apply()` call, so a withdrawal is all-or-nothing.

## CONTEXT

- files:
    - src/withdraw.js — Create — the `withdraw()` operation
    - test/withdraw.test.js — Test — balances after success, the minimum fee, and `InsufficientFundsError`
- docs (read-only references):
    - docs/PROJECT_CONTEXT.md
    - docs/ARCHITECTURE.md
    - docs/DECISIONS.md
    - docs/reviews/TL-14-review.md

## INTERFACES

- Consumes: `computeFee(amountCents: number, kind: string): number` (src/fees.js:5)
- Produces: `withdraw(ledger: Ledger, accountId: string, amountCents: number): number` - the account's new balance in
  cents. Task 002 prints it directly: `formatAmount(withdraw(ledger, accountId, amountCents))`.

## GOAL

Support staff can pay money out of a customer account; the fee goes to the fees account.

## NON-GOALS

- No CLI command - task 002 adds `tl withdraw`.
- No change to the fee schedule - `withdraw` is already in `src/fees.js:2-3`.

## STEPS

1. Confirm the fee kind exists: `grep -n "withdraw" src/fees.js` → `withdraw: 200` (line 2) and `withdraw: 25`
   (line 3).
2. Create `test/withdraw.test.js`:

   ```js
   import assert from 'node:assert/strict';
   import { test } from 'node:test';
   import { InsufficientFundsError } from '../src/errors.js';
   import { FEES_ACCOUNT } from '../src/ledger.js';
   import { withdraw } from '../src/withdraw.js';
   import { tempLedger } from './helpers.js';

   test('withdraw takes the amount plus a 2% fee and returns the new balance', async () => {
     const { ledger, cleanup } = await tempLedger();
     try {
       assert.equal(withdraw(ledger, 'alice', 5000), 4900);
       assert.equal(await ledger.getBalance(FEES_ACCOUNT), 100);
     } finally {
       await cleanup();
     }
   });

   test('small withdrawals pay the 25 cent minimum fee', async () => {
     const { ledger, cleanup } = await tempLedger();
     try {
       assert.equal(withdraw(ledger, 'alice', 500), 9475);
     } finally {
       await cleanup();
     }
   });

   test('withdraw fails without changes when the account cannot cover amount and fee', async () => {
     const { ledger, cleanup } = await tempLedger({ alice: 1000 });
     try {
       assert.throws(() => withdraw(ledger, 'alice', 1000), InsufficientFundsError);
       assert.equal(await ledger.getBalance('alice'), 1000);
     } finally {
       await cleanup();
     }
   });
   ```

3. Run `npm test` → expected FAIL: `Cannot find module` for `src/withdraw.js`.
4. Create `src/withdraw.js`:

   ```js
   import { computeFee } from './fees.js';
   import { FEES_ACCOUNT } from './ledger.js';

   // Take amountCents out of an account; the account also pays the withdrawal fee. Returns the new balance.
   export function withdraw(ledger, accountId, amountCents) {
     const feeCents = computeFee(amountCents, 'withdraw');
     const { balances } = ledger.apply([
       { accountId, deltaCents: -(amountCents + feeCents) },
       { accountId: FEES_ACCOUNT, deltaCents: feeCents },
     ]);
     return balances[accountId];
   }
   ```

5. Run `npm test` → expected PASS, 0 failures.
6. Run `npm run build` → `build ok`; run `npm run lint` → `lint ok`.

## DONE WHEN

- [ ] `withdraw(ledger, 'alice', 5000)` on a fresh `tempLedger()` returns 4900 and credits 100 cents to `FEES_ACCOUNT`
- [ ] A 500-cent withdrawal pays the 25-cent minimum fee
- [ ] A withdrawal the account cannot cover throws `InsufficientFundsError` and changes no balance
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
- Smoke: none - there is no CLI command until task 002

## DOC UPDATE

none required

## COMMIT

feat(TL-14): withdraw() with a 2% fee (25 cent minimum)

- withdraw() debits amount + fee in one ledger.apply() call and returns the new balance
- key invariant: balances change only through Ledger, all-or-nothing

Breaking: none
Migration: none
