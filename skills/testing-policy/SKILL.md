---
name: testing-policy
description: Loaded automatically by execute-task and verify-task for new services, endpoints, workers, or bug fixes - test type rules and coverage requirements. Do not invoke standalone
argument-hint: Provide the changed area and the type of behavior that needs validation
user-invocable: false
---

# Testing Policy

## When to use

Load this skill for any task that creates new services, endpoints, workers, or fixes bugs. Validate test coverage
against the matrix before reporting done.

## Test type matrix

| Change type                                | Unit                  | Integration       | Contract   | Migration  |
|--------------------------------------------|-----------------------|-------------------|------------|------------|
| New service method                         | required              | -                 | -          | -          |
| New API endpoint                           | auth + validation     | happy path        | -          | -          |
| New background worker / job                | dispatch logic        | queue behavior    | -          | -          |
| New DB table / column                      | -                     | -                 | -          | required   |
| Shared type / contract change              | all callers compile   | -                 | required   | -          |
| Bug fix                                    | regression required   | -                 | -          | -          |
| Auth / permission change                   | required              | required          | required   | -          |
| External integration (API client, webhook) | required              | mocked external   | -          | -          |

## Unit test rules

- Mock all external calls: DB, external APIs, message queues, HTTP clients.
- Never hit real infrastructure in unit tests.
- Test: happy path, validation errors, boundary conditions, auth failures.

## Integration test rules

- Use a real test DB - never mock the database in integration tests.
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

## Project-specific test conventions

Read `docs/TEST_CONVENTIONS.md` for this project's test conventions: framework, naming, mocking strategy, fixtures,
and async patterns. That file is filled by repo-scan and maintained by the team.

If a framework-specific testing skill is installed for your stack (e.g., Flutter integration testing, React test
patterns), load it alongside this skill for concrete patterns, APIs, and code examples.

## Running tests

See `docs/PROJECT_CONTEXT.md` build commands section. If `docs/PROJECT_CONTEXT.md` or `docs/TEST_CONVENTIONS.md`
don't exist yet, use reasonable defaults for the detected stack and flag missing docs in your report.

## Handoff

- **Report:** the standard applied to the parent skill's work.
