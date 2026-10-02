Task file: `docs/tasks/feature-TL-16-friendly-amounts/002-parse-amount.md` (paths are relative to the project
repository)
Key constraints: read-only except build/test/lint; never fix; never trust implementer claims.

Implementation report from the execute-task subagent (changed files, implementation summary, validation evidence):

```text
Files changed:
- src/money.js - parseAmount(input) and AMOUNT_PATTERN; imports InvalidAmountError
- test/money.test.js - parseAmount tests: valid forms and refusals

DONE WHEN:
- [x] "12.34" -> 1234, "0.5" -> 50, "7" -> 700, "1,234.50" -> 123450, " 7 " -> 700 - src/money.js:24-37
- [x] "abc", "", "   ", "-5", "1.234", "1,23", "12.", "0", "0.00" refused with InvalidAmountError - src/money.js:24-37
- [x] Non-text input and "90071992547410" refused - src/money.js:25-27, src/money.js:34-36
- [x] Tests cover each case above - test/money.test.js:30-50
- [x] Compiles without errors - npm run build -> build ok
- [x] Unit test passes - npm test -> {{TESTS_PASS}} passed, 0 failed
- [x] CONSTRAINTS satisfied, NON-GOALS untouched, INTERFACES honored - parseAmount(input: string): number at src/money.js:24
- [x] Scope clean - only CONTEXT files and their tests
- [x] Standards validated - all applicable gates from definition-of-done checked; npm run lint -> lint ok
- [x] DOC UPDATE - none required

Validation: npm run build -> build ok; npm test -> {{TESTS_PASS}} passed, 0 failed; npm run lint -> lint ok

Docs updated:
- none required

Commit message:
feat(TL-16): parseAmount reads typed amounts into integer cents

- strict US-style pattern, integer math only, refuses zero and amounts too large to count in cents

Breaking: none
Migration: none
```
