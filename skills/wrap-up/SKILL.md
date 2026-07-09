---
name: wrap-up
description: Use after pr-review returns an Approve verdict to promote exploration entries, verify doc updates, and report final status. TRIGGER — invoke only after pr-review approves.
argument-hint: Provide the branch slug and pr-review verdict
---

# Wrap-up

**Core principle:** No loose ends — verify every step completed before declaring done.

## When to use

After pr-review returns an Approve verdict. If pr-review has not run or the verdict is not Approve, stop and instruct the user to run pr-review first.
This is the terminal skill in the workflow chain — it ensures post-implementation cleanup happens instead of being forgotten.

When starting wrap-up, create this TODO — **every item below, verbatim** (never a single item named after the skill) — and mark items done as you complete them:

TODO:

```markdown
- [ ] Promote exploration.md entries to target docs
- [ ] Verify DOC UPDATE sections from task files were fulfilled
- [ ] Report final status and next steps to user
```

## Step 1: Promote exploration entries

Read `docs/tasks/{branch-slug}/exploration.md`. For each flagged entry, promote to the target doc:

| Flag | Target doc |
|---|---|
| `[CODE_CONVENTIONS]` | `docs/CODE_CONVENTIONS.md` |
| `[ARCHITECTURE]` | `docs/ARCHITECTURE.md` |
| `[LESSONS]` | `docs/LESSONS.md` |
| `[DECISIONS]` | `docs/DECISIONS.md` |
| `[NONE]` | Not promoted — deleted with the log |

Rules:
- **Append-only** — never modify existing doc content.
- If an entry is questionable or you're unsure about placement, hold it and ask the user.
- After all entries are promoted, delete the exploration log.
- If the exploration log doesn't exist or is empty, skip this step.

## Step 2: Verify doc updates

Read each task file in `docs/tasks/{branch-slug}/`. For STANDARD/EPIC tasks with a DOC UPDATE section:

1. Extract the target docs and expected updates.
2. Grep the target docs to confirm the updates were applied.
3. Flag any missing doc updates.

If all doc updates are confirmed, mark this step done. If any are missing, report them.

## Step 3: Report final status

Report to the user:

```text
## Wrap-up complete

### Exploration entries promoted
- [CODE_CONVENTIONS] <entry> → docs/CODE_CONVENTIONS.md
- [LESSONS] <entry> → docs/LESSONS.md
  (or: no entries to promote)

### Doc updates verified
- ✅ docs/ARCHITECTURE.md — updated per task 001
- ❌ docs/DECISIONS.md — missing update from task 002
  (or: all doc updates confirmed)

### Address-feedback rounds
- Round 1: <N> comments addressed (<commit-hash>)
  (or: no address-feedback rounds in this workflow)

### Next steps
- Commit changes (suggested message: <type(scope): subject>)
- Create PR / request merge
```

## Hard rules

- Never skip promotion when the exploration log has entries — unpromoted exploration entries are lost knowledge.
- Never modify existing doc content when promoting — append only.
- If doc updates are missing, report them — do not apply them yourself. The execute-task subagent owns implementation.

## Handoff

- **Report:** final status (exploration promoted, doc updates verified, address-feedback rounds).
