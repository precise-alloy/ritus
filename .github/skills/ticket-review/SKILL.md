---
name: ticket-review
description: 'Analyze Jira tickets and produce an execution plan with detailed task lists. USE FOR: breaking down Jira tickets into implementation tasks, identifying files to modify, planning unit tests, and updating documentation. DO NOT USE FOR: actually implementing the changes, creating PRs, or deploying code.'
argument-hint: 'Provide the Jira ticket URL(s) and any additional context'
---

# Ticket Review & Execution Planning

Analyze Jira tickets, understand requirements, inspect the codebase, and produce a detailed execution plan saved under
the project's ticket review docs path from `.ai/profiles/project.md` section `## Documentation layout` (e.g.
`<ticket-reviews-path>/<ticket-id>-review.md`).

## ⛔ MANDATORY: Remote API access

Load `.ai/profiles/runtime.md` section `## Remote API access` before any remote ticket or PR access. Use the configured
remote helper command and environment check from that section. Do not use ad-hoc HTTP calls, hand-rolled auth headers,
or unrelated MCP provider tools when the profile defines an approved helper.

If a needed call is missing from the configured helper, **stop and ask the user before falling back to anything else.**
Extending the helper is preferred over working around it.

## AI Workflow Integration

This skill operates as **ARCHITECT** role within the `.ai/` workflow.

### Before starting:

1. Read `.ai/AGENTS.md` — follow golden rules and pre-coding read order.
2. Load relevant profile sections: `.ai/profiles/project.md` sections `## Source layout`, `## Documentation layout`,
   `## Requirement source precedence`, and `## Test location conventions`; `.ai/profiles/team.md` sections
   `## Team config`, `## Branch conventions`, `## tasks/ path convention`, and `## Traceability policy`;
   `.ai/profiles/runtime.md` section `## Remote API access`.
3. **Always start from Step 1** (Gather Input) — ask the user for ticket URL(s) and context.
4. **After gathering input, always run Step 0** (Check Existing Work) — check for existing review/task files before
   proceeding to full analysis.
5. After producing or updating the review document, triage per `.ai/workflows/generate-tasks.md` and generate task files
   in `.ai/tasks/{branch-slug}/`.
6. When generating task files, check `.ai/tasks/` for existing files matching this ticket — do NOT create duplicates (update them instead).

### Triage output:

- **TRIVIAL/SIMPLE**: Review document only — no task file needed.
- **STANDARD**: Review document + full task file in `.ai/tasks/`.
- **EPIC**: Review document + full task file + `.ai/memory/{branch-slug}-{feature-slug}-context.md`.

### Documentation planning (mandatory):

When generating task files, always include a DOC UPDATE section that specifies:

1. Which documentation files need to be created or updated.
2. What content should be added/changed (with ticket ID for traceability).
3. Apply `.ai/profiles/team.md` section `## Traceability policy` when deciding whether ticket IDs belong in code
   comments, task files, review docs, or commit messages.

This ensures documentation stays current and future requirements can build on accurate information.

### QA mode (`task`):

- For STANDARD/EPIC: generate `{task-name}.qa.md` alongside each task file.
- QA doc should contain: affected features, test scenarios, regression areas from §4 of the review.

### Standards check:

- Load `.ai/standards/testing-policy.md` — ensure unit test plan in §3.7 matches required test types.
- Load `.ai/standards/security.md` — if ticket touches auth/billing/tenant isolation.
- Load `.ai/standards/definition-of-done.md` — DONE WHEN in task files must satisfy these gates.
- Load `.ai/standards/stakeholders.md` — know who to escalate questions to and who can confirm decisions.

## Prerequisite

Read `.ai/profiles/runtime.md` section `## Remote API access` and run the configured environment check command before
fetching remote data. If required credentials are missing, empty, invalid, expired, revoked, or unauthorized, stop and
ask the user to fix access before continuing.

## Step 0: Check Existing Work

After gathering ticket URL(s) in Step 1, **always** check for existing review and task files before proceeding:

1. Check if `docs/src/tickets/<TICKET_ID>-review.md` exists.
2. Check if `.ai/tasks/` contains any task files matching this ticket ID.
3. Check if `.ai/memory/` contains any context files matching this ticket ID.

### If existing files are found → Incremental Update

When a review file already exists, perform an incremental update instead of a full re-review:

1. Read the existing review file and note the `Last Reviewed` datetime (UTC).
2. Fetch the ticket's change history (changelog) since that datetime using the configured helper from
   `.ai/profiles/runtime.md` section `## Remote API access`.
3. Fetch comments via the configured helper and check for any added or updated after the last review date.
4. If there are **no changes** since last review — inform the user that the review is up-to-date and ask if they want a
   full re-review anyway.
5. If there **are changes**, identify:
    - **Description updates** — requirements may have changed.
    - **New comments** — may contain answers to open questions, confirmation of assumptions, or additional context.
    - **Status changes** — ticket may have moved to a different state.
    - **Acceptance criteria updates** — scope may have shifted.
6. Reflect all relevant changes into the review document and associated task files:
    - Move answered questions from "Open Questions" to "Decisions".
    - Update assumptions that have been confirmed or invalidated.
    - Adjust task lists if scope changed.
    - Update the `Last Reviewed` datetime to the current UTC time.
7. Present a **diff summary** to the user showing what changed in the review.

If the changelog or comment fetch fails because the Jira PAT is invalid, expired, revoked, or lacks access, stop and ask
the user to provide a valid Jira PAT before continuing the incremental update.

### If no existing files are found → Full Review

Proceed to Step 2 (Analyze Requirements & Codebase) and perform the full review workflow.

## Step 1: Gather Input

Ask the user for:

1. The ticket URL(s) or key(s) matching `.ai/profiles/team.md` section `## Team config` ticket format.
2. Any additional information or context that is not captured in the ticket (e.g., verbal decisions, Slack discussions,
   architectural constraints, priority notes)

## Step 2: Analyze Requirements & Codebase

### 2.1 Fetch Jira Ticket(s)

Fetch ticket details and comments only via the configured helper in `.ai/profiles/runtime.md` section
`## Remote API access`. Live ticket data is required before producing the review document or execution plan.

Parse ticket keys according to `.ai/profiles/team.md` section `## Team config` ticket format.

Fetch each ticket:

```bash
bun run .github/scripts/remote-api.ts jira issue "<TICKET_KEY_OR_URL>" "summary,description,status,issuetype,comment,acceptance_criteria"
```

Fetch all comments separately:

Use the configured helper command for comments.

If either Jira request returns `401` or `403`, or returns `404` with
`Issue does not exist or you do not have permission to see it`, stop and ask the user to verify Jira access before
continuing. Do not continue planning with stale or partial ticket data.

If the ticket references a remote PR or branch that affects implementation planning, fetch that PR via the configured
helper before finalizing the plan. If the remote call fails due to invalid, expired, revoked, or insufficient
credentials, ask the user to fix access before continuing.

Apply `.ai/profiles/project.md` section `## Requirement source precedence`.

### 2.2 Identify Requirements

From the ticket description and comments, extract:

1. **Acceptance criteria** — what must be true for the ticket to be considered done.
2. **Expected behavior** — how the feature/fix should work.
3. **Test data** — any specific values, scenarios, or edge cases mentioned.
4. **Constraints** — performance, security, compatibility notes.

### 2.3 Analyze Related Code

Based on the requirements, search the codebase to identify:

- **Existing code** that implements related functionality.
- **Entry points** (controllers, API endpoints, blocks, pages) affected.
- **Services and helpers** that will need changes.
- **Models and DTOs** that may need updates.
- **Configuration** files or constants involved.

Use semantic search, grep, and file exploration across the source layout defined in `.ai/profiles/project.md` section
`## Source layout`.

### 2.4 Check for UI Changes

If the ticket involves UI updates (new components, layout changes, styling, frontend behavior):

1. Inspect frontend/UI paths from `.ai/profiles/project.md` section `## Source layout`.
2. Skip generated artifact paths listed in `.ai/profiles/project.md` section `## Source layout`.

### 2.5 Review Existing Documentation

Check documentation paths listed in `.ai/profiles/project.md` section `## Documentation layout` for existing
documentation related to the feature area.

Note which docs are relevant and whether they need updating or if new documentation should be created.

### 2.6 Ask Clarifying Questions

If anything is unclear, ambiguous, or needs confirmation:

- **Ask the user clearly and specifically.** Do not make assumptions.
- Refer to `.ai/standards/stakeholders.md` to identify who should answer each question.
- The user may answer directly, or may need to escalate to the appropriate stakeholder.
- Frame questions so they can be forwarded to non-technical stakeholders if needed.
- Clearly distinguish between questions that block implementation vs. questions that are nice-to-have clarifications.

### 2.7 Raise Concerns

Proactively raise any concerns related to:

- **Security** — authentication, authorization, input validation, data exposure, injection risks.
- **Compliance** — GDPR, data retention, PII handling, audit logging.
- **Performance** — N+1 queries, large payloads, missing caching, scalability.
- **Breaking changes** — API contract changes, backward compatibility.
- **Data integrity** — race conditions, partial updates, migration risks.

These must be clearly documented in the output so they can be reviewed before implementation begins.

## Step 3: Create Review Document

Create the file `<ticket-reviews-path>/<TICKET_ID>-review.md` (per `.ai/profiles/project.md` →
`## Documentation layout`, e.g. `<ticket-reviews-path>/PROJ-123-review.md`) with the following structure:

````markdown
# <TICKET_ID>: <Ticket Summary>

> Last Reviewed: <YYYY-MM-DD HH:mm UTC>  
> Status: <ticket status>  
> Type: <issue type>

## 1. Questions, Assumptions & Decisions

### Open Questions (Needs Answer)

Items below may need product owner confirmation before the dev team can provide estimation.

- [ ] <Clear question that needs PO/stakeholder answer>
- [ ] <Another question>

### Assumptions

- <Assumption made and reasoning>

### Decisions

- <Decision made based on ticket comments or user input>

## 2. Proposed Implementation

### Approach

<Brief description of the overall technical approach and rationale.>

### Solution Details

<Detailed explanation of how the implementation will work, including:>

- Architecture decisions
- Data flow (use Mermaid diagrams when visual representation aids understanding)
- Integration points
- Error handling strategy

### Diagrams (if applicable)

When the implementation involves complex flows, component interactions, or state transitions, include Mermaid diagrams
to visualize them. Use ```mermaid fenced code blocks.

Examples of when to include diagrams:

- Sequence diagrams for multi-step API/service interactions
- Flowcharts for complex decision logic
- State diagrams for status/workflow transitions
- Class diagrams for new model relationships

## 3. Detailed Task List

### 3.1 Models & Configuration

| #   | File Path         | Action          | Description                  |
| --- | ----------------- | --------------- | ---------------------------- |
| 1   | `path/to/file.cs` | Modify / Create | What needs to change and why |

### 3.2 Services & Business Logic

| #   | File Path | Action | Description |
| --- | --------- | ------ | ----------- |

### 3.3 Integration

| #   | File Path | Action | Description |
| --- | --------- | ------ | ----------- |

### 3.4 Controllers & Endpoints

| #   | File Path | Action | Description |
| --- | --------- | ------ | ----------- |

### 3.5 UI & Frontend

| #   | File Path | Action | Description |
| --- | --------- | ------ | ----------- |

### 3.6 Wiring & DI

| #   | File Path | Action | Description |
| --- | --------- | ------ | ----------- |

### 3.7 Unit Tests

| #   | Test File Path                   | Tests to Add                         | Covers            |
| --- | -------------------------------- | ------------------------------------ | ----------------- |
| 1   | `Project.Tests/path/TestFile.cs` | `MethodName_Scenario_ExpectedResult` | Brief description |

Test file location convention: see `.ai/profiles/project.md` section `## Test location conventions`.

### 3.8 Documentation

| #   | Doc File Path          | Action          | Description      |
| --- | ---------------------- | --------------- | ---------------- |
| 1   | `docs/feature-name.md` | Create / Update | What to document |

Guidelines:

- Existing docs are intentionally brief — **expand them** with implementation details, usage examples, and architecture
  notes when touching related features.
- Create new docs for entirely new features or workflows.
- Include: purpose, how it works, configuration, edge cases, and troubleshooting tips.

## 4. QA Verification Notes

### Test Scenarios

| #   | Scenario        | Steps                       | Expected Result      |
| --- | --------------- | --------------------------- | -------------------- |
| 1   | <Scenario name> | <Steps to reproduce/verify> | <What QA should see> |

### Edge Cases to Verify

- <Edge case 1>
- <Edge case 2>

### Regression Areas

- <Area that might be affected and should be regression-tested>

### Test Data Requirements

- <Any specific data setup needed for QA>

## 5. Risks & Concerns

### Security

- <Security concern if any, or "None identified">

### Compliance

- <Compliance concern if any, or "None identified">

### Performance

- <Performance concern if any, or "None identified">

### Breaking Changes

- <Breaking change risk if any, or "None identified">
````

## Step 4: Generate Task Files (AI Workflow)

After the review document is saved, generate task files per the `.ai/workflows/generate-tasks.md` format:

1. **Triage** the ticket using blast radius, contract impact, and validation clarity.
2. **Create branch slug** from the planned branch name using `.ai/profiles/team.md` sections `## Branch conventions` and
   `## tasks/ path convention`.
3. **Write task file(s)** to `.ai/tasks/{branch-slug}/{NNN-name}.md` using the STANDARD/EPIC template.
4. **Write QA file(s)** to `.ai/tasks/{branch-slug}/{NNN-name}.qa.md` (QA mode is `task`).
5. **For EPIC**: create `.ai/memory/{branch-slug}-{feature-slug}-context.md` with decisions and progress.

### Task file DONE WHEN must include:

- All acceptance criteria from ticket
- `[ ] Compiles without errors`
- `[ ] Unit tests pass (per testing-policy.md)`
- `[ ] No files outside CONTEXT modified`
- `[ ] No claim made about existing code without citing file:line`

### Present execution plan:

After generating task files, output a summary:

- Triage level
- Task file paths created
- Suggested execution order
- Which executor capability to use, based on `.ai/profiles/runtime.md` section `## AI tools in use`.

## Notes

- The `Last Reviewed` datetime (UTC, format `YYYY-MM-DD HH:mm UTC`) is **mandatory** in every review file. It enables
  efficient re-reviews by scoping changelog/comment checks to only what changed since last review — even multiple
  re-reviews on the same day.
- On re-review, always check ticket change history and comments for: answers to previously open questions,
  confirmation/rejection of assumptions, scope changes, and new context. Update the review and task files accordingly.
- If anything is unclear about the requirements, **ask the user** — do not make assumptions. The user can escalate to
  the product owner for confirmation.
- When the ticket is large, suggest splitting into smaller sub-tasks if appropriate.
- Pay attention to integration-specific field names and status strings listed in `.ai/profiles/project.md` sections
  `## Source layout` and `## Project-specific constraints` — typos can cause silent failures.
- Consider backward compatibility when modifying shared models or APIs.
- The review document should be actionable enough that another developer (or the `unit-tests` skill) can follow it
  without re-reading the ticket.
- Security and compliance concerns must always be raised explicitly — never silently ignore them.
- Reference test style examples listed in `.ai/profiles/project.md` section `## Test location conventions`.
