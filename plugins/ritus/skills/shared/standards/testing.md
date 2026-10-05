# Testing standard

Which tests a change needs, and what makes a test count as evidence. `docs/TEST_CONVENTIONS.md` holds the project's
framework, naming, mocking, and fixture rules; where it disagrees with this file, it wins. When a framework-specific
testing skill is installed, use it for patterns. Run tests with the commands in `docs/PROJECT_CONTEXT.md`; if those
docs don't exist yet, use the stack's usual commands and say in your report that they are missing.

## A test counts when

- **It failed before the change.** For new logic and bug fixes, run the new test against the old behavior and watch it
  fail for the reason you expect, then make it pass. A test that was green from the start proves nothing about the
  change. If you wrote the code first, prove the test anyway: revert or break the behavior, see it fail, restore.
- **Its expected value is independent.** Take it from the spec, a worked example, or a reference computed another way -
  never by running the production formula and pasting its output. A test that mirrors the implementation passes when
  both are wrong.
- **You can name the break it catches.** For each test, say which change to the production code would make it fail -
  a flipped condition, a wrong constant, a dropped call. A test you can't name one for protects nothing: it checks a
  mock, restates the code, or asserts a type or a shape where a value belongs. Turned around: for each behavior the
  acceptance names, some test fails when that behavior breaks.
- **It lives in the test project for the assembly or package it exercises.** A test placed in another project still
  leaves its own project untested, and reviewers flag it.
- **A bug fix adds the test that would have caught the bug.**

One behavior at a time is a good rhythm, but the first green is not the finish line: the change is done when the edge
cases its acceptance and its domain call for are handled and tested.

## Existing tests

An existing test that goes red after your change is evidence, not an obstacle. Either the change broke the behavior
the test pins - fix the code - or the task deliberately changes that behavior: then update the test, and say in your
report which acceptance line or plan decision changes it. When the acceptance and an existing test can't both hold and
nothing in the task or plan says which wins, stop and report it: that is the user's call, not a test to edit.

Never turn a test green by weakening it: deleting or skipping it, loosening or removing an assertion, changing an
expected value to whatever the code now returns, or special-casing production code for a test's input or for running
under test. Each of these makes the check pass without making anything work, and hides the regression from every check
after yours. Whoever checks the change reads the diff of every existing test file for exactly this.

## What each change needs

| Change | Unit | Integration | Other |
|---|---|---|---|
| New service method | Happy path and the main failure path | - | - |
| New API endpoint | Input validation | Happy path; 401 without a token; 403 for another tenant or a missing permission | - |
| Background job or worker | Dispatch logic | Queue behavior | - |
| New table or column | - | - | The migration applies cleanly |
| Shared type or contract | Every caller compiles | - | Contract test |
| Bug fix | Regression test | - | - |
| Auth or permission change | Required | Required | Contract test |
| External integration (API client, webhook) | Required | External side mocked | - |

A refactor with no behavior change, a config-only change, or docs need no new test, but the existing tests still pass.
If you skip a test this table asks for, say why in your report.

## Mocks

Unit tests mock databases, queues, and HTTP. Integration tests use a real test database - a mocked one hides the query
bugs integration tests exist to catch - and mock only external services.

- Mock the boundary and assert on the code under test: what it returns, or the state it changes. A test whose only
  assertions are that a mock was called, or returned what the test told it to, tests the mock.
- Build fakes in the real shape - from the type or a recorded response - or the code passes against data it will never
  see.
- Don't add methods, flags, or branches to production code that only tests use.

## Checking someone else's tests

When you check a change you did not write, test its tests. Pick the logic the change adds or fixes that matters most -
the break the implementer named, or else its key condition, call, or constant - and break it in the working tree: copy
the file outside the repository, make the one-line change, run the tests that cover it, then copy the file back and
confirm it matches the copy byte for byte (a checksum, or `git diff --no-index` against the copy) - `git status` misses
a change to an untracked file. At least one test must fail. A break no test catches is a finding: the behavior it
breaks is unprotected, however green the suite is. One or two breaks on the riskiest logic are enough - this is a
spot check. When `docs/TEST_CONVENTIONS.md` names a mutation tool, running it on the changed files is the stronger
version.

## Where tests go

When `docs/TEST_CONVENTIONS.md` is silent: unit tests next to the source (`<file>.test.<ext>` or `__tests__/`),
integration tests in `tests/integration/<module>/`, migration tests in `tests/migrations/`.
