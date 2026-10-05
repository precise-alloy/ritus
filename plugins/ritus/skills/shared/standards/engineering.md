# Engineering standard

What "done" means for a code change in a Ritus run, and the few opinions where this team differs from a capable
engineer's defaults. `docs/CODE_CONVENTIONS.md` holds the project's own rules (naming, structure, error handling,
logging); where it disagrees with this file, it wins.

## Done means

- It builds, lint reports no errors, and the tests pass - using the commands in `docs/PROJECT_CONTEXT.md`, actually
  run. When a command is not configured, say so; don't count it as passed.
- The diff is the task's diff: every changed file is accounted for by the task - its starting points, its tests, the
  docs it names.
- No secrets, keys, or credentials in changed files, logs, or error messages.
- In a typed language, no new untyped value (`any`, `object`, `dynamic`) without a comment saying why.

## Opinions

- **Reuse before you add.** Look for an existing helper, pattern, or library call before writing a new one. A
  reviewer's first question about new code is why the existing one wasn't used.
- **Match the code around you** - its naming, error handling, and structure - even where you would choose differently.
- **Inside the codebase, change the callers.** Don't leave shims, flags, or deprecated paths for code you can update in
  the same change. Compatibility is a requirement only at a boundary you don't control - a public API, persisted
  data, another team's consumer - and then the task says so under Constraints.
- **Extract a helper when it removes duplication the change would otherwise add**, not in anticipation of reuse.
  Three similar lines cost less than the wrong abstraction.
- **Build what the task asks, at the scope it asks.** No option, parameter, or flag the acceptance doesn't use; no
  interface, base class, or factory with one implementation; no file the task doesn't name - a README, a summary, a
  module for a single call; no new dependency unless the task or plan names it. Current models add these unasked, and
  each is code someone reviews and keeps; an option nobody passes is a path no test exercises. When you think one would
  help, name it as a follow-up instead of building it.
- **Guard what can happen.** Validate at the boundaries - input from users, files, the network, another team's code -
  and let internal calls trust their callers. A check or fallback for a state the code can't reach adds a branch no
  test takes, and hides the bug that would put the code there.
- **Understand the flow before choosing the smallest change.** A minimal diff in the wrong place is a second bug.
- **Stay in scope.** A refactor or cleanup outside the task goes in your report as a follow-up, not into the diff.
- **Don't swallow errors.** Handle an error or let it propagate with context; a catch that returns a default hides the
  failure from the caller and from the tests.
- **Comments say what the code can't:** a non-obvious constraint, an invariant, a workaround and what it works around.
  For a deliberate simplification, name its limit and the sign that it is time to revisit it.
- No circular imports between modules.

## By change type

Check the rows the change touches. The tests each row needs are in `testing.md`; risk areas also get `security.md`.

| Change | Also done when |
|---|---|
| New endpoint | Auth guard and ownership scoping are in place, required inputs are validated, and errors return a structured response rather than a stack trace |
| Background job or worker | A failure is logged with the job ID and the error; retry behavior is deliberate, not accidental |
| Database migration | It runs cleanly; row counts and schema shape are spot-checked; queries are parameterized; an irreversible migration says so |
| Shared type or contract | Every module that imports it still compiles |
| UI | Loading, error, and empty states are handled; inputs have labels; images and controls have accessible names |
