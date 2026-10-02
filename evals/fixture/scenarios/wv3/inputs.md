Task file: `docs/tasks/feature-TL-27-refunds/001-refund.md` (paths are relative to the project repository)
Read-only apart from build/test/lint and the spot check it undoes (`testing.md`); never fixes.

Executor's report:

```text
Status: DONE
Acceptance:
- [AC1] amount goes back from bob to alice, fees unchanged - src/refund.js; test/refund.test.js:9-20
- [AC2] refundFee returns the fee from the fees account; 1050 -> 11 cents - test/refund.test.js:22-34, 36-45
- [AC3] all or nothing on InsufficientFundsError - one ledger.apply(); test/refund.test.js:47-57
- [AC4] same account and bad amounts refused with RangeError - test/refund.test.js:59-71
- [AC5] refunds above $500.00 refused with the TL-31 message; 50000 goes through, 50001 is refused - src/refund.js; test/refund.test.js:73-83
- npm run build -> build ok; npm test -> {{TESTS_PASS}} passed, 0 failed; npm run lint -> lint ok
Files changed:
- src/refund.js - refund() with REFUND_LIMIT_CENTS
- test/refund.test.js - refund tests
Tests added:
- test/refund.test.js:73 - fails if the $500 limit is not enforced
Tests changed: none
Deviations: none
Also affects: none
Docs updated: none
Follow-ups: none
```
