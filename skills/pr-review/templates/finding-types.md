# Finding Types

pr-review tags every finding in the §2.6 Issues Table with one primary `type`, orthogonal to severity. Break ties by
"most severe concern wins": security > logic > requirement > test > convention.

Lint / format / style issues are not finding types - they belong to the linter/CI (the `verify-task` lint gate). Do
not raise them as findings; at most note once: "linter not configured / N lint errors - run the linter".

| `type`        | What it catches                                                          | Default disposition |
|---------------|--------------------------------------------------------------------------|---------------------|
| `logic`       | Wrong behavior: bad branch, off-by-one, null deref, race, silent no-op   | Blocking |
| `security`    | Injection, broken authorization/authentication, data/info leakage, IDOR                   | Blocking |
| `requirement` | Acceptance criterion not met, or behavior missing from the diff          | Blocking |
| `test`        | Missing, weak, or misplaced tests for changed logic                      | Blocking if critical logic, else Recommended |
| `convention`  | Naming, structure, project idioms, maintainability / design smells, doc / traceability staleness       | Optional |

Disposition drives the verdict: any `Blocking` finding → "Request changes". `Recommended` / `Optional` findings do
not block on their own. Severity overrides disposition: a `Critical/Bug` or `High` severity finding forces "Request
changes" regardless of its type's default disposition - a severe issue never gets a non-blocking escape hatch.
