---
name: execute-task
description: Implement one Ritus task file (docs/tasks/{branch-slug}/NNN-*.md) or debug case file (investigation-*.md) - use when asked to implement, execute, or work on a task file, when a driving TODO item calls for execute-task, or for a fix task created from verify-task or pr-review findings.
argument-hint: Task file path (plus the findings to fix, for a fix task)
---

# Execute Task

Implement one task from an approved plan. The user approved the task's **goal, acceptance, constraints, interfaces,
and non-goals** - those are binding. The *how* is yours: fit it to the code as it is now, not as the plan imagined it.
An independent check verifies your work from scratch, so optimize for work that is actually done, not for a report
that sounds done.

## Before you start

The task file is written for a reader with no prior context; read it fully, then what it points to - the plan, an EPIC
memory file, a Pattern (its checklist is in `docs/ARCHITECTURE.md`). Two sources are easy to skip and usually worth it:

- `docs/tasks/{branch-slug}/exploration.md` - what earlier tasks learned about this code and where they deviated.
- For a bug fix, the `docs/LESSONS.md` and `docs/DECISIONS.md` entries for the module.

Standards: `skills/shared/standards/engineering.md` and `testing.md` always; `security.md` when the change hits one of
its triggers (auth, user data, outside input, rendering, URL fetching, secrets or config, billing or admin actions,
migrations, shared contracts). Apply any extra standard your dispatch input names.

Other task shapes count too. In an older task file, STEPS (with `from:`/`to:` blocks) are decisions already made, and
DONE WHEN plus VERIFY are the acceptance. In a debug case file, the Proposed Fix is the decision and the Regression
Test is the acceptance.

## When the plan and the code disagree

Follow the plan's decisions unless the code as it is now makes them wrong - preferring another way is not a reason.
Plans do go stale, though. Decide by what resolving the mismatch would change:

- **Nothing binding** (a file moved, a helper already exists, the suggested approach fits poorly) - pick the
  conservative option, keep going, and record it under Deviations.
- **Something binding** (a `Produces` signature, a constraint, scope, user-visible behavior), or the plan is wrong at
  the design level (following it would ship a defect or a security hole) - stop and report `BLOCKED` with `file:line`
  evidence and a suggested correction, even when the correction is obvious. Binding changes are the user's call.
  Recording one under Deviations doesn't make it approved: sibling tasks were planned against the task file as
  written, and the independent check holds you to it.

## Gotchas

- The independent check re-runs your commands. Report what you observed, and only for commands you actually ran.
- DONE means the checks pass. When build or tests fail for a reason outside this task - a failure that was already
  there, a broken environment - report `BLOCKED` with the output instead of working around it.
- A bug report names a symptom. Before editing, find every caller of the function you are about to change and fix
  where the paths meet: one fix in the shared code is a smaller diff than one per caller, and patching only the path
  the ticket names leaves the other callers broken. That fix changes those callers too, and neither the ticket nor a
  diff of one shared function tells the reviewer so: give each caller whose behavior changes its own test, and name it
  under `Also affects`. If a caller's new behavior is something no spec or decision asks for, that is a scope call -
  report `BLOCKED`.
- For new logic and bug fixes, the test must fail before your change and pass after. A test that was already green
  proves nothing about the change.
- Know the break each new test catches, and name it in the report: the check after you makes that break and expects
  the test to fail.
- An existing test that goes red is evidence. Fix the code; update the test only when the task deliberately changes
  that behavior, and say which acceptance line does. Never delete, skip, or loosen a test, change its expected value to
  what the code now returns, or special-case code for a test's input (`testing.md` "Existing tests"). When the
  acceptance and an existing test can't both hold, that is `BLOCKED`.
- Expected values come from the spec or an independent reference, never from re-running the production formula.
- Tests belong in the test project for the assembly or package they exercise.
- String literals, status values, and field names are requirements: copy them from the ticket or plan, not memory.
- When the acceptance is met and its checks pass, stop. More than that - an option nobody passes, an abstraction for
  one use, a file or dependency the task doesn't name, a drive-by refactor - gets flagged by the independent check;
  name it under Follow-ups instead (`engineering.md` "Build what the task asks").

## Docs and notes

Update the docs the task names (Docs, or DOC UPDATE in an older file), including a QA file when it names one.

Append to `docs/tasks/{branch-slug}/exploration.md` (template: `skills/ticket-review/templates/exploration.md`) only
what a later task or wrap-up would want: reusable findings about the code, deviations and why, candidate lessons. If
there is nothing worth saying, leave it alone.

## If you are resumed

You may get a follow-up message instead of a new executor being started: a decision after your BLOCKED report, or
findings from the independent check. Re-read the task file first - a decision that changes the contract is written
there, and that is what the next check holds you to. Then send a complete report again: the next checker starts fresh
and sees only the report and the tree.

## Report

```text
Status: DONE | BLOCKED
Acceptance:
- <condition> - <evidence: file:line, or command -> observed result>
Files changed:
- <path> - <summary>
Tests added: none | <test> - fails if <the break it catches>, one per line
Tests changed: none | <existing test - what changed - the acceptance line or plan decision that changes it>
Deviations: none | <plan said / you did / why>
Also affects: none | <existing code the task does not name - behavior before -> after>
Docs updated: none | <path - what>
Follow-ups: none | <noticed, out of scope>
Blocker (BLOCKED only): <concern + evidence + suggested correction>

Commit message:
type(scope): subject

- what changed and why, including anything under Also affects
Breaking: none | <what breaks>
Migration: none | <what is needed>
```

Commit types: `feat` | `fix` | `refactor` | `test` | `docs` | `chore`. The user reviews the diff and commits.