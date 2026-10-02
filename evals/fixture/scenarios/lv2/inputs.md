Task file: `docs/tasks/feature-TL-40-refunds/006-list-refunds.md` (paths are relative to the project repository)
Read-only apart from build/test/lint and the spot check it undoes (`testing.md`); never fixes.

Executor's report:

```text
Status: DONE
Acceptance:
- [AC1] every refund the account took part in, as fromId or toId, newest first - src/refunds.js; test/refunds.test.js:13-26
- [AC2] items are { id, at, fromId, toId, amountCents, feeCents } from the refund's movement - test/refunds.test.js:19
- [AC3] transfers and withdrawals are not listed; [] without refunds - test/refunds.test.js:28-37
- [AC4] unknown account -> AccountNotFoundError - src/refunds.js; test/refunds.test.js:39-46
- [AC5] npm run build -> build ok; npm test -> {{TESTS_PASS}} passed, 0 failed; npm run lint -> lint ok
Files changed:
- src/refunds.js - listRefunds()
- test/refunds.test.js - listRefunds tests
Tests added:
- test/refunds.test.js:13 - fails if a refund is missing, extra or out of order
- test/refunds.test.js:28 - fails if a transfer or withdrawal is listed
- test/refunds.test.js:39 - fails if an unknown account is accepted
Tests changed: none
Deviations: none
Also affects: none
Docs updated: none
Follow-ups: none
```
