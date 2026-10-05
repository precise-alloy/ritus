# Findings

How pr-review tags a finding, and how the tags set the verdict.

## Type

One per finding. When several fit, the most serious wins: security > logic > requirement > test > scope > convention.

| Type | What it catches | Default disposition |
|---|---|---|
| `logic` | Wrong behavior: a bad branch, an off-by-one, a null dereference, a race, a silent no-op | Blocking |
| `security` | Injection, broken authentication or authorization, data or information leakage, IDOR | Blocking |
| `requirement` | An acceptance criterion not met, or required behavior missing from the diff | Blocking |
| `test` | Missing, weak, or misplaced tests for changed logic; an existing test weakened to pass | Blocking for critical logic or a weakened test, else Recommended |
| `scope` | Code the plan doesn't ask for: an unused option or parameter, a single-use abstraction, an unrequested file or dependency, a guard for an unreachable state | Blocking when it adds behavior no test covers, else Recommended |
| `convention` | Naming, structure, project idioms, design smells, stale docs or traceability | Optional |

Lint, formatting, and style are not findings; they belong to the linter.

## Severity

| Severity | Meaning |
|---|---|
| Critical | A runtime failure, data loss, or a security breach |
| High | An unmet requirement, a data-corruption risk, or critical logic without coverage |
| Medium | A risk under specific conditions |
| Low | Code quality, a minor improvement, defensive hardening |

## Verdict

- **Request Changes** when any finding is Blocking, or any finding is Critical or High whatever its type.
- **Approve** when no finding blocks and every acceptance criterion is evidenced. Recommended and Optional findings go
  along for the author to take or leave.
- **Needs Clarification** when the answer to a question decides whether the change is correct, whether you were called
  directly or dispatched. Name who should answer it (`docs/STAKEHOLDERS.md`).
- **BLOCKED** when you could not review: an input is missing, access failed, or a check the verdict depends on could
  not run.
