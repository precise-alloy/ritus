## TASK

Add `tl withdraw <account> <amount>`: take the typed amount out of the account and print its new balance.
Classification: STANDARD

## PATTERN

Add a CLI command

## CONSTRAINTS

- Must parse the typed amount with `parseAmount` (`src/money.js:24`), never `Number()` (D-001).
- Only `src/cli.js` prints (lint rule `no-console`).

## CONTEXT

- files:
    - src/cli.js — Modify:8-21 — `withdraw` command and its USAGE line
    - test/cli.test.js — Test — `withdraw` prints the new balance
- docs (read-only references):
    - docs/PROJECT_CONTEXT.md
    - docs/ARCHITECTURE.md

## INTERFACES

- Consumes: `withdraw(ledger: Ledger, accountId: string, amountCents: number): number` (task 001)
- Produces: none

## GOAL

Support staff run `tl withdraw alice 50.00` and see what is left in the account (`$49.00`).

## NON-GOALS

- No receipt for withdrawals - TL-14 asks for the balance only.

## STEPS

1. In `src/cli.js`, add `import { withdraw } from './withdraw.js';` after the `transfer` import.
2. In `src/cli.js`:

   from:

   ```js
     tl transfer <from> <to> <amount>`;
   ```

   to:

   ```js
     tl transfer <from> <to> <amount>
     tl withdraw <account> <amount>`;
   ```

3. In `src/cli.js`, add after the `transfer` command:

   ```js
     async withdraw(ledger, [accountId, amount]) {
       return formatAmount(withdraw(ledger, accountId, parseAmount(amount)));
     },
   ```

4. In `test/cli.test.js`, add:

   ```js
   test('withdraw prints the new balance', async () => {
     const { path, cleanup } = await tempLedger();
     try {
       assert.deepEqual(await main(['withdraw', 'alice', '50.00'], { ledgerPath: path }), { code: 0, output: '$49.00' });
     } finally {
       await cleanup();
     }
   });
   ```

5. Run `npm test` → expected PASS, 0 failures; `npm run build` → `build ok`; `npm run lint` → `lint ok`.

## DONE WHEN

- [ ] `tl withdraw alice 50.00` on a fresh ledger prints `$49.00` and exits 0
- [ ] USAGE lists `tl withdraw <account> <amount>`
- [ ] Compiles without errors
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
- Smoke: `node --input-type=module -e "import { main } from './src/cli.js'; import { tempLedger } from './test/helpers.js'; const { path, cleanup } = await tempLedger(); console.log(await main(['withdraw', 'alice', '50.00'], { ledgerPath: path })); await cleanup();"` → `{ code: 0, output: '$49.00' }`

## DOC UPDATE

none required

## COMMIT

feat(TL-14): tl withdraw prints the new balance

- tl withdraw <account> <amount> parses the typed amount and prints what is left

Breaking: none
Migration: none
