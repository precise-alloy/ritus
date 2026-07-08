---
name: pr-review
description: Use when reviewing code diffs, pull requests, or completed implementation — adversarial review of code quality and correctness. TRIGGER — invoke when user says "review my code", "review this PR", "code review", "check my changes", or all tasks are verified. Do NOT use for analyzing requirements or generating tasks — that is ticket-review
argument-hint: Provide either the Azure DevOps/GitHub PR URL or describe the local branch/worktree to review, plus relevant ticket URL(s)
---

# PR Review

**Core principle:** The burden of proof is on the code, not the reviewer. Default to "Request changes" unless you
can prove correctness with evidence at `file:line`.

## Subagent dispatch instructions

When the orchestrating session needs to run pr-review, dispatch a fresh subagent with:
- **Model:** sonnet
- **Effort:** high
- **Tools:** Read, Grep, Glob, Bash, WebFetch
- **Constraints:** adversarial reviewer in fresh context; never apply fixes or modify source files; never create or
  modify environment files (.env, .env.local) — report missing setup to the user; use `git fetch origin` and
  `origin/<branch>` refs — never mutate local branches; default to "Request changes" — the burden of proof is on the
  code, not the reviewer; report BLOCKED if inputs missing.

Inputs to provide:
1. Review mode: local diff/worktree or remote PR URL
2. Requirement source: ticket URL/key or plain description
3. Base branch if it differs from project defaults

## When to use

After all tasks for a ticket are complete, or before opening a PR. This skill runs a full adversarial review of
cumulative changes.

When starting pr-review, create this TODO and mark items as you complete them:

TODO:

```markdown
- [ ] Load context and gather input
- [ ] Adversarial review (Phases 1-5)
- [ ] Report findings and state verdict
- [ ] Follow verdict path (Approve → invoke wrap-up / Request Changes → report to orchestrating session)
```

## Remote API access

Read `remote-api-access.md` in the `shared` skill directory for full remote API instructions — helper commands, URL parsing,
environment setup, and error handling.

## Before starting

1. Load relevant profile sections: `docs/PROJECT_CONTEXT.md` sections `## Requirement source precedence`,
   `## Testing`, and integration-specific entries from `## Source layout`; `docs/PROJECT_CONTEXT.md`
   section `## Team conventions`.
2. **Always start from Step 1** (Gather Input) — ask the user whether this is a PR review or a local pre-PR review, then
   gather the relevant URLs/context. Never silently load existing review/task files or resume previous sessions.
3. After gathering input, load `definition-of-done` skill — verify all hard gates pass.
4. Grep `docs/LESSONS.md` for the affected module/file names — flag if known failure patterns are being repeated.
5. Read `docs/STAKEHOLDERS.md` — know who authored/owns what and who to escalate questions to.
6. Read `docs/tasks/{branch-slug}/exploration.md` if it exists — findings from implementation subagents.
7. Check `docs/tasks/` for task files matching the reviewed branch — verify DONE WHEN conditions are met.

### Review checklist (in addition to §2.5 below)

- [ ] All DONE WHEN conditions in the task file are satisfied
- [ ] No claim about existing code without `file:line` citation
- [ ] Skill files updated if public interface changed (per skill maintenance rules in context)
- [ ] Load `testing-policy` skill — required test types present
- [ ] Load `security` skill — gates pass (if auth/billing/tenant touched)
- [ ] QA file verified per `qa-files.md` rules (if QA mode active)
- [ ] Adversarial pass completed — at least one fault-injection scenario attempted per changed method
- [ ] Every acceptance criterion mapped to a specific `file:line` or marked missing
- [ ] Blast radius analysis — all upstream callers of changed interfaces verified
- [ ] **Traceability policy followed** — verify ticket IDs and rationale appear where `docs/PROJECT_CONTEXT.md` section
  `## Team conventions` requires them.
- [ ] **Documentation up-to-date** — verify affected docs (skill files, docs/ARCHITECTURE.md, docs/DECISIONS.md, docs/LESSONS.md) were
  updated to reflect the PR changes. Flag stale or missing doc updates.

## Step 1: Gather Input

Ask the user for:

1. **Review mode**:
    - PR review: the Azure DevOps or GitHub pull request URL matching the configured remote system.
    - Local pre-PR review: the branch to review and whether the scope is committed branch diff, staged changes, unstaged
      changes, or the full worktree
2. **Requirement source** (one of):
    - Ticket URL(s) or key(s) matching `docs/PROJECT_CONTEXT.md` `## Team conventions` ticket format, OR
    - Plain description of what the changes should achieve (for work without a ticket)
3. Any additional information or context (e.g., verbal decisions, Slack discussions, architectural constraints)
4. The intended base branch if it differs from `docs/PROJECT_CONTEXT.md` section `## Team conventions`.

## Step 2: Review the Pull Request

Choose the review path based on the input mode.

### 2.1 Identify Review Target

#### PR review mode

Fetch remote PR details only via the configured helper in the `## Remote API access` section above.
Grounding the review in live PR metadata is required before reviewing code.

Parse the PR URL using the `## Remote API access` section. The provider is auto-detected from the URL:

```bash
bun run "<plugin-root>/scripts/remote-api.ts" pr "<PR_URL>"
```

This works with any configured provider (GitHub, Azure DevOps, or future providers). If auto-detection fails,
fall back to the explicit provider syntax: `bun run "<plugin-root>/scripts/remote-api.ts" <provider> pr "<PR_URL>"`.

If this helper returns `401` or `403`, or returns `404` with a permission-style message, stop and ask the user to verify
remote provider access before continuing. Do not continue the PR review until the remote PR fetch succeeds.

**Verify** the target branch matches `docs/PROJECT_CONTEXT.md` section `## Team conventions`. If not, warn the user.

#### Local pre-PR review mode

Determine the exact review scope before collecting the diff:

1. Confirm the base branch. Default to `docs/PROJECT_CONTEXT.md` section `## Team conventions` unless the user specifies
   another branch.
2. Determine whether you are reviewing:
    - the current branch against the base branch,
    - only staged changes,
    - only unstaged changes, or
    - the full worktree (staged + unstaged).
3. Capture the current branch name and worktree status:

```powershell
git branch --show-current
git status --short
```

If the user asks for a review of local uncommitted work, do not require a PR URL and do not block on Azure DevOps
metadata.

### 2.2 Fetch Remote Refs (read-only)

Fetch remote refs without mutating local branches. The reviewer must not modify local state.

```bash
git fetch origin
```

Use `origin/<baseBranch>` and `origin/<sourceBranch>` for all comparisons — never update local branch refs.

### 2.3 Get the Diff

Use the narrowest diff command that matches the requested review scope.

#### PR review mode

Use `git diff` with the three-dot notation against remote refs:

```bash
git diff origin/<baseBranch>...origin/<sourceBranch> --stat
git diff origin/<baseBranch>...origin/<sourceBranch>
```

Read the full context of changed files on the feature branch when needed:

```bash
git show origin/<sourceBranch>:<filePath>
```

#### Local committed branch review

Use `git diff` against the remote base branch and the current local branch:

```bash
git diff origin/<baseBranch>...HEAD --stat
git diff origin/<baseBranch>...HEAD
```

#### Local staged-only review

```powershell
git diff --cached --stat
git diff --cached
```

#### Local unstaged-only review

```powershell
git diff --stat
git diff
```

#### Local full-worktree review

Collect both staged and unstaged diffs. Review them together and call out which findings come from staged vs unstaged
changes if that distinction matters.

```powershell
git diff --cached --stat
git diff --cached
git diff --stat
git diff
```

When reviewing local changes, read the working tree version of changed files directly from disk rather than from
`git show`.

### 2.4 Fetch Requirements

**If ticket URL/key was provided:** fetch ticket details and comments via the configured helper in the
`## Remote API access` section above. Live ticket data is required before validating requirements.

**If plain description was provided:** use the description as the requirement source. Skip the ticket fetch below
and proceed directly to the adversarial review.

Parse ticket keys according to `docs/PROJECT_CONTEXT.md` section `## Team conventions` ticket format.

Fetch each ticket (the provider is auto-detected from the key/URL shape — works with Jira keys, GitHub Issue URLs,
and Azure DevOps work item URLs):

```bash
bun run "<plugin-root>/scripts/remote-api.ts" issue "<TICKET_KEY_OR_URL>" [fields]
```

For Jira, the `comment` field in the issue fetch may include comments inline. For ADO and GitHub, always fetch
comments separately using the commands below:

```bash
# For Jira tickets or ADO work items:
bun run "<plugin-root>/scripts/remote-api.ts" comments "<TICKET_KEY_OR_URL>"

# For GitHub Issues:
bun run "<plugin-root>/scripts/remote-api.ts" issue-comments "<ISSUE_URL>"
```

If auto-detection fails, fall back to the explicit provider syntax (e.g., `jira issue`, `github issue`, `ado issue`).

Apply `docs/PROJECT_CONTEXT.md` section `## Requirement source precedence`.

If a ticket request returns `401` or `403`, or returns `404` with a permission-style message, stop and ask the user
to verify access for the relevant provider before continuing. Do not continue the review with stale or partial
ticket data.

### 2.5 Adversarial Review

Adopt an **adversarial mindset**: your job is to break the code, not confirm it works. Assume every change contains at
least one latent defect and hunt for it.

#### Phase 1 — Requirement Mismatch Attack

1. Extract **acceptance criteria**, **test data**, and **expected behavior** using `docs/PROJECT_CONTEXT.md` section
   `## Requirement source precedence`.
2. For each criterion, attempt to construct a scenario where the code produces the wrong result or silently does
   nothing.
3. Look for requirements that are addressed in name only — where the code path exists but the behavior diverges from
   what the ticket actually specifies.

#### Phase 2 — Fault Injection (Mental Fuzzing)

For every changed method or code path, ask:

- **Null / empty inputs**: What happens if any parameter, collection, or config value is null, empty, or whitespace?
- **Boundary values**: What about zero, negative, max-int, empty arrays, single-element lists, strings at max length?
- **Concurrency**: Can two requests hit this path simultaneously and corrupt shared state?
- **Ordering**: Does this assume a specific call order that isn't enforced?
- **External failures**: What if an API call, DB query, or file read throws? Is there a silent swallow?

#### Phase 3 — Blast Radius Analysis

1. Trace every changed public interface upstream and downstream. Identify callers that were not updated.
2. Look for implicit contracts (e.g., a method that used to return non-null now can return null).
3. Check if removed or renamed symbols leave dead references in views, JSON contracts, or config.
4. Verify feature flags, DI registrations, and route registrations are consistent with the change.

#### Phase 4 — Security Adversarial Pass

- **Injection**: Can user-controlled input reach SQL, HTML, or command execution without sanitization?
- **AuthZ/AuthN**: Does the change accidentally expose data or actions to unauthorized users?
- **Information leakage**: Do error messages, logs, or API responses expose internals?
- **IDOR**: Can a user manipulate IDs to access another tenant's or user's data?

#### Phase 5 — Specification Completeness

- List every acceptance criterion and mark it ✅ proven-covered or ❌ not-covered/partially-covered.
- Flag any behavior that is implemented but has **no corresponding test** — treat untested logic as suspect.
- Identify any ticket requirement that is entirely missing from the diff.

### 2.6 Summarize Findings

Present the review as:

1. **Review Overview**: PR title/author/branch info when available, or local branch/worktree scope when reviewing pre-PR
   changes, plus files changed.
2. **Ticket Context**: Brief summary of what the ticket(s) require.
3. **Changes Summary**: What each file change does.
4. **Adversarial Findings**: For each finding, state:
    - The **attack vector** (how you tried to break it)
    - The **evidence** (file:line citation and reproduction scenario)
    - The **impact** (what goes wrong if this defect ships)
5. **Issues Table**: Categorized by severity:
    - **Critical/Bug**: Will cause runtime errors, data loss, or security breach.
    - **High**: Doesn't meet spec requirements, risks data corruption, or has no test coverage for critical logic.
    - **Medium**: Potential issues under specific conditions that should be clarified or defended.
    - **Low**: Code quality, minor improvements, defensive hardening.
    - **Info**: Observations, compiler warnings, style.
6. **Acceptance Criteria Checklist**: Every criterion marked ✅ or ❌ with file:line proof.
7. **Architectural Decisions**: If the review reveals design choices that should be recorded (new patterns introduced,
   significant tradeoffs made, constraints discovered), flag them for `docs/DECISIONS.md`.
8. **Verdict**: Approve / Request changes / Needs clarification.

> **Verdict bias**: Default to "Request changes" unless you can prove correctness for all critical paths. The burden of
> proof is on the code, not the reviewer.

### 2.7 Offer Fixes and Unit Tests

For each identified issue:

1. Propose a concrete code fix.
2. Provide relevant unit tests following the project conventions.

Unit test file location convention: see `docs/PROJECT_CONTEXT.md` section `## Testing`.

Treat wrong test project placement as a review finding. If a test targets one assembly but lives under another
assembly's test project, request changes. If the matching test project does not exist, require creating it rather than
accepting the wrong destination.

Reference test style examples listed in `docs/PROJECT_CONTEXT.md` section `## Testing`.

## Step 3: Report Findings

After presenting the review:

1. Report the verdict (Approve / Request Changes / Needs Clarification) with all findings.
2. **Do NOT apply fixes directly.** The reviewer must remain independent — applying changes is the orchestrating
   session's responsibility via `execute-task`.
3. If verdict is Request Changes, list the specific issues to fix. The orchestrating session dispatches `execute-task`
   to address them.

## Notes

- If anything is unclear about the requirements or the code, **ask the user** — do not make assumptions. Refer to
  `docs/STAKEHOLDERS.md` for escalation guidance.
- When the diff is large, focus on the most impactful changes first.
- Always verify string literals, magic values, and status codes against the Jira ticket spec.
- Pay special attention to integration-specific API field values listed in `docs/PROJECT_CONTEXT.md` sections
  `## Source layout` and `## Project-specific constraints` — typos in status strings or field names can cause silent
  failures.

## Next

**If verdict is Approve:** invoke the `wrap-up` skill to promote exploration entries, verify doc updates, and report final status.

**If verdict is Request Changes:** report the findings back to the orchestrating session and stop — this skill runs
as a subagent and does not dispatch subagents or apply fixes. The orchestrating session then creates a
**fix-cycle TODO** and a SIMPLE fix task file from the review findings using the SIMPLE template in `task-files.md`:

TODO:

```markdown
- [ ] Create fix task from review findings
- [ ] Implement fix (execute-task subagent)
- [ ] Verify fix (verify-task subagent)
- [ ] Re-run pr-review (pr-review subagent)
```

Fix task format:

- TASK: "Fix pr-review findings: \<list the specific issues\>"
- DONE WHEN: one checkbox per finding + compile check + scope check
- VERIFY: the orchestrating session dispatches a fresh subagent to run `verify-task` (see `verify-task`)

The orchestrating session dispatches a fresh subagent to run `execute-task` with that fix task file; when it returns,
the orchestrating session dispatches another to run `verify-task` (model: haiku, effort: medium), then another to run
`pr-review` (model: sonnet, effort: high). If the new review also returns Request Changes, the orchestrating session
creates a new fix-cycle TODO and repeats.

**Circuit breaker:** if the same finding appears in 2 consecutive review cycles, or if 3 review cycles complete
without reaching Approve, stop and escalate to the user — the issue likely requires a design discussion, not
another fix attempt.
