# Dispatch - walking a driving TODO

How the main thread - the session talking to the user - turns a driving TODO into work. Load this before walking one.
Worker skills never load it and never dispatch: the main thread owns the TODO, the fix loop, and the channel to the
user, and a nested agent's result would not come back to it.

## Why dispatch

A subagent starts without this conversation, so every dispatch pays to rebuild context. Dispatch for one of three
reasons:

1. **Independence.** Authors grade their own work generously, so the check on a change runs in a context that did not
   write it. This is the strongest reason, and it does not depend on context size.
2. **Noisy work, small result.** Reading a lot of code, or a build and test log per task: a fresh context per task
   keeps one clear goal, and the main thread keeps only the report.
3. **Specialization.** A different stance (adversarial review), read-only tools, or a routed model.

Implementation runs one task at a time: tasks share the working tree, so parallel executors would mix each other's
build output and `git status`. Only read-only work runs in parallel.

## Mode by level

Levels are defined in `skills/shared/levels.md`.

| Level | Implement | Independent check |
|---|---|---|
| TRIVIAL | Main thread, inline | Self-check with build, test, and lint - the one case where the author checks its own change |
| SIMPLE | Main thread invokes `execute-task` | Dispatch `pr-review`, telling it no per-task verification ran, so it re-runs the Acceptance commands and build/test on the final tree. A flow without a pr-review step dispatches `verify-task` instead |
| STANDARD, EPIC | Dispatch `execute-task` per task | Dispatch `verify-task` after each task; after the last one, dispatch `pr-review` |

Orchestrators build their TODO from this table. When a TODO item already says `invoke` or `dispatch`, do what it says.

## Walking the TODO

Top to bottom, one item at a time:

- `invoke <skill>` - run the skill here, in the main thread.
- `dispatch <skill> subagent` - start a fresh general-purpose subagent and invoke the skill inside it (skill names are
  not agent types). Fresh means it starts without this conversation - not a fork that inherits it: a fork is not
  independent, and it carries all of this context along.

Before dispatching:

- **Write down what the user said.** The subagent sees files, not this conversation. A constraint, a rejected
  approach, or a name the user gave that changes the work goes into the plan or task file first - which also keeps it
  safe through compaction.
- **Pass inputs, not context:** the worker's inputs (table below) plus what it cannot find on its own - companion
  `load` items, extra standards to apply, and for SIMPLE that no per-task verification ran. Context a hook injected
  into this session does not reach subagents.

When it returns:

- **Keep the report, not the work.** No logs, no pasted files. Detail a later task needs belongs in `exploration.md`
  or the case file.
- **Apply the outcome before moving on** - stopping at a verdict without acting on it is the most common way a run
  goes wrong. Insert follow-up items right after the item that produced them, ahead of anything already queued, so a
  re-verify runs before a pending pr-review. Inserting is idempotent: if an equivalent item is already there, do
  nothing.
- **Record progress where a new session will look.** Set the task file's `Status` line to `implemented` when
  `execute-task` returns DONE, and to `verified` when its independent check passes (`verify-task` PASS; for SIMPLE,
  `pr-review` Approve). The driving TODO lives only in this session; a resumed run starts from these lines.

## Outcomes

| Worker returns | Insert right after the current item |
|---|---|
| `execute-task` DONE | STANDARD/EPIC: verify that task. SIMPLE: nothing - the review is next |
| `execute-task` BLOCKED | If the plan or the user's earlier words settle it, write the answer into the task file; otherwise ask the user and write their decision there (and into the plan when sibling tasks rely on it). Then continue the same executor with the decision |
| `verify-task` PASS | nothing; carry its `Outside the task` notes into the `pr-review` brief, or to the user when no review follows |
| `verify-task` FAIL | Fix: continue the task's executor with the findings (if the main thread implemented, fix them here). Then verify again with a fresh `verify-task` |
| `pr-review` Approve | nothing - `invoke wrap-up` follows |
| `pr-review` Request Changes | Fix the findings (below), then re-review: continue the reviewer, or dispatch a fresh `pr-review` with its previous report |
| `pr-review` Needs Clarification, or any worker BLOCKED on something only the user can answer or fix | Relay it to the user; write the answer where the worker will read it, then continue or re-dispatch it |
| any worker BLOCKED for lack of reasoning power | Take it to the user: they can switch the session model, then dispatch it again fresh |
| a companion's blocking FAIL | Fix the findings as for a review (below), then run the companion's check again. An advisory report is recorded and the run continues |

**Fixing review findings.** When the main thread implemented the change, it applies the findings itself, as it would a
fix task: don't argue with a finding, and if you disagree with one, put it to the user instead of dropping it.
Otherwise write a fix task from `skills/ticket-review/templates/task.md` and dispatch `execute-task` for it. No
verify-task runs on a review fix; the re-review re-runs its checks.

**Circuit breaker.** When the same finding comes back in two consecutive fix cycles, or three cycles pass without a
clean result, stop and take it to the user: it needs a design conversation, not another attempt.

## Resume

When the harness lets you message a subagent that has finished, one agent can keep one unit of work until it is done.
Continue an agent in four places:

| Situation | Continue | Why |
|---|---|---|
| `execute-task` BLOCKED, decision made | that executor | It may have half-edited files; a new executor would have to guess what is done |
| `verify-task` FAIL | the task's executor | The fix is part of the same task |
| Writing or revising a plan needs more facts about the code | the analysis agent | It knows where things are, and the answer is small |
| Re-review after Request Changes | the reviewer | It remembers what it already weighed and dismissed, so reviews converge |

- **File first, message second.** A decision that changes the contract goes into the task file or plan before you
  send it: the next checker reads only files, and would fail the task for exactly what the user allowed. Findings
  against an unchanged contract can go in the message.
- **Always have a fallback.** The agent may be gone - an unsupported harness, a restarted session, an ID lost to
  compaction. Then dispatch fresh from the files and the previous report; never stop a run because resume failed.
- **Dispatch so it can be continued:** a general-purpose agent (some harnesses' built-in explore and plan agents are
  one-shot), in the background where the harness only continues background agents - wait for it to finish before the
  next item - and named by role and task (`execute-003`, `review`) so you can find it after compaction.
- **Don't continue** the verifier (it anchors on its earlier verdict; a fresh one against a fixed checklist converges
  anyway), an executor for the next task (fresh context per task; `exploration.md` is the handoff), or an agent that
  needs a stronger model (a continued agent keeps its model).
- **Don't continue to save tokens.** By then the subagent's cache is usually cold (five minutes on Claude Code) and
  the whole transcript is re-read. What continuing buys is continuity.

## Models

Every subagent runs on the model and reasoning effort the platform gives it - the session's, unless the user configured
subagents otherwise. Ritus doesn't pick either: name neither at dispatch. An older `docs/PROJECT_CONTEXT.md` may still
carry a `## Model routing` section, and `runtime.yml` a `model_routing` key; ignore both - `setup` drops them on its
next run.

## Companions

The session context can carry a **Ritus Companion Registry**: one line per companion, naming its manifest on disk.
When you build or update the driving TODO, read every listed manifest and make sure each integration has an item at
the workflow point its `prompt` names - "after task-generation" means once the task files exist, "before pr-review"
means before the review item. Add a missing item; never duplicate one. A `dispatch` integration follows this contract;
a `load` integration attaches the companion skill as a standard to the named worker, passed in its dispatch input. An
empty or absent registry changes nothing.

## Handoff convention

The driving TODO is the one control surface, and only the main thread changes it.

- **Workers** (`execute-task`, `verify-task`, `pr-review`, the analysis agent, companion workers) end at their report
  and name no next step; the main thread applies it per Outcomes.
- **Orchestrators** (`ticket-review`, `debug`, `address-feedback`) build the driving TODO once the user approves the
  plan or the fix.
- **Routing skills** (`start-ritus`, `brainstorm`, `wrap-up`) name the next `invoke <skill>`; `comprehension` is
  terminal.
- The **analysis agent** is dispatched by `ticket-review` before a plan exists, so it is a step of that skill, not a
  TODO item.

## Worker inputs

| Worker | Inputs | Tools | Notes |
|---|---|---|---|
| `execute-task` | Task or case file path; for a fix, the findings; companion `load` items and extra standards | All | - |
| `verify-task` | Task file path, the executor's report | Read, search, shell | Read-only apart from build/test/lint and the spot check it undoes (`testing.md`); never fixes |
| `pr-review` | Review mode (local change or PR URL), requirement source and the approved plan path or debug case file if there is one, base branch if not the default; whether per-task verification ran, and the `Outside the task` notes it left; for a re-review, the previous report | Read, search, shell, web fetch | Never fixes; compares against `origin/` refs |
| Analysis agent | Full path of `skills/ticket-review/references/analysis-brief.md`; the requirement; what the user said that changes the work; the level and specific questions; branch slug; for an EPIC split, the code area | Read, search, shell, web fetch; writes only downloaded attachments | Non-interactive - open questions come back as `[NEEDS CLARIFICATION]`; continue it for follow-up questions |

Tool names are capabilities; map them to your platform's equivalents.