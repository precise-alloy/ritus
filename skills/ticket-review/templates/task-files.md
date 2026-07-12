# Task File Templates

## SIMPLE - task note (3 sections)

```markdown
## TASK

<one focused logical change - imperative sentence>

## DONE WHEN

<!-- For a command-checkable condition, state its expected result so verify-task can re-run and match. -->

- [ ] <condition - for a command, state the expected result, e.g. `<command>` → <expected output>, exit 0>
- [ ] Compiles without errors
- [ ] No files outside stated scope modified

## VERIFY

Verified fresh by a verify-task subagent.

Concrete check (exact command → expected result):

- <one-line command that exercises the change> → <expected observable output>
```

## STANDARD / EPIC - full task file

<!-- Write the task self-contained for a fresh executor that has zero prior context: it sees only this file plus the
     CONTEXT docs. Pin exact names, signatures, and commands. No placeholders (no "TBD", "add error handling",
     "handle edge cases", "similar to task N"). -->

```markdown
## TASK

<one focused logical change - imperative sentence>
Classification: STANDARD | EPIC

## PRIOR CONTEXT

<!-- Remove for first-session tasks -->

- context: docs/memory/<branch-slug>-<feature-slug>-context.md
- done so far: <one-line summary>

## PATTERN

<!-- Reference docs/ARCHITECTURE.md pattern, or "none" -->
none | Add a new <resource> | Add a new endpoint | ...

## CONSTRAINTS

<!-- Invariants that must hold, copied verbatim - project-wide rules relevant to this task plus task-specific ones.
     Write as explicit requirements ("must" / "must not"); the executor treats each line as a hard requirement. Use "none" if none apply. -->

- <e.g. Must render user input as plain text (must not use an HTML-injection sink)>
- <e.g. Public API responses must stay backward-compatible - additive fields only>

## CONTEXT

- files:
    <!-- Annotate each path: Create | Modify:<line-range> | Test, plus a one-line responsibility. -->
    - <path> — Create | Modify:<line> | Test — <one-line responsibility>
- docs (read-only references):
    - docs/PROJECT_CONTEXT.md

## INTERFACES

<!-- The executor sees only this task file. Pin the exact signatures shared with sibling tasks so names and types
     cannot drift. Use "none" when the task has no cross-task surface. -->

- Consumes: <exact signature(s) this task relies on from earlier tasks, e.g. `verifyToken(token: string): Claims`> | none
- Produces: <exact signature(s) later tasks depend on - names, params, return types> | none

## GOAL

<expected outcome - from ACCEPTANCE CRITERIA>

## NON-GOALS

<!-- Explicit out-of-scope so the executor does not over-reach. State what NOT to build or touch, and why.
     Use "none" if the scope is fully covered by CONTEXT. -->

- <e.g. No caching layer - deferred to a later task>

## STEPS

<!-- Positive instructions only. One action per step. For new logic follow TDD order: write the failing test ->
     run it (show command + expected FAIL) -> implement -> run it (show command + expected PASS). Every command step
     names the exact command and its expected output; if actual output does not match expected, stop and report
     instead of continuing. Show real code: for new code show it in full; for edits show the exact `from:` -> `to:`
     blocks located by grep / surrounding content, not line numbers. Never "add X here". -->

1. grep/find to confirm paths before editing
2. ...

## DONE WHEN

<!-- Each command-checkable condition is re-run by verify-task against the expected result stated in VERIFY. -->

- [ ] <condition from ACCEPTANCE CRITERIA>
- [ ] Compiles without errors
- [ ] Smoke test passes (new endpoints)
- [ ] Unit test passes (new business logic)
- [ ] CONSTRAINTS all satisfied; nothing under NON-GOALS implemented
- [ ] INTERFACES honored: `Produces` signatures exposed as written; `Consumes` used exactly as given in INTERFACES
- [ ] No files outside CONTEXT + DOC UPDATE + related test files modified
- [ ] All PATTERN steps completed or marked N/A
- [ ] No claim made about existing code without citing file:line
- [ ] If interface changed: skill file for affected module updated or rewritten
- [ ] Standards validated: all applicable gates from `definition-of-done` skill checked
- [ ] DOC UPDATE completed

<!-- If QA mode is task: -->

- [ ] `{task-name}.qa.md` generated with accurate affected features and risk level
- [ ] Executor verified: QA IMPACT matches actual changes made

## VERIFY

Verified fresh by a verify-task subagent, in a clean context separate from the implementer's. On FAIL, the main thread
owns the fix loop — it appends the fix + re-verify steps and applies the circuit breaker (cap: 3 attempts) from
`skills/shared/dispatch.md`.

Concrete checks (exact command → expected result):

- Build: `<build command from docs/PROJECT_CONTEXT.md>` → exit 0
- Test: `<test command>` → 0 failures
- Smoke: `<one-line command that exercises the change>` → <expected observable output>

## DOC UPDATE

<!-- Apply doc trigger matrix - do not default to "update all" -->
<state each doc path + what to update, or "none required">

## COMMIT

type(scope): subject

- what changed and why
- key invariant enforced

Breaking: none
Migration: none
```
