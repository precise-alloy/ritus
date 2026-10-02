Task file: `docs/tasks/feature-TL-27-refunds/002-refund-limit.md` (paths are relative to the project repository)
Read-only apart from build/test/lint and the spot check it undoes (`testing.md`); never fixes.

Executor's report:

```text
Status: DONE
Acceptance:
- [AC1] refunds above $500.00 refused with the TL-31 message; 50000 goes through, 50001 is refused - src/refund.js; test/refund.test.js:73-83
- [AC2] npm run build -> build ok; npm test -> {{TESTS_PASS}} passed, 0 failed; npm run lint -> lint ok
Files changed:
- src/refund.js - REFUND_LIMIT_CENTS and the limit check before any ledger call
- test/refund.test.js - limit test
Tests added:
- test/refund.test.js:73 - fails if the $500 limit is not enforced
Tests changed: none
Deviations: none
Also affects: none
Docs updated: none
Follow-ups: none
```
