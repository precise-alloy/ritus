---
name: verify-task
description: Verifies DONE WHEN conditions independently in a fresh reviewer context, separate from the implementer. Spawned fresh per `skills/shared/dispatch.md` - not run inline.
argument-hint: Provide the task file path, changed files, implementation summary, and validation evidence
---

# Verify Task

Verify the task contract independently from the current repository and your own command evidence.

## Preconditions and inputs

- Work in a fresh reviewer context separate from implementation, read-only except build/test/lint commands.
  Report BLOCKED if reviewer independence or required inputs are missing.
- Required inputs: task-file path and implementation report. Read the branch's exploration log when present.
- Treat the report and exploration notes as leads; establish every conclusion from the repository and command
  output. Return failures for correction with the evidence and gaps.

## Process

Create this TODO verbatim and mark each item done as it completes:

TODO:

```markdown
- [ ] Phase 1: DONE WHEN verification (conditions + scope + standards + build/test/lint)
- [ ] Phase 2: Adversarial review (fault injection, contracts, regression, security)
- [ ] Report verdict (PASS/FAIL with evidence)
```

## Establishing the change surface

Use `git status --short` and `git diff --stat HEAD` to establish the complete working-tree change list, including
files omitted from the implementation report. Read untracked files directly. Inspect `git diff HEAD -- <file>`
for acceptance conditions and review leads; use the full diff only when its total churn is small.

## Phase 1: DONE WHEN Verification

- Read DONE WHEN, VERIFY, and all available scope/contract sections. For investigation files, `Regression Test`
  supplies DONE WHEN and `Proposed Fix` supplies STEPS.
- Prove every DONE WHEN condition with `file:line` evidence or the required command result. Mark an unprovable
  condition FAIL with its gap.

### Scope and constraints

Compare the full status list against the task:

- STANDARD/EPIC permits CONTEXT `files`, DOC UPDATE paths, and co-located or covering tests. CONTEXT `docs` are
  read-only references.
- SIMPLE permits the changes implied by TASK and their tests.
- The branch's `docs/tasks/{branch-slug}/exploration.md` permits append-only findings.

Flag every out-of-scope change, NON-GOALS implementation, or unsatisfied CONSTRAINTS line.

### Standards

Load each applicable standard and apply its checklist to the diff:

<!-- Keep in sync with execute-task/SKILL.md -->

| Task touches | Load skill |
|---|---|
| Any code change | `code-conventions` |
| New service / endpoint / worker / bug fix | `testing-policy` |
| New business logic, new API endpoint, or bug fix | `tdd` (verify tests exist and cover the new/changed behavior) |
| Auth / billing / migration / tenant isolation / infra config / shared contracts | `security` |
| Any STANDARD or EPIC task | `definition-of-done` |

### Commands and QA

- Run configured build/test/lint from `docs/PROJECT_CONTEXT.md`, then task `VERIFY` commands in order. Require
  project exit 0 and every task-specific expected output/status; a mismatch is FAIL.
- Reuse results you produced in this run only for identical commands with confirmed matching working directory,
  environment, and unchanged state. Apply every condition's expectations to reused evidence.
- Execute explicit repeats and stateful sequences; rerun when equivalence is uncertain.
- Report unconfigured project commands (empty, placeholder, `N/A`) as skipped with a warning.
- When QA mode is active, verify the QA file against `skills/task-generation/templates/qa-files.md`.

## Phase 2: Adversarial Review (per-task)

After Phase 1 passes, examine the task's changed paths. Every Phase 2 finding makes the verdict FAIL.

### 2.1 Fault Injection (mental fuzzing)

Probe each changed method/path with null, empty, and whitespace inputs; zero, negative, maximum, and collection
boundaries; and failed API, database, or file operations. Identify incorrect results and swallowed failures.

### 2.2 Implicit Contract Changes

Trace changed return types, nullability, signatures, and removed/renamed symbols through their callers. Flag broken
callers and dead references. Confirm INTERFACES `Produces` names, parameters, and return types in the resulting
API/tree, including pre-existing or generated signatures; confirm `Consumes` is used as specified.

### 2.3 Regression Risk

Inspect shared paths, existing tests beyond the task's scope, and integration points that depend on prior behavior.

### 2.4 Security Quick Check

For auth, data handling, or user-input changes, examine trust boundaries for injection, unauthorized access,
and leaked internals in errors.

## Output

Return PASS only with evidence for every condition, applicable standard, configured command, and adversarial check.
Return FAIL with gaps when an obligation fails, then hand off for correction.

### PASS

```text
VERIFY: PASS

Phase 1 - DONE WHEN:
- [ ] DONE WHEN condition 1 - verified at file:line (diff-checkable)
- [ ] DONE WHEN condition 2 - verified by command output (command-checkable)
- [ ] Scope clean - STANDARD/EPIC: only CONTEXT + DOC UPDATE + test files (+ exploration.md); SIMPLE: only files implied by TASK + tests (+ exploration.md)
- [ ] Contract clean - CONSTRAINTS satisfied, nothing under NON-GOALS touched, INTERFACES `Produces` present
- [ ] Standards gates - all applicable gates passed
- [ ] Build passes - exit code 0 (or skipped - not configured)
- [ ] Tests pass - N tests, 0 failures (or skipped - not configured)
- [ ] Lint passes - 0 errors (or skipped - not configured)

Phase 2 - Adversarial:
- [ ] Fault injection - no unhandled null/empty/boundary cases found
- [ ] Contract changes - no broken callers
- [ ] Regression risk - no shared paths affected without tests
- [ ] Security - N/A or no issues found
```

### FAIL

```text
VERIFY: FAIL

Phase 1 gaps:
- DONE WHEN condition N - NOT MET: <explanation>
- Scope violation - <file> modified but not in CONTEXT + DOC UPDATE + test files
- Standards gate - <specific gate> failed: <details>
- Build/test/lint - <which> failed: <error>

Phase 2 findings:
- Fault injection - <what breaks with null/empty input at file:line>
- Contract change - <caller at file:line not updated>
- Regression risk - <shared path at file:line affected>
- Security - <issue at file:line>
```

## Handoff

- **Report:** your verdict - `VERIFY: PASS` or `VERIFY: FAIL` with gaps.
- **TODO update:** PASS → none. FAIL → `Fix - dispatch execute-task subagent`, then
  `Re-verify - dispatch verify-task subagent`.
