---
name: definition-of-done
description: Loaded automatically by execute-task and verify-task for STANDARD and EPIC tasks - hard gates and per-change-type completion checklists. Do not invoke standalone
argument-hint: Provide the task or ticket identifier, changed files, and validation evidence
user-invocable: false
---

# Definition of Done

## When to use

Load this skill for all STANDARD and EPIC tasks. All hard gates must pass before reporting done. Per-change-type
checklists are additive - check all that apply to the current task.

## Hard gates - apply to all changes

- [ ] Project compiles with zero errors
- [ ] Lint passes with zero errors (warnings flagged, non-blocking)
- [ ] No new untyped values without inline comment explaining why (typed languages)
- [ ] No secrets, API keys, or credentials in changed files
- [ ] Scope clean: no files modified outside the task's stated CONTEXT

## Per change type

### New service method

- [ ] At least one unit test: happy path
- [ ] At least one unit test: primary failure path
- [ ] Error handling follows `code-conventions` skill pattern (no naked throws, no swallowed errors)

### New API endpoint

- [ ] Auth guard tested: 401 without valid token
- [ ] Tenant/ownership scoping tested: 403 for wrong entity
- [ ] Input validation present for required fields
- [ ] Structured error response returned to client (not stack trace)

### New background worker / job

- [ ] Dispatch logic tested
- [ ] Error logged on failure (job ID + error + stack)
- [ ] Retry behavior tested if applicable

### Database migration

- [ ] Migration file exists and runs cleanly
- [ ] Data integrity verified: row counts and schema shape spot-checked
- [ ] Irreversibility documented if migration cannot be rolled back
- [ ] Queries in migration use parameterized inputs

### Shared type / contract change

- [ ] All importing modules compile after the change
- [ ] Contract test passes (or documented why N/A with justification)

### UI change

- [ ] Component renders without errors (check for runtime warnings in console output)
- [ ] Responsive breakpoints handled in code (verify CSS/class logic covers mobile + desktop)
- [ ] Accessibility attributes present: `aria-label`, `alt`, `role` where applicable
- [ ] Form inputs have associated labels (no unlabeled inputs)
- [ ] Loading, error, and empty states handled (not just the happy path)
- [ ] No hardcoded pixel values where relative units are expected (rem/em/% vs px)
- [ ] Browser verification required - add to DONE WHEN: `Verified in browser at 375px and 1280px (human)`

### Safety override changes (auth, billing, migrations, tenant isolation, infra config, shared contracts)

- [ ] Full security checklist in `security` skill completed
- [ ] Audit log entry created for any state changes
- [ ] Classified STANDARD or above - no TRIVIAL/SIMPLE

## Soft gates - flag but non-blocking

- Lint warning count > 5 new: note in commit message
- Test omitted for specific edge case: document reason in DONE WHEN
- Browser verification deferred: document reason - must be logic-only or config-only

## Quality thresholds (apply to new or substantially rewritten code only)

- No single function with cyclomatic complexity > 10 without a comment (count independent branching paths: if/else, switch cases, loops, logical operators, ternaries, catch blocks)
- No function > 60 lines without structural justification
- No file > 400 lines - split at module boundary

Pre-existing violations in unchanged code are not your problem - flag them as tech debt if noticed, but do not
refactor outside the task's scope.

## Completion signal

Report done only after:

1. All applicable hard gates above checked
2. All DONE WHEN items in task file verified
3. DOC UPDATE completed per doc trigger matrix in `ticket-review` skill
4. Output block in execute-task format produced

## Handoff

- **Report:** the standard applied to the parent skill's work.

