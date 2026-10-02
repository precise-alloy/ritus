Task file: `docs/tasks/feature-TL-40-refunds/001-refund.md` (paths are relative to the project repository)
Read-only apart from build/test/lint and the spot check it undoes (`testing.md`); never fixes.

Executor's report:

```text
Status: DONE
Acceptance:
- [AC1] amount goes back from bob to alice, fees unchanged - src/refund.js; test/refund.test.js:9-20
- [AC2] refundFee returns the transfer fee from the fees account; 1050 -> 11 cents - src/refund.js; test/refund.test.js:22-34
- [AC3] all or nothing on InsufficientFundsError - one ledger.apply(); test/refund.test.js:36-46
- [AC4] same account and bad amounts refused with RangeError - test/refund.test.js:48-60
- [AC5] resolves to { id, fromId, toId, amountCents, feeCents } - test/refund.test.js:13, 27
- [AC6] npm run build -> build ok; npm test -> {{TESTS_PASS}} passed, 0 failed; npm run lint -> lint ok
Files changed:
- src/refund.js - refund()
- test/refund.test.js - refund tests
Tests added:
- test/refund.test.js:9 - fails if the amount doesn't go back or the fees account changes
- test/refund.test.js:22 - fails if refundFee doesn't return the fee from the fees account
- test/refund.test.js:36 - fails if a refused refund changes a balance
- test/refund.test.js:48 - fails if the same account or a bad amount is accepted
Tests changed: none
Deviations: none
Also affects: none
Docs updated: none
Follow-ups: none
```
