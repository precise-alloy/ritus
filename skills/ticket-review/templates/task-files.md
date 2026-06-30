# Task File Templates

## TRIVIAL — no task file

Implement directly. Log in commit message only.

## SIMPLE — task note (3 sections)

```markdown
## TASK

<one focused logical change — imperative sentence>

## DONE WHEN

- [ ] <condition>
- [ ] Compiles without errors
- [ ] No files outside stated scope modified

## VERIFY

After implementation, dispatch a fresh `verify-task` subagent (model: haiku, effort: medium). Do not self-verify.
```

## STANDARD / EPIC — full task file

```markdown
## TASK

<one focused logical change — imperative sentence>
Classification: STANDARD | EPIC

## PRIOR CONTEXT

<!-- Remove for first-session tasks -->

- context: docs/memory/<branch-slug>-<feature-slug>-context.md
- done so far: <one-line summary>

## PATTERN

<!-- Reference ARCHITECTURE.md pattern, or "none" -->
none | Add a new <resource> | Add a new endpoint | ...

## CONTEXT

- files:
    - <entry-point path>
- docs (read-only references):
    - docs/PROJECT_CONTEXT.md

## GOAL

<expected outcome — from ACCEPTANCE CRITERIA>

## STEPS

<!-- Positive instructions only. No "don't do X". -->

1. grep/find to confirm paths before editing
2. ...

## DONE WHEN

- [ ] <condition from ACCEPTANCE CRITERIA>
- [ ] Compiles without errors
- [ ] Smoke test passes (new endpoints)
- [ ] Unit test passes (new business logic)
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

After implementation, dispatch a fresh `verify-task` subagent (model: haiku, effort: medium) to independently verify
DONE WHEN conditions. Do not self-verify — the reviewer must have a clean context.
If verification fails, dispatch `execute-task` (fresh subagent) to fix the gaps,
then dispatch a new `verify-task` subagent to re-verify. Repeat until PASS.

## DOC UPDATE

<!-- Apply doc trigger matrix — do not default to "update all" -->
<state each doc path + what to update, or "none required">

## COMMIT

type(scope): subject

- what changed and why
- key invariant enforced

Breaking: none
Migration: none
```
