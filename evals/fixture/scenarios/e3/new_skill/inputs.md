Task file: `docs/tasks/feature-TL-16-friendly-amounts/002-parse-amount.md` (paths are relative to the project
repository)
Read-only apart from build/test/lint; never fixes.

Executor's report:

```text
Status: DONE
Acceptance:
- "12.34" -> 1234, "0.5" -> 50, "7" -> 700, "1,234.50" -> 123450, " 7 " -> 700 - src/money.js:24-37; test/money.test.js:30-39
- "abc", "", "   ", "-5", "1.234", "1,23", "12.", "0", "0.00" refused with InvalidAmountError - src/money.js:24-37; test/money.test.js:41-45
- Non-text input and "90071992547410" refused - src/money.js:25-27, src/money.js:34-36; test/money.test.js:47-50
- Tests cover each case above - test/money.test.js:30-50
- Build - npm run build -> build ok
- Tests - npm test -> {{TESTS_PASS}} passed, 0 failed
- Lint - npm run lint -> lint ok
- Standards - "Done means" in engineering.md met; testing.md checks applied to the new tests
Files changed:
- src/money.js - parseAmount(input) and AMOUNT_PATTERN; imports InvalidAmountError
- test/money.test.js - parseAmount tests: valid forms and refusals
Deviations: none
Docs updated: none (none required)
Follow-ups: none

Commit message:
feat(TL-16): parseAmount reads typed amounts into integer cents

- strict US-style pattern, integer math only, refuses zero and amounts too large to count in cents
Breaking: none
Migration: none
```
