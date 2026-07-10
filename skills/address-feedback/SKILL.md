---
name: address-feedback
description: Use when PR review comments need to be addressed - fetches review feedback, generates fix tasks, dispatches execute-task, and prepares a reviewable local change for the user to commit. TRIGGER - invoke when user says "address feedback", "fix PR comments", "resolve comments", "address review", "fix review feedback", or provides a PR URL with review comments to fix. Do NOT use for reviewing code - that is pr-review
argument-hint: Provide the PR URL (GitHub or Azure DevOps) and optionally the count of comments to process
---

# Address Feedback

**Core principle:** Read the actual review feedback, understand what each comment asks, fix it, verify it, and hand
back a reviewable local change with a suggested commit message. The human reviews the diff and commits when ready.

## When to use

After a PR is created and reviewers (human or AI) have left comments that need code changes. This skill bridges
PR review comments to actionable task files for execute-task.

**Hard gate - before any other action, create this TODO list - every item below, verbatim (never a single item named after the skill) - and follow it exactly.**

TODO:

```markdown
- [ ] Fetch and filter PR comments
- [ ] Present filtered list to user for approval
- [ ] Generate fix task file (round N)
- [ ] Load `dispatch.md`, then implement fix - dispatch execute-task subagent
- [ ] Verify fix - dispatch verify-task subagent
- [ ] Ask user about pr-review re-check
- [ ] If user wants re-check, dispatch pr-review subagent (apply its verdict per dispatch.md)
- [ ] If pr-review approves: invoke wrap-up
- [ ] Report the fixes + suggested commit message - the user reviews the diff and commits
- [ ] Present questions to user (if any)
```

Mark each item as completed. If any step fails, stop and report - do not skip.
This session orchestrates; the implement and verify items run as dispatched subagents.

## Step 1: Gather Input

Ask the user for:

1. **PR URL** - GitHub (`https://github.com/owner/repo/pull/123`) or Azure DevOps PR URL
2. **Comment count** (optional) - limit to the latest N comments. Default: all.

The provider is auto-detected from the PR URL - no manual provider selection needed.

## Step 2: Fetch PR Comments

Read `remote-api-access.md` in the `shared` skill directory for the remote API helper instructions.

Fetch PR metadata (provider is auto-detected from the URL):

```bash
bun run "<plugin-root>/scripts/remote-api.ts" pr "<PR_URL>"
```

For review comments (GitHub only):

```bash
bun run "<plugin-root>/scripts/remote-api.ts" comments "<PR_URL>" [count]
```

If auto-detection fails, fall back to explicit provider syntax (e.g., `github pr`, `ado pr`).

If the provider returns `401`, `403`, or a permission-style `404`, stop and ask the user to verify remote access.
Do not continue with stale or partial data.

### Response structure

**GitHub** returns two sets:
- `reviewComments` - inline code review comments with `path`, `line`, `original_line`, `diff_hunk`, `body`,
  `user.login`, `in_reply_to_id`
- `issueComments` - general PR conversation comments with `body`, `user.login`

**ADO** returns threads:
- Each thread has `status`, `threadContext.filePath`, `threadContext.rightFileStart`, `threadContext.rightFileEnd`
- Each thread contains `comments[]` with `author.displayName`, `content`, `commentType`

## Step 3: Filter to Actionable Comments

Not all PR comments need code changes. Classify each comment:

### Keep (actionable)

- Comments requesting specific code changes ("change X to Y", "add null check", "rename this", "use X instead")
- Comments pointing out bugs or issues ("this will crash if...", "missing error handling", "race condition here")
- Comments asking for additions ("add tests for...", "need documentation for...", "missing validation")

### Skip (not actionable)

- Comments that are not valid change requests. Analyze the comment to determine whether it requests code changes. If it does not, skip it and report to the user.
- Resolved/closed threads (ADO: `status !== 'active'`)
- Reply threads where the last message is from the PR author (likely already addressed)
- Approvals, praise, acknowledgments ("LGTM", "looks good", "nice work", "+1")
- Bot-generated comments (CI output, lint reports, coverage reports)
- System/status comments (ADO: `commentType === 'system'`)

### Flag as questions (present to user later)

- Questions that don't request changes ("why did you choose X?", "have you considered...?")
- Comments requesting design discussion rather than code changes

For each kept comment, extract:

```text
{ filePath, line, commentBody, author, type: 'change' | 'addition' | 'question' }
```

Present the filtered summary to the user:

```text
Found N actionable comments (M skipped, K questions flagged for later).
Actionable:
1. [src/index.ts:42] @reviewer1: "Add null check before accessing .name"
2. [src/utils.ts:15] @reviewer2: "Rename this to parseConfig for clarity"
...
Proceed with fixes?
```

**Hard gate - wait for user approval before proceeding.**

## Step 4: Detect Round Number

Check `docs/tasks/{branch-slug}/` for existing `fix-review-round-*.md` files:

- No existing files → round 1
- `fix-review-round-1.md` exists → round 2
- Pattern: `fix-review-round-{N}.md`

If previous rounds exist, compare comment timestamps against the previous round's task file creation time.
Exclude comments that predate the previous round - they were already addressed. Only include new comments
from the current review cycle.

## Step 5: Generate Fix Task File

Create a task file at `docs/tasks/{branch-slug}/fix-review-round-{N}.md`.

Use the **SIMPLE format** (TASK + DONE WHEN + VERIFY) when there are 5 or fewer actionable comments.
Use the **STANDARD format** (with CONTEXT section) when there are more than 5.

### SIMPLE format (5 or fewer comments)

```markdown
## TASK

Address PR review feedback (round N): <count> comments from <PR_URL>

## STEPS

1. **[src/index.ts:42]** Add null check before accessing `.name` - _"@reviewer1: Add null check before accessing .name"_
2. **[src/utils.ts:15]** Rename function to `parseConfig` - _"@reviewer2: Rename this to parseConfig for clarity"_

## DONE WHEN

- [ ] src/index.ts:42 - null check added before `.name` access
- [ ] src/utils.ts:15 - function renamed to `parseConfig`, all call sites updated
- [ ] Compiles/builds without errors
- [ ] Existing tests pass
- [ ] No files outside the referenced paths modified

## VERIFY

Verified fresh by a verify-task subagent.
```

### STANDARD format (more than 5 comments)

Add a CONTEXT section listing all referenced files before STEPS:

```markdown
## CONTEXT

files:
  - src/index.ts         # null check, error handling
  - src/utils.ts         # rename parseConfig
  - src/api/handler.ts   # add validation
  - tests/utils.test.ts  # update test for renamed function
```

## Step 6: Dispatch execution

With the fix task file ready (Step 5), load `dispatch.md`, then walk the remaining TODO items, dispatch `execute-task` (implement the fixes), then `verify-task` (verify), and, if the user wants a re-check, `pr-review`.

Once the fixes are verified, report them to the user with a suggested commit message, and let the user review the diff
and commit locally. Suggested commit message format:

```text
fix(review): address PR review feedback (round N)

- <one-line summary per fix>
```

## Step 7: Handle Questions

If Step 3 flagged comments as questions, present them to the user alongside the reported fixes:

```text
These comments appear to be questions, not change requests:

1. @reviewer1 on src/api/handler.ts:30: "Why did you choose to use a Map here instead of a plain object?"
2. @reviewer2 (general): "Have you considered adding rate limiting to this endpoint?"

You may want to reply to these directly on the PR.
```

## Hard rules

- If a comment references a file that doesn't exist, flag it and skip
- If execute-task or verify-task fails, stop and report - do not auto-retry
- Load `code-conventions` and `security` companion skills when applicable

## Handoff

- **Report:** the round-N fixes + a suggested commit message, ready for the user to review and commit locally.
- **TODO update:** if the pr-review re-check runs, its verdict is applied per `dispatch.md` (Approve → `invoke wrap-up`;
  Request Changes → a Fix → Verify → Re-review cycle first). If the re-check is skipped, wrap-up does not run (it
  requires a pr-review approval) and the round ends with the fixes ready for the user to commit.

When more review comments arrive on the PR, invoke `address-feedback` again - it auto-detects the next
round number.
