---
name: task-generation
description: Dispatched by ticket-review for STANDARD/EPIC changes - converts the approved review document into task files (plus QA files and an EPIC memory file when applicable), runs the self-review, and drafts the execution plan. Not invoked directly by the user; ticket-review owns the human gates.
argument-hint: Provide the approved review-document path, the exploration-log path, the branch slug, the classification (STANDARD/EPIC), and the QA mode
user-invocable: false
---

# Task Generation

**Core principle:** Turn an approved review document into precise, self-contained task files. You run
non-interactively AFTER human approval - never redesign the requirement or re-open settled questions.

## When to use

Dispatched as a fresh subagent by `ticket-review` for STANDARD/EPIC changes after its completeness gate, to keep the
template reads, the generated task text, the path-verification greps, and the cross-task consistency checks off the
main thread. Not invoked directly by the user. For SIMPLE changes `ticket-review` writes the 3-section note inline
instead of dispatching you.

When starting task-generation, create this TODO - **every item below, verbatim** (never a single item named after the skill) - and mark items done as you complete them:

TODO:

```markdown
- [ ] Read the approved review document + exploration log
- [ ] Generate task files (classification, granularity, naming)
- [ ] Generate QA files + EPIC memory file (when applicable)
- [ ] Self-review the task files
- [ ] Draft the execution plan
- [ ] Report the paths + execution plan back to ticket-review
```

## Operating constraints

- **Write-only task artifacts** - you write task files under `docs/tasks/{branch-slug}/`, per-task `.qa.md` files, and
  the EPIC memory file. Touch nothing else - no source files, no review document (approved and frozen), no skill files.
- **Fully non-interactive** - the review document is approved and every `[NEEDS CLARIFICATION]` is resolved before you
  start. You never ask the user; on a genuine blocker stop and report to ticket-review, never guess.
- **Return findings, not dumps** - the Output block returns paths + execution plan + coverage summary, never raw
  task-file contents.

## Inputs (from ticket-review)

- **Review-document path** - the approved review document that shapes every task.
- **Exploration-log path** - `docs/tasks/{branch-slug}/exploration.md`.
- **Branch slug** - the `docs/tasks/{branch-slug}/` directory to write into.
- **Classification** - STANDARD or EPIC (SIMPLE never reaches you).
- **QA mode** - off / task / epic-only, read from `docs/PROJECT_CONTEXT.md` (off when absent).

## Step 1: Read the approved review + exploration

Read the review document and the exploration log. Extract the acceptance criteria, the approach, the scope boundary,
the decisions, and the file / entry-point citations. Do not re-analyze or re-explore - the analysis is approved.

## Step 2: Generate task files

Read `templates/task-files.md` in this skill's directory for the STANDARD/EPIC full template.

### Classification -> format

| Level        | Task file format             |
|--------------|------------------------------|
| **STANDARD** | Full task file               |
| **EPIC**     | Full task file + memory file |

### Granularity rule

One task = one logical change. Merge when: same module, no inter-dependency, no shell needed. Split when: different
executor needed, true sequential dependency.

### Naming

Read the tasks/ path convention from `docs/PROJECT_CONTEXT.md` `## Team conventions`.

**Hard rules:**

- One task file per logical change.
- Task files live in `docs/tasks/{branch-slug}/` - never in source dirs.
- Do not touch another branch's task directory.

## Step 3: QA files + EPIC memory file

- **QA files** - read `templates/qa-files.md` in this skill's directory and generate a `.qa.md` per task when QA mode
  requires it.
- **EPIC memory** - for EPIC work read `templates/epic-memory.md` in this skill's directory and create the memory file.

## Step 4: Doc trigger matrix

This sets each task's DOC UPDATE section.

**Meta-rule:** Update docs only when the change affects how future humans or agents understand, navigate, or safely
modify the system.

| Change type                   | `docs/CUTOFF.md` | `docs/ARCHITECTURE.md` | `docs/DECISIONS.md` | `docs/LESSONS.md`      | `.qa.md`        |
|-------------------------------|------------------|------------------------|---------------------|------------------------|-----------------|
| Bug fix                       | ❌                | ❌                      | ❌                   | ✅ if dangerous pattern | ✅ if QA mode on |
| New endpoint                  | ✅                | ❌                      | ❌                   | ❌                      | ✅ if QA mode on |
| New module                    | ✅                | ✅                      | optional            | ❌                      | ✅ if QA mode on |
| New arch pattern / decision   | ❌                | ✅                      | ✅                   | ❌                      | ✅ if QA mode on |
| Config / env change           | ✅                | ❌                      | optional            | ❌                      | ❌               |
| Refactor (no contract change) | ❌                | ❌                      | ❌                   | ❌                      | ✅ if QA mode on |
| Auth / error / build changed  | ❌                | ❌                      | ✅                   | ❌                      | ❌               |

## Step 5: Self-review

Before presenting task files to the user, run this checklist yourself:

1. **Requirement coverage** - skim each acceptance criterion from the requirement source. Can you point to a task that
   implements it? List any gaps.
2. **DONE WHEN completeness** - every task has at least one diff-checkable and one command-checkable condition. No
   vague conditions ("works correctly", "handles errors").
3. **CONTEXT accuracy** - every file path in CONTEXT `files` exists (grep to confirm). No hallucinated paths.
4. **Cross-task consistency** - do function names, type names, and file paths used across tasks match? A function
   called `validateToken` in task 1 but `verifyToken` in task 3 is a bug. Check INTERFACES: each task's `Consumes`
   block matches a sibling task's `Produces` block - same names, parameters, and return types.
5. **No placeholders** - search for `TBD`, `TODO`, `[NEEDS CLARIFICATION]`, `implement later`, and hand-wave steps
   like "add appropriate error handling", "handle edge cases", "similar to task N" (without repeating the code), or
   "write tests for the above" (without the test code). All must be resolved with concrete content.
6. **Spec-grade sections present** - every STANDARD/EPIC task states CONSTRAINTS (or "none"), INTERFACES
   `Consumes`/`Produces` (or "none"), and NON-GOALS.

If you find issues, fix them inline. No need to re-review - just fix and move on. If you find a requirement with no
task, add the task.

## Step 6: Execution plan

Always output this block in chat after task files are created. Group tasks by dependency:

- **Parallel group**: tasks with no overlapping writable files. Can run simultaneously.
- **Sequential**: tasks that depend on a previous group's output or share writable files.

Determine grouping by checking overlap across CONTEXT files, DOC UPDATE paths, and related test files. If two tasks
share any writable file, they must be sequential. SIMPLE tasks (no CONTEXT section) always go in a sequential group.

```markdown
## Execution plan

### Group 1 (parallel):

- docs/tasks/<slug>/001-name.md
- docs/tasks/<slug>/002-name.md

### Group 2 (after group 1):

- docs/tasks/<slug>/003-name.md

### Batch commit message:

type(scope): overall subject

- task 1 summary
- task 2 summary

Breaking: none
Migration: none
```

You draft this and return it; the main thread presents it and drives dispatch.

## Output

Return to `ticket-review` (do not print raw file contents):

```text
TASK GENERATION COMPLETE

Task files:
- docs/tasks/{slug}/001-name.md
- ...

Execution plan:
<the grouped plan + batch commit message>

Coverage summary:
- <acceptance criterion> -> <task file>

Self-review: <pass, or the issues found and fixed>

QA / EPIC memory: <paths, or none>
```

## Hard rules

- One task file per logical change - never bundle unrelated changes.
- Task files live in `docs/tasks/{branch-slug}/` - never in source dirs.
- No executor field in task files.
- Positive instructions only in STEPS - no negative instructions.
- GOAL = expected outcome only, no implementation details.
- No placeholders (`TBD`, "add error handling", "handle edge cases", "similar to task N").
- Return findings, not dumps.

## Handoff

- **Report:** the task files + execution plan (the Output above). `ticket-review` runs the task-file approval gate and
  dispatches execution.
