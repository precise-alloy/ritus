---
name: verify-task
description: Verifies DONE WHEN conditions independently in a fresh reviewer context, separate from the implementer. Spawned fresh per `skills/shared/dispatch.md` - not run inline.
argument-hint: Provide the task file path, changed files, implementation summary, and validation evidence
---

# Verify Task

**Core principle:** Never trust the implementer - verify from the diff and command output only. A clean context
prevents bias; that's why this runs in a fresh subagent.

## When to use

After each task is implemented by `execute-task`.

When starting verify-task, create this TODO - **every item below, verbatim** (never a single item named after the skill) - and mark items done as you complete them:

TODO:

```markdown
- [ ] Phase 1: DONE WHEN verification (conditions + scope + standards + build/test/lint)
- [ ] Phase 2: Adversarial review (fault injection, contracts, regression, security)
- [ ] Report verdict (PASS/FAIL with evidence)
```

## Operating constraints

- Read-only except build/test/lint commands.
- Never fix issues - report findings only.
- Never trust implementer claims - verify from the diff and command output only.
- Report BLOCKED if inputs are missing.

## Hard gate

**You must be a fresh reviewer that did not implement the change under review.** If you implemented it, you are
disqualified - verification must run in a clean context to prevent bias. (The orchestrator guarantees this by
spawning verify-task as a fresh subagent; this gate is the safety net.)

On FAIL, report the gaps and stop - verify-task never fixes issues and never re-runs itself.

## Inputs

1. Task file path (e.g., `docs/tasks/feat-auth/001-add-login.md`)
2. The implementer's report (files-changed list + summary) - a hint for where to look, not ground truth.
3. `docs/tasks/{branch-slug}/exploration.md` if it exists - prior findings and flagged risks from the analysis and
   implementation subagents. Treat it like the implementer's report: a map of where to look and what was already
   flagged, **not** ground truth. Use it to aim your adversarial review (a `[LESSONS]` or security note is a lead to
   probe harder), but confirm every DONE WHEN condition and Phase 2 check from the diff and command output - an
   "already investigated" note is never a substitute for verifying it yourself.

## Establishing the change surface

The implementer leaves work **uncommitted and unstaged** in the working tree - never diff against a base branch
or the index (`--cached`), both of which would show nothing or stale content. Derive the change surface from the
working tree, cheapest-first, to keep token cost bounded:

1. **File list + churn (always, tiny):** run `git status --short` and `git diff --stat HEAD`. The `git status
   --short` output is the ground truth for the scope check and catches files the implementer's report omitted.
   Untracked new files appear only here - read them directly, since `git diff HEAD` does not include them.
2. **Content (scoped, on demand):** pull `git diff HEAD -- <file>` only for files tied to a DONE WHEN condition or
   flagged during adversarial review. Fetch the full `git diff HEAD` only when total churn (from `--stat`) is small
   enough to be cheap. Never load a large unified diff wholesale.

## Phase 1: DONE WHEN Verification

1. **Read the task file** - extract DONE WHEN conditions, CONTEXT files, DOC UPDATE section. (A debug fix arrives as
   the investigation case file: its `Regression Test` is the DONE WHEN and its `Proposed Fix` is the STEPS.)

2. **Check every DONE WHEN condition:**
   - **Diff-checkable** conditions (file exists, field added, logic changed): verify from the scoped working-tree
     diff (see *Establishing the change surface*), cite `file:line`.
   - **Command-checkable** conditions (compiles, tests pass, no lint errors): verify by running commands in step 5.
   - If a condition cannot be verified by either method, mark it FAIL with explanation.

3. **Scope check** - compare the `git status --short` file list (not the implementer's report) against the allowed scope:
   - For STANDARD/EPIC tasks: allowed scope = source files listed in CONTEXT `files` + files listed in DOC UPDATE
     + test files co-located with or covering changed source files. CONTEXT `docs` entries are read-only
     references - modifications to them are scope violations. Flag modifications outside this scope as violations.
   - For SIMPLE tasks (no CONTEXT section): check that changes are limited to what the TASK description implies.
   - `docs/tasks/{branch-slug}/exploration.md` (append-only) is always allowed regardless of task type.

4. **Standards gates - load and check applicable standard skills:**

   <!-- Keep in sync with execute-task/SKILL.md -->

   | Task touches | Load skill |
   |---|---|
   | Any code change | `code-conventions` |
   | New service / endpoint / worker / bug fix | `testing-policy` |
   | New business logic, new API endpoint, or bug fix | `tdd` (verify tests exist and cover the new/changed behavior) |
   | Auth / billing / migration / tenant isolation / infra config / shared contracts | `security` |
   | Any STANDARD or EPIC task | `definition-of-done` |

   Run each loaded standard's checklist against the diff.

5. **Run verification commands:**
   - Build: run the build command from `docs/PROJECT_CONTEXT.md` → must pass
   - Test: run the test command from `docs/PROJECT_CONTEXT.md` → must pass
   - Lint: run the lint command from `docs/PROJECT_CONTEXT.md` → must pass

   If any command is not configured in `docs/PROJECT_CONTEXT.md` (empty, placeholder, or `N/A`), skip it with a
   warning in the output - do not hard-fail on missing build/test/lint configuration.

6. **QA file check:** if QA mode is active in `docs/PROJECT_CONTEXT.md`, verify QA file per
   `qa-files.md` template rules.

## Phase 2: Adversarial Review (per-task)

After DONE WHEN passes, apply these adversarial checks against the diff. This is a lighter version focused on the
single task's changes, not the full ticket-level review (which is `pr-review`'s job).

### 2.1 Fault Injection (mental fuzzing)

For every changed method or code path, ask:

- **Null / empty inputs**: What happens if any parameter, collection, or config value is null, empty, or whitespace?
- **Boundary values**: What about zero, negative, max-int, empty arrays, single-element lists?
- **External failures**: What if an API call, DB query, or file read throws? Is there a silent swallow?

### 2.2 Implicit Contract Changes

- Did the change alter a return type, add a nullable field, or change method signatures?
- Are there callers that weren't updated?
- Did removed or renamed symbols leave dead references?

### 2.3 Regression Risk

- Does the change touch shared code paths used by other features?
- Could the change break existing tests not in the task's scope?
- Are there integration points that depend on the old behavior?

### 2.4 Security Quick Check

Only if the task touches auth, data handling, or user input:

- Can user-controlled input reach SQL, HTML, or command execution without sanitization?
- Does the change accidentally expose data to unauthorized users?
- Do error messages leak internals?

## Output

### PASS

```text
VERIFY: PASS

Phase 1 - DONE WHEN:
- [ ] DONE WHEN condition 1 - verified at file:line (diff-checkable)
- [ ] DONE WHEN condition 2 - verified by command output (command-checkable)
- [ ] Scope clean - STANDARD/EPIC: only CONTEXT + DOC UPDATE + test files (+ exploration.md); SIMPLE: only files implied by TASK + tests (+ exploration.md)
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

## Hard rules

- Never PASS without running all configured build, test, and lint commands and confirming exit code 0.
- Never PASS based on the implementer's claims - verify from the diff and command output.
- Report evidence for every PASS condition - "looks correct" is not evidence.
- Phase 2 findings are FAIL conditions - they must be fixed before PASS.

## Handoff

- **Report:** your verdict - `VERIFY: PASS` or `VERIFY: FAIL` with gaps.
- **TODO update:** PASS → none. FAIL → `Fix - dispatch execute-task subagent`, then
  `Re-verify - dispatch verify-task subagent`.
