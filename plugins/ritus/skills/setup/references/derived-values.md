# Derived values

Computed from the answers, never asked. Write them to `docs/profiles/team.yml`; the user can override any of them
there.

## Tasks path - `tasks_path_convention`

`docs/tasks/{branch-slug}/{NNN-name}.md` for every team, `{branch-slug}` being the branch name with `/` replaced by
`-`. Resuming a run, verification, and wrap-up all look for task files there.

## Branch naming - `branch_format`

```text
feat/{ticket}-{slug}       new feature
fix/{ticket}-{slug}        bug fix
chore/{slug}               tooling, dependencies, config
refactor/{slug}            restructuring with no behavior change
docs/{slug}                documentation only
test/{slug}                tests only
```

With `ticket_format` `none`, drop the ticket segment (`feat/{slug}`). Otherwise use its shape: `feat/PROJ-123-{slug}`,
`feat/#123-{slug}`, or `feat/12345-{slug}`. With several ticket systems, use the first one's shape; developers pick the
key that applies. In `team.yml`, write the whole block as a block scalar (`branch_format: |`).

## By team size

| Team | `pr_reviewers` | `memory_expiry_days` | `traceability_policy` |
|---|---|---|---|
| `solo` | 0 - self-merge allowed | 60 | Commit messages only; no ticket ID required |
| `small` | 1 | 30 | Ticket ID in the branch name and the commit message |
| `medium` | 1-2 | 21 | Ticket ID in the branch, the commit, and the PR title |
| `large` | 2 | 14 | Ticket ID in the branch, the commit, the PR title, and the task file name |

Memory expiry is shorter for bigger teams because more EPICs run at once and their context goes stale faster. When an
EPIC memory file reaches its expiry date, before deleting it: append its decisions to `docs/DECISIONS.md`, its lessons
and failures to `docs/LESSONS.md`, and a one-line summary to `docs/CHANGELOG.md`.
