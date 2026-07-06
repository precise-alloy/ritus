---
name: ticket-review
description: Use after triage to produce task files — analyzes requirements, fetches Jira or Azure DevOps tickets, and generates execution plans. Reached via triage's Next section, not invoked directly for code review. Do NOT use for reviewing code diffs or PRs — that is pr-review
argument-hint: Provide a requirement description or Jira/Azure DevOps ticket URL(s) with any additional context
---

# Ticket Review

**Core principle:** No task file without understanding the requirement first. Analyze, flag ambiguities, get user
approval — then generate tasks. Rushing to task generation produces tasks that solve the wrong problem.

## When to use

After triage classifies the change. This skill produces task files and execution plans.

When starting ticket-review, create this TODO and mark items as you complete them:

TODO:

```markdown
- [ ] Gather input (requirement source + context)
- [ ] Check existing work (review files, task files, memory)
- [ ] Fetch and analyze requirements
- [ ] Create review document + user review gate
- [ ] Generate task files + self-review
- [ ] Present to user for approval
- [ ] Create execution TODO and dispatch
```

## Step 1: Gather Input

Ask the user for:

1. **The requirement source** — either:
   - A plain requirement description (summary of what needs to be done), OR
   - Jira ticket URL(s)/key(s) or Azure DevOps work item URL(s)/ID(s) matching docs/PROJECT_CONTEXT.md
     `## Team conventions` ticket format
2. **Additional context** — verbal decisions, Slack discussions, architectural constraints, priority notes, or anything
   not captured in the requirement/ticket.

## Step 2: Check Existing Work

After gathering input, **always** check for existing review and task files before proceeding:

1. Determine the search key:
   - If ticket URL provided → use ticket ID (e.g., `PROJ-123`)
   - If plain requirement → use the current branch slug (e.g., `feat-add-login`)
2. Check if a review document exists in the ticket reviews path (from docs/PROJECT_CONTEXT.md `## Documentation layout`)
   matching the search key.
3. Check if `docs/tasks/` contains any task files matching the search key.
4. Check if `docs/memory/` contains any context files matching the search key.

### If existing files are found → Incremental Update

When a review file already exists, perform an incremental update:

1. Read the existing review file and note the `Last Reviewed` datetime (UTC).
2. **If ticket URL provided:** fetch the ticket's change history (changelog) and comments since that datetime using
   `remote-api-access.md` in the `shared` skill directory. Identify description updates, new comments, status changes,
   acceptance criteria updates.
3. **If plain requirement:** compare the user's current description against the existing review — identify what changed.
4. If there are **no changes** — inform the user that the review is up-to-date and ask if they want a full re-review.
5. If there **are changes**, reflect them into the review document and associated task files:
   - Move answered questions from "Open Questions" to "Decisions".
   - Update assumptions that have been confirmed or invalidated.
   - Adjust task lists if scope changed.
   - Update the `Last Reviewed` datetime to the current UTC time.
6. Present a **diff summary** to the user showing what changed in the review.

### If no existing files are found → Full Analysis

Proceed to Step 3 and perform the full analysis workflow.

## Step 3: Fetch Ticket (if ticket URL provided)

**Skip this step if the user provided a plain requirement.**

Read `remote-api-access.md` in the `shared` skill directory for the remote API helper instructions.

Fetch ticket details and comments via the helper. Live ticket data is required before producing the review document.

Parse ticket keys/work item IDs according to docs/PROJECT_CONTEXT.md `## Team conventions` ticket format.

For Jira tickets:

```bash
bun run "<plugin-root>/scripts/remote-api.ts" jira issue "<TICKET_KEY_OR_URL>" "summary,description,status,issuetype,comment,acceptance_criteria"
```

For Azure DevOps work items:

```bash
bun run "<plugin-root>/scripts/remote-api.ts" ado issue "<WORK_ITEM_URL_OR_ID>" "System.Title,System.Description,System.State,System.WorkItemType,System.Tags"
bun run "<plugin-root>/scripts/remote-api.ts" ado comments "<WORK_ITEM_URL_OR_ID>"
```

If either provider returns `401`, `403`, or a permission-style `404`, stop and ask the user to verify remote access.
Do not continue with stale or partial ticket data.

Apply docs/PROJECT_CONTEXT.md `## Requirement source precedence`.

## Step 4: Analyze Requirements

### 4.1 Identify Requirements

From the requirement source (ticket description + comments, or plain requirement text), extract:

1. **Acceptance criteria** — what must be true for the work to be considered done.
2. **Expected behavior** — how the feature/fix should work.
3. **Test data** — any specific values, scenarios, or edge cases mentioned.
4. **Constraints** — performance, security, compatibility notes.

### 4.2 Analyze Related Code

Based on the requirements, search the codebase to identify:

- **Existing code** that implements related functionality.
- **Entry points** (controllers, API endpoints, blocks, pages) affected.
- **Services and helpers** that will need changes.
- **Models and DTOs** that may need updates.
- **Configuration** files or constants involved.

Use semantic search, grep, and file exploration across the source layout defined in docs/PROJECT_CONTEXT.md `## Source layout`.

### 4.3 Check for UI Changes

If the requirements involve UI updates (new components, layout changes, styling, frontend behavior):

1. Inspect frontend/UI paths from docs/PROJECT_CONTEXT.md `## Source layout`.
2. Skip generated artifact paths listed in docs/PROJECT_CONTEXT.md `## Source layout`.

### 4.4 Analyze Attached Images

If the Jira ticket or requirement includes image attachments (screenshots, mockups, annotated images):

First, download the images locally so they can be viewed:

```bash
bun run "<plugin-root>/scripts/remote-api.ts" jira attachment-download "<TICKET_KEY>" ".jira-attachments/<TICKET_KEY>"
```

Then read each downloaded image using the `Read` tool (which supports images). The download command returns
a JSON list of `{ filename, path }` entries — use the `path` values.

If the download fails or returns no images, ask the user to share the screenshots directly.

After downloading:

1. Read the ticket description and acceptance criteria FIRST — understand what the customer expects.
2. THEN examine each image against that context:
   - **What I see** — describe specific elements, not just general layout. Count items, read text, note states.
   - **What the ticket says should happen** — the expected behavior from 4.1.
   - **The gap** — what differs between what the image shows and what the ticket expects.
3. For annotated images (arrows, circles, highlights):
   - Identify what the annotation is pointing at — the specific element, not "an area of the page."
   - Infer intent from the ticket context — "red circle on dropdown + ticket says 'wrong options'" → the dropdown
     content is the issue, not the dropdown's existence.
4. Document image findings in the review document under `## Visual References`.

**Do NOT** just describe images in isolation. Always cross-reference against the ticket requirements.

### 4.5 Review Existing Documentation

Check documentation paths listed in docs/PROJECT_CONTEXT.md `## Documentation layout` for existing documentation related
to the feature area.

### 4.5b Research Technical Options

**Conditional** — run this step only for STANDARD/EPIC tasks that involve:

- New external dependency or library choice
- New integration with an unfamiliar system or API
- Architectural pattern not yet used in this codebase
- Technology choice where multiple viable options exist

Skip for bug fixes, refactors, and features that extend existing patterns.

When triggered:

1. **Search the codebase first** — check if the project already uses a library or pattern for this. If it does,
   use what exists. Do not propose alternatives unless the existing solution cannot meet the requirements.
2. **Investigate options** — for genuinely new choices, research 2-3 options. For each, note:
   - Compatibility with the project's stack (from `docs/PROJECT_CONTEXT.md`)
   - Maintenance status and community support
   - Performance characteristics relevant to the use case
   - Security implications
3. **Recommend one option** with rationale. Do not present a menu — make a decision and justify it.
4. **Record the decision** — write a `DECISION-NNN` entry per Step 4.8 if the choice is non-obvious.

Keep research lightweight — this is a 10-minute investigation, not a spike. If research would take longer, flag it
as `[NEEDS CLARIFICATION: requires spike — <what to investigate>]` and let the user decide whether to invest the
time.

### 4.6 Flag Ambiguities

For every requirement that could be interpreted two ways, mark it:

- `[NEEDS CLARIFICATION: <specific question>]` — ambiguous requirement, blocks task generation.
- `[ASSUMPTION: <what you assumed and why>]` — reasonable default chosen, does not block but must be visible.

Rules:

- Do NOT guess when two interpretations lead to different implementations. Flag it.
- Every `[NEEDS CLARIFICATION]` marker must include a specific question, not just "this is unclear."
- Read `docs/STAKEHOLDERS.md` to identify who should answer each question. Frame questions so they can be forwarded
  to non-technical stakeholders if needed.
- Clearly distinguish between questions that block implementation vs nice-to-have clarifications.

### 4.7 Raise Concerns

Proactively raise any concerns related to:

- **Security** — authentication, authorization, input validation, data exposure, injection risks.
- **Performance** — N+1 queries, large payloads, missing caching, scalability.
- **Breaking changes** — API contract changes, backward compatibility.
- **Data integrity** — race conditions, partial updates, migration risks.

These must be documented in the output so they can be reviewed before implementation begins.

### 4.8 Record Architectural Decisions

If a non-obvious architectural decision was made during analysis (e.g., chose JWT over sessions, picked a specific
library, decided on a data model shape), write a `DECISION-NNN` entry to `docs/DECISIONS.md`:

```text
### DECISION-NNN: <title>
Date: YYYY-MM-DD
Context: <what prompted this>
Decision: <what was decided>
Rationale: <why — tradeoffs>
Consequences: <what this constrains or enables>
```

Skip this step if all decisions were obvious or already documented.

## Step 5: Create Review Document

For STANDARD and EPIC classifications, create a review document.

Read `templates/review-document.md` in this skill's directory for the template format.

## Step 5a: User Review Gate

**Hard gate — present the review document to the user and wait for approval before proceeding.**

The review document is the overview that shapes all subsequent tasks. The user must review and confirm:

- Open questions and assumptions
- Proposed solutions and approach
- Scope boundaries
- Security or architectural concerns raised in Step 4.7

Do NOT proceed to Step 6 until the user explicitly approves. If the user has feedback, update the review document
and re-present for approval.

## Step 5b: Completeness Gate

Hard gate — do not proceed to Step 6 until all checks pass.

- [ ] User has approved the review document (Step 5a)
- [ ] No `[NEEDS CLARIFICATION]` markers remain unresolved
- [ ] All acceptance criteria are testable (can be verified by diff or command)
- [ ] Success criteria have measurable outcomes (not "works correctly" — specify what "correct" means)
- [ ] Edge cases identified for each requirement (at minimum: empty input, missing data, concurrent access)
- [ ] Scope boundary is explicit — what this change does NOT affect is stated
- [ ] If touching auth/billing/tenant: security implications documented in Step 4.7

If any check fails, resolve it before generating task files. Ask the user if needed — do not force-pass.

## Step 6: Generate Task Files

Convert the analyzed requirements into task files + execution plan.

Read `templates/task-files.md` in this skill's directory for TRIVIAL, SIMPLE, and STANDARD/EPIC templates.

### Classification

Use the classification level assigned by triage. If triage defaulted to STANDARD because the input was a ticket key,
upgrade to EPIC after fetching if the ticket involves multi-session work, multiple modules, or new architecture
patterns. Map to task file format:

| Level        | Task file format                     |
|--------------|--------------------------------------|
| **TRIVIAL**  | Direct fix — no task file            |
| **SIMPLE**   | 3-section: TASK + DONE WHEN + VERIFY |
| **STANDARD** | Full task file                       |
| **EPIC**     | Full task file + memory file         |

### Granularity rule

One task = one logical change.
Merge when: same module, no inter-dependency, no shell needed.
Split when: different executor needed, true sequential dependency.

### Naming convention

See docs/PROJECT_CONTEXT.md `## Team conventions` for tasks/ path convention.

**Branch slug rule:** take current git branch name, replace `/` with `-`.
Example: `feat/PROJ-42-auth-refresh` → slug `feat-PROJ-42-auth-refresh`

**Hard rules:**

- One task file per logical change — never bundle unrelated changes
- Task files live in `docs/tasks/` — never in project source directories
- Do not touch another branch's task directory

### QA files

Read `templates/qa-files.md` in this skill's directory for QA file formats and rules.

### EPIC memory file

For EPIC work, read `templates/epic-memory.md` in this skill's directory for the memory file template.

## Doc trigger matrix

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

## Execution plan

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

## Hard constraints

- Triage before generating task files — no exceptions
- TRIVIAL: implement directly, no task file
- SIMPLE: 3-section task note (TASK + DONE WHEN + VERIFY)
- Safety override (changes touching auth, billing, migrations, tenant isolation, infra, or shared contracts) is non-negotiable — always upgrade to STANDARD
- No executor field in task files
- STANDARD/EPIC: output file paths + execution plan in chat
- No negative instructions in STEPS
- No full repo scan
- GOAL = expected outcome only, no implementation details
- `Last Reviewed` datetime (UTC) is mandatory in every review file
- If anything is unclear, flag it with `[NEEDS CLARIFICATION]` — do not assume. All markers must be resolved
  before Step 6
- Security and compliance concerns must always be raised explicitly

## Self-review

Before presenting task files to the user, run this checklist yourself:

1. **Requirement coverage** — skim each acceptance criterion from the requirement source. Can you point to a task that
   implements it? List any gaps.
2. **DONE WHEN completeness** — every task has at least one diff-checkable and one command-checkable condition. No
   vague conditions ("works correctly", "handles errors").
3. **CONTEXT accuracy** — every file path in CONTEXT `files` exists (grep to confirm). No hallucinated paths.
4. **Cross-task consistency** — do function names, type names, and file paths used across tasks match? A function
   called `validateToken` in task 1 but `verifyToken` in task 3 is a bug.
5. **No placeholders** — search for `TBD`, `TODO`, `[NEEDS CLARIFICATION]`, `implement later`. All must be resolved.

If you find issues, fix them inline. No need to re-review — just fix and move on. If you find a requirement with no
task, add the task.

## Next

After self-review, **present the task files and execution plan to the user for review.** Do not dispatch subagents
until the user approves. The user may adjust task scope, reorder priorities, or request changes.

Once the user approves:

1. **Create the exploration log** — write `docs/tasks/{branch-slug}/exploration.md` with the header from
   `skills/ticket-review/templates/exploration.md`. This ensures it exists before any execute-task subagent starts.
2. **Create the execution TODO list** from the execution plan before dispatching any subagents.
   This is the concrete per-task tracker for the implementation phase:

TODO:
```markdown
- [ ] Implement task 001: <name> (execute-task subagent)
- [ ] Verify task 001 (verify-task subagent)
- [ ] Implement task 002: <name> (execute-task subagent)
- [ ] Verify task 002 (verify-task subagent)
  ...
- [ ] Run pr-review for full ticket (pr-review subagent)
- [ ] If pr-review approves: run wrap-up (promote exploration, verify docs)
```

For parallel groups, list all tasks in the group together. Mark each item as subagents complete. If verify-task
returns FAIL, add fix items inline before marking the original task done.

Then dispatch `execute-task` following the execution plan:

- **Parallel groups**: dispatch multiple `execute-task` subagents simultaneously. Each execute-task dispatches its own
  `verify-task` subagent (model: haiku, effort: medium) per execute-task's Process checklist.
- **Sequential groups**: wait for previous group's tasks to all pass `verify-task` subagent before starting.

Do not implement tasks in this session.
