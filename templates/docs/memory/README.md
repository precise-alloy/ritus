# memory/ — Multi-session context snapshots

EPIC tasks use memory files to persist context across sessions.

## Lifecycle

1. `ticket-review` creates a memory file when generating an EPIC task (using the `epic-memory.md` template)
2. `execute-task` updates State + Tasks table after each session
3. On expiry: decisions and lessons are promoted to long-term docs, then the file is deleted

## Format

See `epic-memory.md` template in the `ticket-review` skill for the canonical format and naming rules.

## Expiry

If Auto-expire passed AND feature done → delete (after promoting decisions/lessons).
If still active → extend date and note why.

## On workflow adoption

Existing memory files are NEVER touched.
