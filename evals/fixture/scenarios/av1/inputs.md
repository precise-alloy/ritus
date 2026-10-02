Task file: `docs/tasks/feature-TL-27-refunds/fix-review-round-1.md` (paths are relative to the project repository)
Read-only apart from build/test/lint and the spot check it undoes (`testing.md`); never fixes.

Executor's report:

```text
Status: DONE
Acceptance:
- [AC1] fees account refused on either side with RangeError, nothing changes - src/refund.js:13; test/refund.test.js:86-98
- [AC2] unknown option -> Error: Unknown option --fees, exit 1, nothing moves; --fee and no option still work - src/cli.js:29; test/cli.test.js:85-97, :57
- [AC3] npm run build -> build ok; npm test -> {{TESTS_PASS}} passed, 0 failed; npm run lint -> lint ok
Files changed:
- src/refund.js - refuse the fees account as a refund party
- src/cli.js - reject unknown refund options
- test/refund.test.js - fees-party test
- test/cli.test.js - unknown-option test
Tests added:
- test/refund.test.js:86 - fails if the fees account may be a refund party
- test/cli.test.js:85 - fails if an unknown option is accepted
Tests changed: none
Deviations: none
Also affects: none
Docs updated: none
Follow-ups: none
```
