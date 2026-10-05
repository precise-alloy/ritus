# Levels

How much process a change gets. Size a change by what it could break, not by how small it looks: a one-line change to
token validation can do more damage than a new page, and full ceremony on a typo fix teaches everyone to skip the
process. `ticket-review` sizes new work with this file; `debug` sizes a fix with it once the cause is known. Who
implements and who checks at each level is in `skills/shared/dispatch.md` "Mode by level".

| Level | Fits when | Plan and approval | Implement and check |
|---|---|---|---|
| TRIVIAL | One obvious edit that adds no logic - a typo, a change to existing copy, a config value the user named | None | Main thread, inline; self-check with build, test, and lint |
| SIMPLE | One logical change with clear acceptance, inside one module, touching no shared contract | A short plan in chat and one task file, approved together | Main thread runs `execute-task`; a fresh `pr-review` re-runs the Acceptance commands |
| STANDARD | Several files or tasks, a design decision, a public contract, or acceptance that still needs working out. The default for a ticket | Analysis subagent reads the code; the main thread writes the plan and task breakdown; one approval | Fresh executor and verifier per task, then `pr-review` |
| EPIC | Several sessions or PRs, several modules, or a new architecture pattern | As STANDARD, with analysis split by code area if it helps, a second approval once the task files exist, and an EPIC memory file | As STANDARD; one PR per phase |

## Signals

Strongest first:

1. **Blast radius** - how many modules, services, or teams a mistake would reach.
2. **Contract impact** - whether a public API, a shared type, persisted data, or another team's consumer changes.
3. **Validation clarity** - whether pass and fail can be stated as a command and its expected result.

File count and lines changed are hints only. Twelve test files updated for a renamed fixture can be SIMPLE; three
lines that change when sessions expire cannot.

## Never below STANDARD

Mistakes in these areas ship green and surface later as a breach, a double charge, or lost data, so they always get an
analysis, a written plan, and an independent check:

- authentication, authorization, sessions, and tokens
- payments and billing
- database migrations
- tenant or workspace isolation
- infrastructure and runtime config
- shared contracts - types or interfaces that other modules import

## Choosing and changing the level

- **A ticket starts at STANDARD.** Its size is unknown until you have read it and the code it touches; lower it once
  both show the change is clearly small.
- **TRIVIAL has nothing to check, so it gets no check.** New logic - a branch, a condition, output in a case that had
  none - or acceptance criteria someone listed make it at least SIMPLE, however small the diff: SIMPLE costs one
  approval and one review, and a skipped check is exactly where a small change ships wrong.
- **When torn between two levels, pick the higher one** and say why. Under-sizing costs a missed caller; over-sizing
  costs one extra approval.
- **The user can move it.** "Just do it", "skip the plan", or "quick fix" lowers it - except in the areas above, where
  it stays STANDARD and you say so in one line. "Full process" or "be careful" raises it.
- **Raise it when the work grows** - analysis finds another caller, a contract, or a risk area - and tell the user
  before going on. Never lower it silently after approval: the user approved a plan with that level's checks in it.

## Output

One line, before any plan, naming the signal that decided it:

`Level: SIMPLE - one validation rule in OrderService, covered by its existing tests`

When the user asked for a different level, say what happened to the request:
`Level: STANDARD - changes token refresh; stays STANDARD despite "just do it"`.

## When not to

- Don't write a plan for TRIVIAL or a task breakdown for SIMPLE - the process would cost more than the change.
- Don't re-size work that already has an approved plan unless the work itself changed.
