---
name: triage
description: Use before any implementation work - classifies changes by blast radius and recommends a model capability and effort. TRIGGER - invoke when user provides a requirement, feature request, or ticket key/URL (e.g., PROJ-123)
argument-hint: Provide the requirement, feature request, bug report, or ticket URL/key to classify
---

# Triage

**Core principle:** Classify before you load context. The blast radius of a change determines how much process it
needs - not how simple it looks.

## When to use

Run before any context load or task generation. Every incoming change must be classified first.

When starting triage, create this TODO - **every item below, verbatim** (never a single item named after the skill) - and mark items done as you complete them:

TODO:

```markdown
- [ ] Classify the requirement
- [ ] State classification + recommended model
- [ ] Load next skill (ticket-review or implement directly for TRIVIAL)
```

## Input handling

If the user provides a **ticket key or URL** (e.g., `PROJ-123`, Jira URL) instead of a plain requirement:

- Default classification to **STANDARD** - ticket content is not available at triage time.
- Skip classification signals - proceed directly to Output and the Handoff (which invokes ticket-review).
- `ticket-review` may upgrade to EPIC after fetching and analyzing the ticket content.

If the user provides a **plain requirement**, classify using the signals below.

## Classification signals

| Signal                                                                    | Weight          |
|---------------------------------------------------------------------------|-----------------|
| Blast radius - how many systems / modules / teams affected                | **Primary**     |
| Contract impact - does a public interface / shared type change?           | **Primary**     |
| Validation clarity - is pass/fail unambiguous without running the system? | **Primary**     |
| File count                                                                | Supporting hint |
| LOC                                                                       | Supporting hint |

## Classification levels

| Level        | Criteria                                                                    | Output                           |
|--------------|-----------------------------------------------------------------------------|----------------------------------|
| **TRIVIAL**  | Single file, no public contract change, clear validation, low blast radius  | Direct fix - no task file        |
| **SIMPLE**   | ≤2 files, no cross-module contract, clear path, low blast radius            | Task note: TASK + DONE WHEN + VERIFY |
| **STANDARD** | Cross-file, design decision, public contract changed, or validation unclear | Full task file                   |
| **EPIC**     | Multi-session, multiple modules, new architecture pattern                   | Full task file + memory file     |

## Safety override

Force upgrade to STANDARD regardless of classification when touching:

- auth / session / token handling
- payment / billing logic
- database migrations
- tenant / workspace isolation
- infra / runtime config
- shared contracts (types or interfaces exported across modules)

## Context budget per level

| Level    | Load                                                                                       | Approx tokens |
|----------|--------------------------------------------------------------------------------------------|---------------|
| TRIVIAL  | ritus golden rules + grep target file                                                      | ~1k           |
| SIMPLE   | ritus + relevant skill file                                                                | ~2–3k         |
| STANDARD | ritus + docs/PROJECT_CONTEXT.md + relevant skills + docs/ARCHITECTURE.md (if new resource) | ~5–8k |
| EPIC     | Full context + memory file                                                                 | ~10–15k       |

Standards tokens are in addition to the budget above - load applicable standard skills per ritus standards table.

## Output

After classification, state:

1. **Classification level** - TRIVIAL / SIMPLE / STANDARD / EPIC
2. **Recommended model and effort** - read the model routing table from `docs/PROJECT_CONTEXT.md` `## Model routing` and
   include the recommended model and effort level for this classification. When dispatching subagents, use these values.

## Handoff

- **Report:** the classification (TRIVIAL / SIMPLE / STANDARD / EPIC) + recommended model/effort.
- **TODO update:**
  - TRIVIAL → no TODO; implement directly in this session (ritus golden rules), self-verify with build + test, then
    report to the user.
  - SIMPLE / STANDARD / EPIC → `invoke ticket-review`.
