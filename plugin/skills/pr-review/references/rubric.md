# Review rubric

Five angles on the same change. Each asks a different question, and together they cover how changes usually break.
Spend the time where the diff is riskiest, not evenly.

## 1. Requirement mismatch

- List the acceptance criteria, the test data the ticket names, and the expected behavior, taking the sources in the
  order of `docs/PROJECT_CONTEXT.md` `## Requirement source precedence`.
- For each criterion, try to build the input that makes the code do the wrong thing, or silently nothing.
- Look for criteria met in name only: the code path exists, but it behaves differently from what the ticket says.

## 2. Fault injection

For every changed function or path:

- Null, empty, or whitespace input; a missing config value.
- Boundaries: zero, negative, the maximum, a single element, the longest string.
- Two calls at once on shared state; a call order the code assumes but doesn't enforce.
- A dependency that fails - an API, a query, a file read. Is the failure swallowed?

## 3. Blast radius

- Trace each changed public interface to its callers and consumers. Is any caller not updated?
- Implicit contracts: a function that could not return null now can; an error type changed; an order changed.
- Removed or renamed symbols still referenced in views, JSON contracts, config, or docs.
- Registrations that must change with the code: dependency injection, routes, feature flags.

## 4. Security

Apply `skills/shared/standards/security.md` for every trigger the change hits. In any case, look for:

- User-controlled input reaching a query, HTML, a shell command, or a file path without the right encoding or check.
- Data or actions newly reachable without the right authentication or authorization, and IDs a user can change to
  reach someone else's data.
- Internals leaking through error messages, logs, or responses.

## 5. Completeness

- Every acceptance criterion is met, partial, or missing, with its evidence.
- Logic without a test is suspect. Each test `skills/shared/standards/testing.md` requires exists and would fail
  without the change: name the break each new test catches. A test you can't name one for - it checks a mock,
  recomputes the production formula, or asserts only a type or a shape - is a `test` finding. When no per-task
  verification ran, confirm it on the riskiest logic with the spot check in `testing.md`.
- Existing tests the diff weakens - deleted, skipped, a loosened assertion, an expected value changed to match the new
  output - need a reason in the plan or task files; without one it is a blocking `test` finding, since it hides
  whatever made the test fail. Production code that special-cases a test's input, or checks whether it runs under
  test, is a `logic` finding.
- Requirements missing from the diff entirely.
- Docs: what the task files' Docs sections name is updated, and module docs where a public interface changed.
- Traceability: ticket IDs and rationale appear where `docs/PROJECT_CONTEXT.md` `## Team conventions` requires them.
- With QA mode on, the QA file follows `skills/ticket-review/templates/qa-files.md`.
- Reuse: new code that duplicates an existing helper, the standard library, or the platform. Report it with its
  replacement and the evidence that behavior is preserved.
- Code the plan doesn't ask for: an option, parameter, or flag no caller passes; an interface, base class, or factory
  with one implementation; a file or dependency the plan and task files don't name; a guard or fallback for a state
  the code can't reach. Show it unused - search for its callers - and name what to remove. It is a `scope` finding
  (`references/findings.md`).
