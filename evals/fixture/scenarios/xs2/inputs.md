Task file: `docs/tasks/feature-TL-27-refunds/002-refund-command.md` (paths are relative to the project repository)
Read-only apart from build/test/lint and the spot check it undoes (`testing.md`); never fixes.

Executor's report:

```text
Status: DONE
Acceptance:
- [AC1] `tl refund alice bob 20.00` -> `Refund R-1001: $20.00 back to alice` - test/cli.test.js:57-71
- [AC2] `--fee` -> `Refund R-1002: $10.50 and $0.11 fee back to alice` - test/cli.test.js:57-71
- [AC3] above the limit -> the TL-31 error, exit 1 - test/cli.test.js:73-83
- [AC4] USAGE lists `tl refund <from> <to> <amount> [--fee]` - src/cli.js
- [AC5] npm run build -> build ok; npm test -> {{TESTS_PASS}} passed, 0 failed; npm run lint -> lint ok
Files changed:
- src/cli.js - `refund` command and USAGE line
- test/cli.test.js - `tl refund` tests
Tests added:
- test/cli.test.js:57 - fails if the summary line or the fee part is wrong
- test/cli.test.js:73 - fails if the limit error is not printed with exit 1
Tests changed: none
Deviations: none
Also affects: none
Docs updated: none
Follow-ups: none
```
