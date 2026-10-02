# Exploration log template

The handoff between contexts on one branch. Each task runs in a fresh executor that can't see what earlier tasks
learned; this file is where that knowledge waits for it. The main thread creates it before the first task; executors,
`debug`, and the main thread append to it; later tasks and `pr-review` read it; `wrap-up` promotes the flagged entries
into the project docs and then deletes it.

Path: `docs/tasks/{branch-slug}/exploration.md`

```markdown
# Exploration log - {branch-slug}

## {YYYY-MM-DD HH:mm} - {task name, or "plan"}

- [ARCHITECTURE] <structural finding> - `file:line`
- [CODE_CONVENTIONS] <a pattern the code follows that isn't written down> - `file:line`
- [LESSONS] <a trap a later change could fall into> - `file:line`
- [DECISIONS] <a decision that outlives this ticket, and why>
- [DEVIATION] <the plan said / done instead / why>
- [NONE] <context a later task needs, with nothing to promote>
```

## Flags

| Flag | After pr-review approves |
|---|---|
| `[ARCHITECTURE]` | Promoted to `docs/ARCHITECTURE.md` |
| `[CODE_CONVENTIONS]` | Promoted to `docs/CODE_CONVENTIONS.md` |
| `[LESSONS]` | Promoted to `docs/LESSONS.md` |
| `[DECISIONS]` | Promoted to `docs/DECISIONS.md` |
| `[DEVIATION]` | Not promoted - wrap-up lists it in its report, for the PR description |
| `[NONE]` | Not promoted - deleted with the log |

## Rules

- Append only; never edit or remove an entry. A correction is a new entry that says what it corrects.
- One line per entry, each with a flag, and with a `file:line` for any claim about code.
- Write only what a later reader would act on. A log that narrates the work buries the one entry that mattered.
- Read the whole log before starting a task, so you don't rediscover what an earlier task already found.
