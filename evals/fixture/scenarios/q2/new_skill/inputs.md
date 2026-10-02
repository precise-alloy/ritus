Task file: `docs/tasks/feature-TL-27-refunds/001-refund.md` (paths are relative to the project repository)
Read-only apart from build/test/lint and the spot check it undoes (`testing.md`); never fixes.

Executor's report:

```text
Status: DONE
Acceptance:
- [AC1] refund(ledger, 'alice', 'bob', 2000) moves 2000 back to alice, fees unchanged - src/refund.js:13-20; test/refund.test.js:9-20
- [AC2] refundFee gives alice the transfer fee back from the fees account - src/refund.js:13-19; test/refund.test.js:22-31
- [AC3] all or nothing: InsufficientFundsError and no balance changes - one ledger.apply() at src/refund.js:21; test/refund.test.js:33-40
- [AC4] the same account and amounts that are not positive whole cents are refused with RangeError - src/refund.js:7-12; test/refund.test.js:55-62
- [AC5] resolves to { id, fromId, toId, amountCents, feeCents } - src/refund.js:22; test/refund.test.js:42-53, test/refund.test.js:9-20
- [AC6] npm run build -> build ok; npm test -> {{TESTS_PASS}} passed, 0 failed; npm run lint -> lint ok
Files changed:
- src/refund.js - refund(): validation, reversed entries, the fee entry when a fee is refunded, one apply()
- test/refund.test.js - refund tests: amount back, fee back, all or nothing, one ledger call, same account
Deviations: none
Also affects: none
Docs updated: none
Follow-ups: none

Commit message:
feat(TL-27): refund() undoes a mistaken transfer

- the amount goes back from the recipient to the sender; with refundFee the transfer fee comes back from the fees
  account, all in one ledger.apply()
Breaking: none
Migration: none
```
