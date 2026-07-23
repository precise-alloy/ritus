---
name: ticket-review
description: Use after triage to produce task files - analyzes requirements from a plain description or a Jira, Azure DevOps, or GitHub Issues ticket, and generates execution plans.
argument-hint: Provide a requirement description or ticket URL(s)/key(s) (Jira, Azure DevOps, or GitHub Issues) with any additional context
---

# Ticket Review

**Core principle:** No task file without understanding the requirement first. Analyze, flag ambiguities, get user
approval - then generate tasks. Rushing to task generation produces tasks that solve the wrong problem.

## When to use

After triage classifies the change. This skill produces task files and execution plans.

When starting ticket-review, create this TODO - **every item below, verbatim** (never a single item named after the skill) - and mark items done as you complete them:

TODO:

```markdown
- [ ] Gather input (requirement source + context)
- [ ] Analyze requirement - STANDARD/EPIC: dispatch requirement-analysis subagent; SIMPLE: inline
- [ ] Review document ready (confirm/finalize) + user review gate
- [ ] Completeness gate
- [ ] Generate task files - SIMPLE: inline; STANDARD/EPIC: dispatch task-generation subagent
- [ ] Using `dispatch.md`, create the execution TODO, and dispatch
```

## Step 1: Gather Input

Ask the user for:

1. **The requirement source** - either:
   - A plain requirement description (summary of what needs to be done), OR
   - A ticket URL or key for any configured provider - capture just the reference here;
     `requirement-analysis` detects the provider and reads the ticket content in Step 2.
2. **Additional context** - verbal decisions, Slack discussions, architectural constraints, priority notes, or anything
   not captured in the requirement/ticket.

Gather only the requirement *source* here (the key/URL or description). The ticket's *content* is fetched downstream
by the `requirement-analysis` subagent. Hand the source to Step 2; the fetch happens there.

## Step 2: Analyze the requirement

Produce the review document that shapes every downstream task.

- **STANDARD / EPIC** - **dispatch a `requirement-analysis` subagent** (load `dispatch.md` in
  the `shared` skill directory for the run config) with the Step 1 intake: requirement source + context + branch
  slug / search key. It **fetches the ticket**, checks existing work, explores
  the code inline, flags ambiguities, and drafts the review document, then returns a findings summary, the review-doc
  path, any `[NEEDS CLARIFICATION]` / `[ASSUMPTION]` markers, raised concerns, and - for an incremental update - a
  diff summary + `up-to-date` flag. Keeping this read-heavy work in a subagent keeps the main thread's context lean,
  and keeps ticket-fetching inside `requirement-analysis`, the one skill that owns it - it loads the fetch helper in
  its own context, so here you only spawn it and hand over the intake. (Every ticket lands here: triage defaults a
  ticket to STANDARD because its content is not known yet, so a ticket is always STANDARD/EPIC at this point.)
- **Plain-text SIMPLE** - a lightweight inline analysis (no subagent, no fetch): extract acceptance criteria and
  the affected files / entry points with `file:line` citations. SIMPLE tasks skip the full review document. Only a
  plain-text requirement classifies SIMPLE here - a ticket is STANDARD/EPIC by default, so it always dispatches above.

**Own the interactions the subagent can't** (it is non-interactive):

- If it returns an incremental review with `up-to-date: yes`, tell the user the review is current and ask whether they
  want a full re-review.
- If it returns a diff summary, present that summary to the user.
- If it recommends a classification upgrade (e.g. STANDARD → EPIC), apply it before generating task files.

## Step 3: Review Document & User Review Gate

**First, make sure the review document is ready.** For STANDARD/EPIC, `requirement-analysis` drafted it in Step 2 -
open it at the returned path, confirm it's complete against `templates/review-document.md`, and fill any gaps. For a
plain-text SIMPLE requirement there's no full document - use the inline analysis. The review document is the overview
that shapes all subsequent tasks; it must exist and be approved before Step 5 generates any task files.

**Calibration - flag gaps, not polish.** When confirming the document, only flag issues that would cause a flawed
plan: a missing section, an internal contradiction, a requirement so ambiguous it could be built two different ways,
or scope large enough to need decomposition. Minor wording, stylistic preferences, and "some sections are less
detailed than others" are not gaps - treat the document as ready unless there is a serious gap that would mislead task
generation.

**Hard gate - present the review document (or, for SIMPLE, the inline analysis) to the user and wait for approval before proceeding.**

The user must review and confirm:

- Open questions and assumptions
- Proposed solutions and approach
- Scope boundaries
- Security or architectural concerns raised during analysis

Do NOT proceed to task generation until the user explicitly approves. If the user has feedback, send it back for a
re-analysis (re-dispatch `requirement-analysis` with the feedback, or revise inline for SIMPLE) and re-present.

## Step 4: Completeness Gate

Hard gate - do not proceed to task generation until all checks pass.

- [ ] User has approved the review document (Step 3)
- [ ] No `[NEEDS CLARIFICATION]` markers remain unresolved
- [ ] All acceptance criteria are testable (can be verified by diff or command)
- [ ] Success criteria have measurable outcomes (not "works correctly" - specify what "correct" means)
- [ ] Edge cases identified for each requirement (at minimum: empty input, missing data, concurrent access)
- [ ] Scope boundary is explicit - what this change does NOT affect is stated
- [ ] If touching auth/billing/tenant: security implications documented during analysis

If any check fails, resolve it before generating task files. Ask the user if needed - do not force-pass.

## Step 5: Generate Task Files

**SIMPLE (plain-text requirement)** - create a single SIMPLE task file under `docs/tasks/{branch-slug}/` (per naming conventions in `docs/PROJECT_CONTEXT.md`) using the SIMPLE template in
`skills/task-generation/templates/task-files.md`. No subagent.

**STANDARD / EPIC** - after the completeness gate (Step 4) passes, **dispatch a `task-generation` subagent** (load
`dispatch.md` in the `shared` skill directory for the run config), handing over:

- the approved review-document path;
- the exploration-log path (`docs/tasks/{branch-slug}/exploration.md`);
- the branch slug - current git branch with `/` → `-` (e.g. `feat/PROJ-42-auth` → `feat-PROJ-42-auth`);
- the classification (STANDARD/EPIC, including any EPIC upgrade from Step 2);
- the QA mode (from `docs/PROJECT_CONTEXT.md`; off when absent).

It generates the task files under `docs/tasks/{branch-slug}/` (plus QA files and an EPIC memory file when applicable),
runs the self-review, drafts the execution plan, and returns the task-file paths + execution plan + coverage summary -
keeping template reads, generated task text, path-verification greps, and cross-task consistency off the main thread,
which owns the task-file approval gate and dispatch below.

**Branch slug rule:** take current git branch name, replace `/` with `-`.
Example: `feat/PROJ-42-auth-refresh` → slug `feat-PROJ-42-auth-refresh`

**Hard rules (the subagent enforces; you confirm on return):** one task file per logical change; task files live in
`docs/tasks/{branch-slug}/`, never in source dirs; never touch another branch's task directory.

## Hard rules

- Triage before generating task files - no exceptions
- SIMPLE: 3-section task note (TASK + DONE WHEN + VERIFY), written inline
- Safety override (changes touching auth, billing, migrations, tenant isolation, infra, or shared contracts) is non-negotiable - always upgrade to STANDARD
- STANDARD/EPIC: `task-generation` writes the task files; the main thread presents the returned file paths + execution plan in chat
- No full repo scan
- `Last Reviewed` datetime (UTC) is mandatory in every review file
- If anything is unclear, flag it with `[NEEDS CLARIFICATION]` - do not assume. All markers must be resolved before task generation
- Security and compliance concerns must always be raised explicitly

## Handoff

- **Report:** the task files + execution plan.
- **TODO update:** on user approval, generate the run's driving TODO - see **Dispatch execution** below.

## Dispatch execution

**Use the `dispatch.md` you loaded in Step 2** - it holds the dispatch rule and per-worker run config (model /
effort), which you need to spawn the subagents below. If you took the plain-text SIMPLE path (inline analysis, no
subagent), load it now.

After generating task files (SIMPLE: the single SIMPLE task file; STANDARD/EPIC: after `task-generation` returns), **present the task files and execution plan to the user for review.** Do not
dispatch subagents until the user approves. The user may adjust task scope, reorder priorities, or request changes.

Once the user approves:

1. **Ensure the exploration log exists** - `requirement-analysis` seeds `docs/tasks/{branch-slug}/exploration.md`
   during analysis; if it's missing (e.g. the SIMPLE inline path), create it with the header from
   `skills/ticket-review/templates/exploration.md`. It must exist before any execute-task subagent starts.
2. **Create the execution TODO list** from the execution plan - the concrete per-task tracker for implementation:

TODO:

```markdown
- [ ] Implement task 001: <name> - dispatch execute-task subagent
- [ ] Verify task 001 - dispatch verify-task subagent
- [ ] Implement task 002: <name> - dispatch execute-task subagent
- [ ] Verify task 002 - dispatch verify-task subagent
  ...
- [ ] Run pr-review for full ticket - dispatch pr-review subagent
- [ ] If pr-review approves: invoke wrap-up
```

For parallel groups, list all tasks in the group together. Mark each item as subagents complete. If verify-task
returns FAIL, add fix items inline before marking the original task done. If the final pr-review returns Request
Changes (not Approve), the main thread runs the fix cycle from `dispatch.md`'s outcome table - create a SIMPLE fix
task from the findings, then execute-task → verify-task → re-review, capped by the circuit breaker; wrap-up runs only
after an Approve.

Then walk this driving TODO per the dispatch rule:

- **Parallel groups**: dispatch the group's execute-task subagents simultaneously, then their matching verify-task
  subagents; a verify FAIL inserts fix items before the task is marked done.
- **Sequential groups**: wait for the previous group's tasks to all pass verification before starting.

Do not implement tasks in this session.
