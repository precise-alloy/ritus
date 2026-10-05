# Task file template

Write each task for a capable engineer who has never seen this conversation: they get this file and the docs it
links, nothing else. Anything the user said that changes the work - a constraint, a rejected approach, a name - goes
in here, usually under Constraints or Decisions already made. Pin what must not drift - acceptance, interfaces,
constraints, non-goals - and leave the *how* to the executor unless the plan already decided it. Drop sections that
would only say "none".

```markdown
# Task NNN: <imperative summary>

Level: SIMPLE | STANDARD | EPIC - Depends on: <NNN | none> - Plan: <approved plan path | none>
Status: todo <!-- the main thread sets implemented, then verified, as the run goes; a new session resumes from it -->
<!-- EPIC only --> Memory: docs/memory/{branch-slug}-{feature-slug}-context.md

## Goal

<The outcome in 1-3 sentences, plus why it matters when that is not obvious.>

## Acceptance

<!-- Binding. Each line is observable and says how to check it; the independent check re-runs every command. -->

- [ ] <behavior> - `<command>` -> <expected output or exit code>
- [ ] <behavior> - diff: <what a reviewer should find, where>
- [ ] <a rule that shapes a value: rounding, a minimum, a cap> - `<command>` -> <the value at the edge where it decides>
- [ ] <new logic / bug fix> - `<test command>` fails before the change, passes after

## Constraints

<!-- Only what this task must respect beyond project-wide rules, each with its reason. -->

- <invariant> - because <reason>

## Interfaces

<!-- Exact signatures shared with sibling tasks, so names and types cannot drift. -->

- Consumes: `<signature>` (from task NNN)
- Produces: `<signature>` (used by task NNN)

## Non-goals

- <what not to build or touch> - <why, or where it is handled instead>

## Starting points

<!-- Where the work likely lands, with evidence. A map, not a whitelist. -->

- `<path>:<lines>` - <what is there and what changes>
- Pattern: <docs/ARCHITECTURE.md pattern name>

## Decisions already made

<!-- Plan decisions the executor must follow. Include code only for a detail that is easy to get wrong. -->

## Docs

- `<doc path>` - <what to update>
<!-- QA mode "task" only --> QA: `<task-name>.qa.md` (template: `skills/ticket-review/templates/qa-files.md`)
```

A SIMPLE task usually needs only Goal, Acceptance, and Starting points.

A fix task - written when verify or review findings go to a new executor - needs a Goal naming the findings, one
Acceptance line per finding (the input that failed now gives the expected result) plus build and test, and Starting
points at each finding's `file:line`. Keep it next to the task it fixes, named per the project's task naming.
