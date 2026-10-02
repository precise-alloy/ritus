Task file: `docs/tasks/feature-TL-40-refunds/007-refunds-report.md` (paths are relative to the project repository)
Read-only apart from build/test/lint and the spot check it undoes (`testing.md`); never fixes.

Executor's report:

```text
Status: DONE
Acceptance:
- [AC1] one line per refund in the order given, the fee when one was returned, the UTC day - src/report.js; test/report.test.js:10-20
- [AC2] totals line, singular for one refund - test/report.test.js:10-20, 22-24
- [AC3] `No refunds for <account>` - test/report.test.js:26-28; test/cli.test.js:109-116
- [AC4] `tl refunds <account>` prints the report, exit 0; USAGE lists it - src/cli.js; test/cli.test.js:90-107
- [AC5] npm run build -> build ok; npm test -> {{TESTS_PASS}} passed, 0 failed; npm run lint -> lint ok
Files changed:
- src/report.js - renderRefundReport()
- src/cli.js - the refunds command and its USAGE line
- test/report.test.js - report tests
- test/cli.test.js - refunds command tests
Tests added:
- test/report.test.js:10 - fails if a line, the order or a total is wrong
- test/report.test.js:22 - fails if one refund reads plural
- test/report.test.js:26 - fails if an empty report prints lines
- test/cli.test.js:90 - fails if the command doesn't print listRefunds' refunds as the report
- test/cli.test.js:109 - fails if an account without refunds errors
Tests changed: none
Deviations: none
Also affects: none
Docs updated: none
Follow-ups: none
```
