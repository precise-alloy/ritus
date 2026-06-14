# memory/ — Multi-session context snapshots

## Lifecycle
1. Architect agent creates when starting an EPIC
2. Agent updates State + Tasks table after each session
3. Human deletes when all tasks done + logs in CHANGELOG.md

## Format

```markdown
# <Feature> — Context
Created-by: <first task ID>
Active-until: <last task ID> done
Owner: <module>
Auto-expire: <YYYY-MM-DD — 14 days from creation>

## State
<!-- What exists right now after last session -->

## Decisions
<!-- Key decisions with rationale — never delete -->

## Tasks
| # | File | Status | Depends on |
|---|---|---|---|

## Next
<!-- What runs next session -->
```

## Expiry
If Auto-expire passed AND feature done → delete.
If still active → extend date and note why.

## On workflow adoption
Existing memory files are NEVER touched.
