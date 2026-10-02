---
name: wrap-up
description: Close out a Ritus run once its change is approved - use when pr-review approves, or when the user says wrap up, finish, done, or ready for a PR. Moves what the run learned into the docs, checks the doc updates the tasks promised, and drafts the PR description.
argument-hint: The branch, if not the current one
---

# Wrap-up

Close the run so what it learned outlives it. A run leaves knowledge in its exploration log, in deviations from the
plan, and in follow-ups nobody got to. If none of it reaches the docs and the PR description, the next person starts
from zero and the reviewer approves a change they only half understand.

Run it once the change is approved - by `pr-review` in a Ritus run, or by the user. When nothing has reviewed the
change, offer `pr-review` first, and wrap up without it only if the user says so - then say so at the top of the report.

## 1. Check the promised doc updates

Before you write anything, compare each task file in `docs/tasks/{branch-slug}/` (for one PR of an EPIC, that PR's
tasks) with the change: did each doc its Docs section names (DOC UPDATE in older task files) get the update it
describes?

A missing update is a gap in the change. Report it; don't fill it - not even a one-line edit. Step 2 still promotes
the log's entries into that doc; just don't slip the missing update in with them. An update written here skips the
review the rest of the change had, and the report would then say "done" where it should show a gap. The choice is the user's: have it fixed now, as a fix task like a
review finding, then checked again here - or ship without it, listed as a follow-up.

## 2. Promote the exploration log

Read `docs/tasks/{branch-slug}/exploration.md` - a run that logged nothing has none - and move each flagged entry to
its doc:

| Flag | Goes to |
|---|---|
| `[CODE_CONVENTIONS]` | `docs/CODE_CONVENTIONS.md` |
| `[ARCHITECTURE]` | `docs/ARCHITECTURE.md` |
| `[LESSONS]` | `docs/LESSONS.md` |
| `[DECISIONS]` | `docs/DECISIONS.md` |
| `[DEVIATION]` | The PR description (step 3), not a doc |
| `[NONE]` | Nowhere - it is deleted with the log |

- Append; never rewrite what a doc already says. Follow each doc's existing format and numbering.
- Write each entry for someone who never saw this run: per `skills/shared/standards/writing.md`, with its evidence
  (`file:line`) and the date.
- When you are unsure an entry belongs, or where, ask the user instead of guessing.
- Then delete the log. For one PR of an EPIC with more PRs to come, first copy the `[NONE]` entries later tasks still
  need into the EPIC memory file's State.

## 3. Draft the PR description

From the plan or ticket, the task files, the reports, and the diff. The user posts it as written, so follow
`skills/shared/standards/writing.md`.

- What changes and why, in the reviewer's terms, with the ticket reference `## Team conventions` asks for.
- How it was checked: the commands that ran and what they returned, and any review rounds (`fix-review-round-N.md`)
  with what each addressed.
- Deviations from the plan: what the plan said, what was done instead, and why.
- Follow-ups: everything the run put off - the plan's non-goals marked for later, deferrals in the log and the
  reports, and a missing doc update the user chose to ship without - each with the condition recorded for coming back
  to it. Where none was recorded, say so instead of supplying one: an invented condition hides the gap, and a
  follow-up with no condition is the kind that quietly rots.

## Output

```text
Wrap-up - <branch name>
Reviewed: <pr-review Approve | approved by the user | not reviewed, at the user's request>
Doc updates: <doc> - done per task NNN | missing per task NNN, one per line
Promoted: <entry> -> <doc>, one per line (or none)
Follow-ups without a revisit condition: <each, or none>

PR description:
<the draft>
```

When a doc update is missing, end with the choice - fix it now, or ship it as a follow-up - and end your turn until
the user answers. Once nothing is waiting on them, `invoke comprehension`, unless the change was TRIVIAL.
