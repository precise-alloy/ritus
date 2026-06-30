# LESSONS.md — Scar Tissue Log

Reactive discoveries from bugs, incidents, and near-misses.
Each lesson encodes a "never again" rule learned from something that actually went wrong.

**Read this file during STANDARD/EPIC planning if the task touches a module with a known lesson.**

---

## Format

```text
### LESSON-NNN: {title}
Date: YYYY-MM-DD
Module: {module affected}
What happened: {brief description of the incident or bug}
Root cause: {technical reason}
Rule: {concrete "never do X" / "always do Y" statement}
Fix: {what resolved it}
Constraint added: ritus → {section} | none
Decisions-ref: DECISION-NNN | none          ← optional — omit if no ADR was created
Superseded-by: LESSON-NNN ({reason}) | —    ← optional — omit if still active
```

**Field rules:**

- `Decisions-ref`: fill only when the lesson led to a formal ADR in `docs/DECISIONS.md`. Leave out (don't write `none`) if no ADR exists — omitting keeps entries clean.
- `Superseded-by`: fill only when the lesson is no longer valid (e.g. library upgraded, pattern replaced). Absence means active — no `Status: Active` field needed.

---

## When to add a lesson

Add an entry here when a bug fix reveals a pattern that **must never repeat** — not just "we fixed a bug" but "we now know this category of mistake is dangerous in this codebase."

Examples of lesson-worthy bugs:
- A missing auth guard that allowed unauthorized access
- A state machine jump that corrupted workflow status
- An agent that silently swallowed an error and produced incorrect output
- A DB write that overwrote data without creating a version first
- A retry loop with no cap that caused runaway jobs

**Not every bug needs a lesson.** Typos, missing fields, off-by-one errors — fix them and commit. Lessons are for patterns, not one-offs.

---

## Lessons

<!-- Add entries below as they are discovered. -->
<!-- Start at LESSON-001. Increment sequentially. -->

<!-- Example (delete when first real lesson is added):

### LESSON-001: Example — always cap retry loops
Date: 2025-01-15
Module: queue/workers
What happened: A BullMQ worker entered an infinite retry loop when an external API returned a recoverable error. Job count grew unbounded.
Root cause: No `attempts` cap set on the queue job config. BullMQ default is unlimited retries.
Rule: Always set `attempts` and `backoff` on every BullMQ job. Never rely on the default.
Fix: Added `attempts: 3, backoff: { type: 'exponential', delay: 2000 }` to all job definitions.
Constraint added: ritus → Project-specific constraints
Decisions-ref: DECISION-001
Superseded-by: —

-->