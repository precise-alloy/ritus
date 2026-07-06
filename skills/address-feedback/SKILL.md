---
name: address-feedback
description: Use when PR review comments need to be addressed — fetches review feedback, generates fix tasks, dispatches execute-task, commits locally. TRIGGER — invoke when user says "address feedback", "fix PR comments", "resolve comments", "address review", "fix review feedback", or provides a PR URL with review comments to fix. Do NOT use for reviewing code — that is pr-review
argument-hint: Provide the PR URL (GitHub or Azure DevOps) and optionally the count of comments to process
---

# Address Feedback

**Core principle:** Read the actual review feedback, understand what each comment asks, fix it, verify it, commit
locally. Never push — the human reviews the diff and pushes when ready.

## When to use

After a PR is created and reviewers (human or AI) have left comments that need code changes. This skill bridges
PR review comments to actionable task files for execute-task.

**Hard gate — before any other action, create this TODO list and follow it exactly.**

TODO:

```markdown
- [ ] Fetch and filter PR comments
- [ ] Present filtered list to user for approval
- [ ] Generate fix task file (round N)
- [ ] Dispatch execute-task subagent — do NOT implement fixes in this session
- [ ] Dispatch verify-task subagent — do NOT self-verify
- [ ] Ask user about pr-review re-check
- [ ] Create local commit — do NOT push
- [ ] Present questions to user (if any)
```

Mark each item as completed. If any step fails, stop and report — do not skip.
Do not implement fixes in this session — this session orchestrates, a fresh subagent implements.

## Step 1: Gather Input

Ask the user for:

1. **PR URL** — GitHub (`https://github.com/owner/repo/pull/123`) or Azure DevOps PR URL
2. **Comment count** (optional) — limit to the latest N comments. Default: all.

Determine the provider from the URL format:
- `github.com` → GitHub provider
- `dev.azure.com` or `*.visualstudio.com` → ADO provider

## Step 2: Fetch PR Comments

Read `remote-api-access.md` in the `shared` skill directory for the remote API helper instructions.

Fetch PR metadata to get branch info:

For GitHub:

```bash
bun run "<plugin-root>/scripts/remote-api.ts" github pr "<PR_URL>"
bun run "<plugin-root>/scripts/remote-api.ts" github comments "<PR_URL>" [count]
```

For Azure DevOps:

```bash
bun run "<plugin-root>/scripts/remote-api.ts" ado pr "<PR_URL>"
bun run "<plugin-root>/scripts/remote-api.ts" ado pr-threads "<PR_URL>" [count]
```

If either provider returns `401`, `403`, or a permission-style `404`, stop and ask the user to verify remote access.
Do not continue with stale or partial data.

### Response structure

**GitHub** returns two sets:
- `reviewComments` — inline code review comments with `path`, `line`, `original_line`, `diff_hunk`, `body`,
  `user.login`, `in_reply_to_id`
- `issueComments` — general PR conversation comments with `body`, `user.login`

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

**Hard gate — wait for user approval before proceeding.**

## Step 4: Detect Round Number

Check `docs/tasks/{branch-slug}/` for existing `fix-review-round-*.md` files:

- No existing files → round 1
- `fix-review-round-1.md` exists → round 2
- Pattern: `fix-review-round-{N}.md`

If previous rounds exist, compare comment timestamps against the previous round's task file creation time.
Exclude comments that predate the previous round — they were already addressed. Only include new comments
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

1. **[src/index.ts:42]** Add null check before accessing `.name` — _"@reviewer1: Add null check before accessing .name"_
2. **[src/utils.ts:15]** Rename function to `parseConfig` — _"@reviewer2: Rename this to parseConfig for clarity"_

## DONE WHEN

- [ ] src/index.ts:42 — null check added before `.name` access
- [ ] src/utils.ts:15 — function renamed to `parseConfig`, all call sites updated
- [ ] Compiles/builds without errors
- [ ] Existing tests pass
- [ ] No files outside the referenced paths modified

## VERIFY

After implementation, dispatch a fresh `verify-task` subagent (model: haiku, effort: medium).
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

## Step 6: Execute TODO

Follow the TODO list created at the start. The TODO is the authoritative sequence — refer to it for dispatch
targets, model/effort configs, and gates. Commit message format:

```text
fix(review): address PR review feedback (round N)

- <one-line summary per fix>
```

## Step 7: Handle Questions

If Step 3 flagged comments as questions, present them to the user after fixes are committed:

```text
These comments appear to be questions, not change requests:

1. @reviewer1 on src/api/handler.ts:30: "Why did you choose to use a Map here instead of a plain object?"
2. @reviewer2 (general): "Have you considered adding rate limiting to this endpoint?"

You may want to reply to these directly on the PR.
```

## Hard constraints

- If a comment references a file that doesn't exist, flag it and skip
- If execute-task or verify-task fails, stop and report — do not auto-retry
- Load `code-conventions` and `security` companion skills when applicable

## Next

After the user pushes and receives more review comments, invoke `address-feedback` again — it auto-detects the
next round number.
