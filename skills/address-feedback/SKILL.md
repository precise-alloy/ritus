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
- [ ] Classify comments against the keep bar, then present keep + challenged-skip lists for approval (veto allowed)
- [ ] Generate fix task file (round N)
- [ ] Load `dispatch.md`, then implement fix - dispatch execute-task subagent
- [ ] Verify fix - dispatch verify-task subagent
- [ ] Ask user about pr-review re-check
- [ ] If user wants re-check, dispatch pr-review subagent (apply its verdict per dispatch.md)
- [ ] If pr-review approves: invoke wrap-up
- [ ] Report the fixes + suggested commit message + the challenged-skip report (reasons + ready-to-paste replies) - the user reviews the diff and commits
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

**Resolve state:** ADO carries resolve state as per-thread `status` on each thread. GitHub review and issue comment
payloads carry no per-comment resolved flag, so GitHub resolve state is not available from the fetched comments.

## Step 3: Filter to Actionable Comments

Not all PR comments warrant a code change - and the burden of proof is on the comment. Apply the adversarial keep
bar from `skip-reasons.md` in this skill's `templates` directory in order: first auto-skip any comment matching a
`noise` or `resolved` category, then keep a comment only when it passes all four challenge tests (Concrete, Correct,
In scope, Grounded). When a remaining comment fails any test, skip it under exactly one challenged-skip category from
`skip-reasons.md`, and default to skip whenever a comment leaves any test in doubt.

Provider data feeds the `resolved` auto-skip only where it is available: on ADO, classify `resolved` from thread
`status`. GitHub comments carry no resolve state in the fetched payload, so they are classified by the other
categories and the keep bar, and the classifier relies on no per-comment resolved field that GitHub does not provide.

For each comment, record a verdict:

```text
{ filePath?, line?, commentBody, author, verdict: 'keep' | 'auto-skip' | 'challenged-skip', category?, reason?, suggestedReply? }
```

`filePath` and `line` are absent for general PR conversation comments (GitHub `issueComments`), which have no file
location, so the classifier represents them without inventing coordinates.

The optional fields follow the verdict: `keep` sets no `category`, `reason`, or `suggestedReply`; `auto-skip` sets
`category` to `noise` or `resolved` with no `reason` or `suggestedReply`; `challenged-skip` sets `category` to one of
`incorrect`, `out-of-scope`, `subjective`, `speculative`, or `question` and requires both `reason` and `suggestedReply`.

- **keep** - passes all four challenge tests; feeds a fix step.
- **auto-skip** - `noise` or `resolved`; report as a collapsed count only.
- **challenged-skip** - `incorrect`, `out-of-scope`, `subjective`, `speculative`, or `question`. Write a `reason`
  (cite `file:line` for `incorrect`) and a `suggestedReply` the developer can paste onto the PR. State both
  plainly and professionally - the developer posts them verbatim.

Present both lists to the user at one gate:

```text
Found N actionable comments. K challenged-skips (reason + reply each). M auto-skipped (noise/resolved).

Actionable (will be fixed):
1. [src/index.ts:42] @reviewer1: "Add null check before accessing .name"
...

Challenged-skips (judged non-actionable - veto any to move it back to Actionable):
1. [src/utils.ts:15] @reviewer2 - subjective: a style preference with no backing convention.
   Suggested reply: "Thanks - this is a style preference and the current form matches the surrounding code, so I'll keep it as is."
2. [src/api.ts:8] @reviewer3 - out-of-scope: valid, but unrelated to this PR's change.
   Suggested reply: "Good catch - this sits outside this PR's scope, so I've opened a follow-up to track it."
...

Proceed with the actionable fixes?
```

**Hard gate - wait for user approval before proceeding.** When the user vetoes a challenged-skip, move it into the
actionable list before generating the fix task.

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

## Hard rules

- If a comment references a file that doesn't exist, flag it and skip
- If execute-task or verify-task fails, stop and report - do not auto-retry
- Load `code-conventions` and `security` companion skills when applicable

## Handoff

- **Report:** the round-N fixes + a suggested commit message + the challenged-skip report (each skip's reason and ready-to-paste reply), ready for the user to review and commit locally.
- **TODO update:** if the pr-review re-check runs, its verdict is applied per `dispatch.md` (Approve → `invoke wrap-up`;
  Request Changes → a Fix → Verify → Re-review cycle first). If the re-check is skipped, wrap-up does not run (it
  requires a pr-review approval) and the round ends with the fixes ready for the user to commit.

When more review comments arrive on the PR, invoke `address-feedback` again - it auto-detects the next
round number.
