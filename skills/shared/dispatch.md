# Dispatch - executing a driving TODO

How the **main thread** turns a *driving TODO* into work. Load this before walking a driving TODO. Worker skills
never load it - they stay pure capabilities and never dispatch, so this capability stays out of
dispatched-subagent contexts.

## Why dispatch, and when a change runs inline

Dispatch protects two things - **independent verification** and a **lean orchestrator context**. A fresh subagent
that did not author a change reviews it with clear eyes and catches what the author is blind to; keeping that work in
subagents also keeps the main thread lean for the rest of the run. Implementation size is a separate matter - a
small dispatched change earns the same independent verification as a large one.

**The execution mode follows triage classification:**

- **TRIVIAL** - the main thread applies the fully-specified single-file edit inline, then self-verifies with the
  build/test/lint commands.
- **SIMPLE and larger** - the main thread dispatches `execute-task` to implement and `verify-task` to verify, each in
  a fresh subagent. Detailed STEPS (exact `from:`/`to:` blocks, exact commands, expected output) make the
  implementation faster and more faithful and keep the **independence** reason for dispatch fully intact: a task whose
  STEPS already carry the exact code is still dispatched, and the executor fits that plan to the current file (confirm
  each `from:` still matches, apply the `to:`, run the commands, confirm the expected output).

**Dispatched work keeps the author and the verifier in separate contexts:** for SIMPLE and larger changes,
verification runs in a fresh `verify-task` (or, at ticket scope, `pr-review`) that did not author the change. A
TRIVIAL fix is the deliberate exception - its blast radius is small enough to self-verify inline with the
build/test/lint commands.

## The `## Handoff` convention

Every workflow skill ends with a `## Handoff`: its **Report** and, for skills the main
thread tracks, a **TODO update** - the driving TODO is the single control surface the main thread owns and executes.
A skill never executes its own update. (Companion standards also end with a `## Handoff`, but Report-only - no TODO
update.)

- **Orchestrators** (`ticket-review`, `address-feedback`, `debug`) generate the run's TODO items up front.
- **Workers** (`execute-task`, `verify-task`, `pr-review`) run as dispatched subagents: they **report a verdict** and
  name their follow-up (a fix cycle), which the **main thread applies** on their behalf per the outcome table in
  **Dispatch rule** below - a worker can't mutate the TODO it doesn't own. Happy path: nothing to append.
- **Routing** (`brainstorm`, `triage`, `wrap-up`) set the next step as `invoke <skill>` (`wrap-up` → `invoke comprehension`).
- **Terminal** (`comprehension`) has no update.
- **Intra-skill worker** (`requirement-analysis`) is spawned by another skill (ticket-review), not from the driving
  TODO; it reports its result to that skill and has no driving-TODO update (see **Subagent configs**).

A TODO item is executed by the main thread as one of:

- **dispatch `<skill>` subagent** - delegated, never done inline: spawn a fresh subagent and invoke that skill
  (per the Dispatch rule below).
- `invoke <skill>` - run that main-thread skill inline.

**Fix items are inserted after the current step, not appended to the end.** When applying a Handoff's TODO update,
place each new item **immediately after the step that produced it** (the just-finished verify/review), ahead of any
downstream steps already queued - so a `Re-verify` runs before a `pr-review` that was already planned, never after it.
The update is idempotent: if an equivalent item is already queued in that position it's a no-op; if it's missing
(standalone invocation or an incomplete plan) it fills the gap.

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
   TODO items below and **insert them right after the item just finished** - ahead of any downstream steps already
   queued (e.g. a pending `pr-review`) - before moving on. Reading the verdict without applying its update is the main
   failure mode - don't do it.

| Subagent returns | Main thread inserts next, right after the current item (idempotent) |
|---|---|
| `execute-task` (implemented) | `Verify - dispatch verify-task subagent` for that task |
| `execute-task` → BLOCKED (a STEP is unclear or provably wrong) | apply a targeted correction to that task's STEPS that stays within the approved review doc, then re-dispatch `execute-task`; escalate to the user when the correction would change design or scope, or when the circuit breaker trips |
| `verify-task` → PASS | nothing - the plan's next item runs |
| `verify-task` → FAIL | `Fix - dispatch execute-task subagent`, then `Re-verify - dispatch verify-task subagent` |
| `pr-review` → Approve | nothing - continue to `invoke wrap-up` |
| `pr-review` → Request Changes | `Fix - dispatch execute-task subagent`, then `Verify - dispatch verify-task subagent`, then `Re-review - dispatch pr-review subagent` |
| any worker → `BLOCKED` (insufficient reasoning power) | re-dispatch one step up the `cheap → standard → most capable` ladder; if already `most capable`, stop and escalate to the user (terminal - do not loop) |

This table is the main thread's authority; each worker's own `## Handoff` names the same outcome so it also holds
when the worker is invoked standalone. When a `Fix` item follows pr-review findings, first create a SIMPLE fix task
from those findings (SIMPLE template in `skills/ticket-review/templates/task-files.md`; one DONE WHEN checkbox per
finding + compile + scope) for the execute-task subagent.

**Circuit breaker (cap the fix loop at 3 attempts):** if the same finding recurs across 2 consecutive fix cycles, or 3
fix cycles (fix/re-verify or plan-fix/re-dispatch) pass without reaching a clean state, stop and escalate to the
user - the issue needs a design discussion, not another fix attempt.

## Subagent configs (per-worker run config)

The worker skills the main thread spawns. Main-thread skills (`brainstorm`, `triage`, `ticket-review`,
`address-feedback`, `debug`, `wrap-up`, `comprehension`) run inline and are not spawned - except that `ticket-review` itself spawns
`requirement-analysis` during its analysis step (an intra-skill dispatch: the worker reports its analysis back to
ticket-review and is not a driving-TODO item, so it has no outcome-table row).

**Model capability, not model names.** Each worker names one of `cheap`, `standard`, or `most capable` -
never a vendor model ID. Map it to the best-matching model your platform offers:

- **cheap** - fastest, lowest-cost model; mechanical, single-file, fully-specified work and independent verification.
- **standard** - default model; multi-file integration, judgment, requirement analysis, adversarial review.
- **most capable** - highest-capability model; architecture / design decisions and complex reasoning.

**Model selection rule (select by capability; pin a concrete model at dispatch):** choose the *lowest* capability
(`cheap → standard → most capable`) that can do the job. At dispatch time, map that capability to the concrete model
your platform provides and name it explicitly - never let a subagent silently inherit the session's model. Scale the
reviewer's capability to the diff's size and risk. If a subagent returns BLOCKED for insufficient reasoning power,
re-dispatch it one step up the ladder; if it is already `most capable`, stop and escalate to the user (see the
`BLOCKED` row in the outcome table). Tool names below denote capabilities - map them to your platform's equivalents
(e.g. `web fetch` = your URL-reading tool).

| Worker skill | Model capability | Effort | Tools | Key constraints |
|----------|------------------|--------|-------|-----------------|
| `execute-task` | per triage | per triage | all | Implement STEPS exactly; do not redesign |
| `verify-task` | cheap | medium | Read, Grep, Glob, Bash; Playwright MCP browser tools when `ritus-ui` enabled | Read-only except build/test/lint; never fix; never trust implementer claims |
| `pr-review` | standard | high | Read, Grep, Glob, Bash, `web fetch`; Playwright MCP browser tools when `ritus-ui` enabled | Adversarial; never apply fixes; use `origin/` refs; default to "Request changes" |
| `requirement-analysis` | per triage | medium | Read, Grep, Glob, Bash, Write (review doc / exploration / DECISIONS only) | Read-only otherwise; non-interactive (defer questions to `[NEEDS CLARIFICATION]`); spawned by ticket-review |

The Playwright MCP browser tools are granted to `verify-task` and `pr-review` only when the optional `ritus-ui`
plugin is enabled - enablement is the presence of its skills and Playwright MCP tools in the session (see
`ritus-ui.md` in `shared/`). Disabled sessions keep the narrow tool set (`verify-task`: `Read, Grep, Glob, Bash`;
`pr-review`: those plus `web fetch`). Each worker keeps its existing constraints - `verify-task` stays read-only except
build/test/lint, and `pr-review` reports findings and defaults to "Request changes".
