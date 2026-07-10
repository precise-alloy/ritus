# Exploration Log Template

Create `docs/tasks/{branch-slug}/exploration.md` during requirement analysis - `requirement-analysis` seeds it, and
ticket-review creates it for the SIMPLE inline path. It must exist before the first task on a branch starts.

This file is **append-only** - subagents add entries, never modify or remove existing ones. Safe for parallel agents.

## Entry format

Each entry is timestamped, tagged with the task name, and flagged with a target doc:

```markdown
# Exploration Log - {branch-slug}

## {YYYY-MM-DD HH:mm} - {task-name}

- [CODE_CONVENTIONS] <codebase pattern discovered - one line>
- [ARCHITECTURE] <structural finding - one line>
- [LESSONS] <dangerous pattern found - one line>
- [DECISIONS] <non-obvious decision made - one line>
- [NONE] <useful context, no doc update needed - one line>
```

## Flags

| Flag | Promoted to | When |
|---|---|---|
| `[CODE_CONVENTIONS]` | docs/CODE_CONVENTIONS.md | After pr-review approves |
| `[ARCHITECTURE]` | docs/ARCHITECTURE.md | After pr-review approves |
| `[LESSONS]` | docs/LESSONS.md | After pr-review approves |
| `[DECISIONS]` | docs/DECISIONS.md | After pr-review approves |
| `[NONE]` | Not promoted | Deleted with exploration log |

## Rules

- One entry per finding. Keep entries to one line.
- Flag every entry - no unflagged lines.
- Read the full log before starting work - avoid re-discovering what another subagent already found.
- Append before exiting - don't batch; write as you discover.
