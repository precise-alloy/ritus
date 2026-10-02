# Plan template

The plan is what the user approves and what `pr-review` checks the change against. It leads with what needs the
user's call, and it states acceptance so that it can be checked. Keep it short: a plan the user only skims was never
really approved. Drop sections that would only say "none".

Path: `<ticket-reviews-path>/<KEY>-review.md`, with the ticket reviews path from `docs/PROJECT_CONTEXT.md`
`## Documentation layout` (`docs/reviews/` when none is set). For a plain request, `{branch-slug}-review.md`.

````markdown
# <KEY or branch slug>: <summary>

Level: <LEVEL> - <reason> - Last reviewed: <YYYY-MM-DD HH:mm UTC>
Sources: <ticket URL and status | user request and date | brainstorm decision brief>
<!-- Where sources conflict, apply `## Requirement source precedence` and put the resolution under Decisions. -->

## Summary

<What changes and why, in at most five lines, including what users will see differently.>

## Decisions to confirm

| # | Decision | Recommendation | Alternatives | Why |
|---|---|---|---|---|
| D1 | <a choice that changes the code> | <option> | <other options> | <evidence - file:line or source> |

## Open questions

<!-- Blocking first. A blocking question names who answers it (docs/STAKEHOLDERS.md); a non-blocking one names the
     default the plan uses until someone answers. -->

- [NEEDS CLARIFICATION: <question> - blocks: <what> - ask: <stakeholder>]
- [ASSUMPTION: <default and why> - revisit if: <signal>]

## Acceptance criteria

<!-- Binding. Each is observable, says how to check it, and names its source. Cover the edge cases that matter here
     (empty, missing, concurrent, unauthorized), or name them under Non-goals. A rule that shapes a value - rounding, a
     minimum, a cap - gets its own AC with an example at the edge where it decides the result. -->

- AC1: <behavior> - check: <command -> expected result | what a reviewer finds in the diff> [ticket AC1]
- AC2: <behavior> - check: <...> [user <YYYY-MM-DD>]
- AC3: <behavior> - check: <...> [D1]

<!-- Only when the ticket specifies any: the data and environment the checks need, so tasks and tests use them. -->
Test data and setup: <accounts, values, scenarios, environments> [source]

## Approach

<One paragraph: where the change lands, what it reuses, how data flows. Add a mermaid diagram only for a flow that is
hard to follow in words.>

## Scope

- In: <what this change covers>
- Non-goals: <what it leaves alone - why, or where that is handled>
- Constraints: <what the work must respect - why - source>

## Risks and security

<!-- Only when there are any: the risk, its evidence, and what in the plan guards it. -->

- <risk> - <evidence> - guarded by: <AC, task, or constraint>

## Affected areas

- `<path>:<lines>` - <what changes> - must keep working: <callers, file:line>

## Visual references

<!-- Only when the ticket has images. -->

| Image | What I see | What the ticket expects | Gap |
|---|---|---|---|

## Task breakdown

| # | Task | Serves | Depends on | Produces |
|---|---|---|---|---|
| 001 | <imperative summary> | AC1, AC2 | none | `<signature>` |

<!-- EPIC: group the tasks into PRs, one per phase, each one safe to merge on its own. -->
````
