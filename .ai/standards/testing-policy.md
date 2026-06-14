# Testing Policy — V1.0

## Test type matrix

| Change type                                | Unit                  | Integration       | Contract   | Migration  |
|--------------------------------------------|-----------------------|-------------------|------------|------------|
| New service method                         | ✅ required            | —                 | —          | —          |
| New API endpoint                           | ✅ auth + validation   | ✅ happy path      | —          | —          |
| New background worker / job                | ✅ dispatch logic      | ✅ queue behavior  | —          | —          |
| New DB table / column                      | —                     | —                 | —          | ✅ required |
| Shared type / contract change              | ✅ all callers compile | —                 | ✅ required | —          |
| Bug fix                                    | ✅ regression required | —                 | —          | —          |
| Auth / permission change                   | ✅                     | ✅                 | ✅          | —          |
| External integration (API client, webhook) | ✅                     | ✅ mocked external | —          | —          |

<!-- Fill: extend this matrix with project-specific change types after repo-scan -->

## Unit test rules

- Mock all external calls: DB, external APIs, message queues, HTTP clients.
- Never hit real infrastructure in unit tests.
- Test: happy path, validation errors, boundary conditions, auth failures.

## Integration test rules

- Use a real test DB — never mock the database in integration tests.
  (Mocked-DB tests can pass while real migrations fail — integration tests catch this.)
- Mock external HTTP and third-party API calls.
- New API endpoints: test 401 (no token), 403 (wrong tenant/permission), happy path.

## Migration tests

- Every migration must be tested: apply runs cleanly, spot-check row counts and schema shape.
- Document explicitly if a migration is irreversible.

## Contract tests

- Required when a type from the shared types module changes.
- All modules importing the changed type must compile and their tests must pass after the change.

## Regression rule

- Bug fixes must include a test that would have caught the bug before the fix.
- Skipping a required test must be explained in DONE WHEN with explicit justification.

## Test location

| Type        | Location                                                          |
|-------------|-------------------------------------------------------------------|
| Unit        | Co-located `<file>.test.<ext>` or `__tests__/` adjacent to source |
| Integration | `tests/integration/<module>/`                                     |
| Migration   | `tests/migrations/`                                               |

<!-- Fill: adjust test locations per project structure after repo-scan -->

## Running tests

<!-- Fill after repo-scan — add project-specific test commands -->
See `AGENTS.md` build commands section.