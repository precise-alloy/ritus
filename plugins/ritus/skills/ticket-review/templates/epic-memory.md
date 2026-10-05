# EPIC Memory File Template

Create `docs/memory/{branch-slug}-{feature-slug}-context.md` for EPIC work.

**Naming rule:** `{branch-slug}` = current git branch name with `/` replaced by `-`.
Example: branch `feat/PROJ-42-auth` + feature `token-refresh` → `memory/feat-PROJ-42-auth-token-refresh-context.md`

This ensures no two developers on different branches collide on the same memory file.

**Expiry:** use memory expiry days from docs/PROJECT_CONTEXT.md Team conventions (set by setup). Default 14 if unset.

**On expiry (mandatory before delete):**

1. Append `## Decisions` entries → `docs/DECISIONS.md`
2. Append failure/lesson entries → `docs/LESSONS.md`
3. Write one-line summary → `docs/CHANGELOG.md`
4. Delete the memory file

## Template

```markdown
# <Feature> - Context

Branch: <git branch name>
Created-by: <first task ID>
Active-until: <last task ID> done
Owner: <module>
Auto-expire: <today + expiry days>

## State

## Decisions

## Lessons

## Tasks

| # | File | Status | Depends on |
| --- | --- | --- | --- |

## QA

<!-- Only when QA mode is not off. The main thread adds each task's affected features and risk as it passes (from its
     .qa.md in `task` mode); the EPIC QA summary is written from this section. -->
Affected features so far:

- (add as tasks complete)

High risk areas:

- (add as tasks complete)

## Next
```
