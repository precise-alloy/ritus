---
name: ticket-review
description: Use after triage to produce task files - analyzes requirements from a plain description or a Jira, Azure DevOps, or GitHub Issues ticket, and generates execution plans.
argument-hint: Provide a requirement description or ticket URL(s)/key(s) (Jira, Azure DevOps, or GitHub Issues) with any additional context
---

# Ticket Review

Turn a triaged requirement into task files and an execution plan. Obtain separate user approvals for the requirement
review and the generated tasks.

## Process

Create this TODO verbatim and mark each item done as it completes:

TODO:

```markdown
- [ ] Gather input (requirement source + context)
- [ ] Obtain requirement analysis - STANDARD/EPIC: worker result; SIMPLE: inline
- [ ] Review document ready (confirm/finalize) + user review gate
- [ ] Completeness gate
- [ ] Prepare task files - SIMPLE: inline; STANDARD/EPIC: worker result
- [ ] Obtain task-file approval and hand off the execution plan
```

## Step 1: Gather Input

Obtain the plain requirement or ticket URL/key and any additional decisions, constraints, or priority notes.
Capture the ticket reference at intake; its live content belongs to the analysis result.

Use the triage classification. Ticket references start at STANDARD; work touching auth, billing, migrations, tenant
isolation, infra, or shared contracts requires at least STANDARD.

Derive the branch slug from the current branch by replacing `/` with `-`. Use the ticket ID as the search key when
available, otherwise the branch slug.

## Step 2: Analyze the requirement

- **STANDARD / EPIC:** obtain the review-document path, findings, open markers, concerns, and any incremental result
  through the analysis handoff below.
- **Plain-text SIMPLE:** extract acceptance criteria and affected files/entry points inline, citing `file:line`.
  Keep exploration focused on the affected area; this inline analysis serves as the review.

Present returned diff summaries. For `up-to-date: yes`, ask whether the user wants a full re-review. Apply a
recommended classification upgrade before generation. Relay blockers and specific clarification questions to the user.

## Step 3: Review Document & User Review Gate

For STANDARD/EPIC, confirm the returned document against `templates/review-document.md`, including `Last Reviewed`
in UTC. Resolve gaps that would misdirect generation: missing sections, contradictions, material ambiguities, or scope
requiring decomposition. Judge readiness by decision completeness rather than prose polish.

Present the document, or SIMPLE inline analysis, for explicit approval of questions, assumptions, approach, scope,
and security, compliance, or architectural concerns. Incorporate feedback through re-analysis and present it again.

## Step 4: Completeness Gate

Proceed to generation only when every condition holds:

- [ ] User has approved the review document (Step 3)
- [ ] Every `[NEEDS CLARIFICATION]` marker is resolved
- [ ] Each acceptance criterion is verifiable by diff or command with a measurable expected outcome
- [ ] Each requirement covers edge cases, including empty input, missing data, and concurrent access
- [ ] Scope boundaries and exclusions are explicit
- [ ] Security implications are documented for auth/billing/tenant changes

Resolve unmet conditions with the user before continuing.

## Step 5: Generate Task Files

- **Plain-text SIMPLE:** write one task inline using the SIMPLE template in
  `skills/task-generation/templates/task-files.md`: TASK, DONE WHEN, VERIFY.
- **STANDARD / EPIC:** obtain task paths, execution plan, coverage summary, and applicable QA/memory paths through
  the generation handoff below.

Keep one task per logical change, under `docs/tasks/{branch-slug}/` using `docs/PROJECT_CONTEXT.md` naming conventions.
Limit task-file writes to the current branch's directory.

## Handoff

Use `skills/shared/dispatch.md` for worker invocations at the matching process step:

- **Analysis:** dispatch `requirement-analysis` for STANDARD/EPIC with the requirement source, additional context,
  branch slug, and search key. Route review feedback back to it; revise SIMPLE analysis inline.
- **Generation:** after review approval and completeness, dispatch `task-generation` with the approved review path,
  exploration-log path, branch slug, classification, and QA mode from `docs/PROJECT_CONTEXT.md` (off when absent).
- **Report:** the task files + execution plan.
- **Task approval:** present the task files and plan in chat and wait for explicit user approval. Incorporate requested
  scope or ordering changes before implementation.

### Dispatch execution

After task approval, ensure `docs/tasks/{branch-slug}/exploration.md` exists; create a missing log using
`templates/exploration.md`. Generate the driving TODO from the approved plan:

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

- **TODO update:** execute the driving TODO through the shared dispatch contract, preserving the approved groups,
  independent workers, outcome handling, and bounded fix loop. Continue to wrap-up after pr-review approves.
