---
name: execute-task
description: Use when given a task file to implement - reads context, implements steps, runs tests, reports results. TRIGGER - invoke when user says "implement task", "run task", "execute task", "work on task", or provides a task file path (e.g., docs/tasks/.../*.md)
argument-hint: Provide the task file path, requirement source, and expected validation commands
---

# Execute Task

Implement the approved task contract. Complete every STEP and address every DONE WHEN condition before reporting
the implementation result.

## Process

Create this TODO verbatim and mark each item done as it completes:

TODO:

```markdown
- [ ] Read the task file using the applicable task shape below.
- [ ] Load CONTEXT and available PRIOR CONTEXT + exploration log; for bugs, search LESSONS and DECISIONS.
- [ ] Load applicable standards before implementation.
- [ ] Apply the relevant ARCHITECTURE checklist when PATTERN is set.
- [ ] Implement the task against current files and its constraints.
- [ ] Run build + tests per DONE WHEN and the exact VERIFY commands with their expected results.
- [ ] Complete DOC UPDATE and record reusable findings in the exploration log.
- [ ] Report the implementation result and each DONE WHEN outcome.
```

## Task contract

| Shape | Interpretation |
|---|---|
| SIMPLE | Implement TASK and satisfy DONE WHEN + VERIFY; follow STEPS when present. |
| STANDARD / EPIC | Read all sections, including CONSTRAINTS, INTERFACES, NON-GOALS, and DOC UPDATE. |
| Investigation case file | Use `Proposed Fix` as STEPS and `Regression Test` as DONE WHEN. |

Use the task's stated scope, keep NON-GOALS excluded, satisfy every CONSTRAINTS line, use INTERFACES `Consumes`
signatures verbatim, and expose `Produces` exactly as specified.

- Read referenced CONTEXT files and `docs/tasks/{branch-slug}/exploration.md` when present. For bug fixes, search
  `docs/LESSONS.md` and `docs/DECISIONS.md` for the affected module. Resolve PATTERN through `docs/ARCHITECTURE.md`.
- Confirm referenced existing paths and each STEP's `from:` block against current code before applying its `to:`.
  Execute a valid STEP as written when the only objection is preference.
- An unclear STEP, missing referenced input, stale block, or demonstrated code contradiction, compile defect, or
  security flaw ends the attempt with `BLOCKED: <concern + evidence + suggested correction>`. Cite `file:line`.
- An unexpected command status or output ends the attempt with a failure report. Compare every prescribed result,
  including the intended assertion failure in a red step.
- Apply DOC UPDATE when present. Append reusable patterns, gotchas, or decisions to the exploration log using
  `skills/ticket-review/templates/exploration.md`, creating the log when needed. A SIMPLE task with neither a doc
  update nor a reusable finding leaves those artifacts untouched.

## Standards

Load and apply every matching standard before editing code:

<!-- Keep in sync with verify-task/SKILL.md -->

| Task touches | Load skill |
|---|---|
| Any code change | `code-conventions` |
| New service / endpoint / worker / bug fix | `testing-policy` |
| New business logic, new API endpoint, or bug fix | `tdd` |
| Auth / billing / migration / tenant isolation / infra config / shared contracts | `security` |
| Any STANDARD or EPIC task | `definition-of-done` |

## Output format

Return one final report after completing the work, or the blocker/failure when progress stops. Address each DONE WHEN
condition in the existing summaries, cite `file:line` for code claims, and summarize command outcomes and failures.

```text
Files changed:
- path - summary

Docs updated:
- path - what changed   (or: none required)

Commit message:
type(scope): subject

- what changed and why
- key invariant enforced (if any)

Breaking: none | <what breaks>
Migration: none | <migration needed>
```

Commit types: `feat` | `fix` | `refactor` | `test` | `docs` | `chore`

## Handoff

- **Report:** your implementation report (files changed + commit message), or `BLOCKED: <concern + evidence + suggested correction>` when a STEP is unclear or provably wrong.
- **TODO update:** Implemented → `Verify - dispatch verify-task subagent` for this task. BLOCKED → `Fix plan - correct the STEPS, then dispatch execute-task subagent`.
