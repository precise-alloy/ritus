# Dispatch - executing a driving TODO

How the **main thread** turns a *driving TODO* into work. Load this before walking a driving TODO. Worker skills
never load it - they stay pure capabilities and never dispatch, so this capability stays out of
dispatched-subagent contexts.

## The `## Handoff` convention

Every workflow skill ends with a `## Handoff`: its **Report** and, for skills the main
thread tracks, a **TODO update** - the driving TODO is the single control surface the main thread owns and executes.
A skill never executes its own update. (Companion standards also end with a `## Handoff`, but Report-only - no TODO
update.)

- **Orchestrators** (`ticket-review`, `address-feedback`, `debug`) generate the run's TODO items up front.
- **Workers** (`execute-task`, `verify-task`, `pr-review`) run as dispatched subagents: they **report a verdict** and
  name their follow-up (a fix cycle), which the **main thread applies** on their behalf per the outcome table in
  **Dispatch rule** below - a worker can't mutate the TODO it doesn't own. Happy path: nothing to append.
- **Routing** (`brainstorm`, `triage`) set the next step as `invoke <skill>`.
- **Terminal** (`wrap-up`) has no update.
- **Intra-skill worker** (`requirement-analysis`) is spawned by another skill (ticket-review), not from the driving
  TODO; it reports its result to that skill and has no driving-TODO update (see **Subagent configs**).

A TODO item is executed by the main thread as one of:

- **dispatch `<skill>` subagent** - delegated, never done inline: spawn a fresh subagent and invoke that skill
  (per the Dispatch rule below).
- `invoke <skill>` - run that main-thread skill inline.

**Appends are idempotent.** When applying a Handoff's TODO update, add an item only if an equivalent item isn't
already queued. So a worker can safely append its follow-up whether or not an orchestrator pre-seeded it - if the
step is already present the append is a no-op; if it's missing (standalone invocation or an incomplete plan) the
append fills the gap.

## Dispatch rule (spawn-then-invoke)

The main thread (the session talking to the user) is the only dispatcher. Walk the active driving TODO top to
bottom; for each **dispatch `<skill>` subagent** item:

1. **Spawn** a fresh generic subagent (skill names are not agent types - a skill is invoked *inside* the spawned
   context).
2. **Invoke** the named skill inside that subagent with the item's inputs, using the run config in
   **Subagent configs** below. The subagent loads that skill and every reference doc the skill needs - its fetch
   helper, conventions, templates - inside its own context; the main thread's part is complete once it has spawned
   the subagent and handed over the inputs.
3. **Mark the item done** when the subagent returns.
4. **Apply the outcome to the TODO - never stop at the verdict.** A dispatched subagent only *reports*; it cannot
   touch the main thread's TODO. So when it returns, the main thread must immediately translate its verdict into the
   TODO items below, before moving on. Reading the verdict without applying its update is the main failure mode -
   don't do it.

| Subagent returns | Main thread appends next (idempotent) |
|---|---|
| `execute-task` (implemented) | `Verify - dispatch verify-task subagent` for that task |
| `verify-task` → PASS | nothing - the plan's next item runs |
| `verify-task` → FAIL | `Fix - dispatch execute-task subagent`, then `Re-verify - dispatch verify-task subagent` |
| `pr-review` → Approve | nothing - continue to `invoke wrap-up` |
| `pr-review` → Request Changes | `Fix - dispatch execute-task subagent`, then `Verify - dispatch verify-task subagent`, then `Re-review - dispatch pr-review subagent` |

This table is the main thread's authority; each worker's own `## Handoff` names the same outcome so it also holds
when the worker is invoked standalone. When a `Fix` item follows pr-review findings, first create a SIMPLE fix task
from those findings (SIMPLE template in `skills/ticket-review/templates/task-files.md`; one DONE WHEN checkbox per
finding + compile + scope) for the execute-task subagent.

**Circuit breaker (cap the fix loop at 3 attempts):** if the same finding recurs across 2 consecutive fix cycles, or 3
fix/re-verify cycles pass without reaching a clean state, stop and escalate to the user - the issue needs a design
discussion, not another fix attempt.

## Subagent configs (per-worker run config)

The worker skills the main thread spawns. Main-thread skills (`brainstorm`, `triage`, `ticket-review`,
`address-feedback`, `debug`, `wrap-up`) run inline and are not spawned - except that `ticket-review` itself spawns
`requirement-analysis` during its analysis step (an intra-skill dispatch: the worker reports its analysis back to
ticket-review and is not a driving-TODO item, so it has no outcome-table row).

| Worker skill | Model | Effort | Tools | Key constraints |
|----------|-------|--------|-------|-----------------|
| `execute-task` | per triage | per triage | all | Implement STEPS exactly; do not redesign |
| `verify-task` | haiku | medium | Read, Grep, Glob, Bash | Read-only except build/test/lint; never fix; never trust implementer claims |
| `pr-review` | sonnet | high | Read, Grep, Glob, Bash, WebFetch | Adversarial; never apply fixes; use `origin/` refs; default to "Request changes" |
| `requirement-analysis` | per triage | medium | Read, Grep, Glob, Bash, Write (review doc / exploration / DECISIONS only) | Read-only otherwise; non-interactive (defer questions to `[NEEDS CLARIFICATION]`); spawned by ticket-review |
