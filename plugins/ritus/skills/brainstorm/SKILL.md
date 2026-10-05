---
name: brainstorm
description: Think a problem through before it becomes a plan - use when the user is unsure what to build, weighing options or approaches, asking "how should we approach...", comparing pros and cons, or wants a design challenged. Interviews one question at a time, grounds the options in the code, and ends with a decision brief.
argument-hint: The idea, problem, or design question, plus any constraints you already know
---

# Brainstorm

Turn an open question into a decision someone can plan from. The usual failures are opposite: building the first
idea that came up, and a comparison where the "alternatives" are strawmen set up to lose. A vague request planned as
is gets sized wrong and built twice.

## 1. Understand the problem

Ask one question at a time, multiple choice where it fits, each with the default you would pick. Learn the problem
behind the requested solution, what success looks like, the constraints (performance, compatibility, time, team),
and what was already tried. Stop asking once the next answer wouldn't change the options.

## 2. Ground it in the code

Read what the options would touch: the entry points, the existing patterns, what could be reused. Every option names
real files and patterns; an option that only exists as architecture on a whiteboard can't be sized.

## 3. Lay out the options

Two or three genuine options, recommended first:

- **What** - one line, and how it works in this codebase, citing `file:line`.
- **Effort** - small, medium, or large, with its rough shape ("3 files", "new module and a migration").
- **Risk** - what could go wrong: breaking changes, performance, migration.
- **Reversibility** - easy to undo, or a one-way door.

If only one option survives, say what you checked that ruled the others out.

## 4. Look for the blind spots

Before the user chooses, check what all the options assume, where they fail at the edges - volume, concurrency,
partial failure, the risk areas in `skills/shared/levels.md` - who else they affect (`docs/STAKEHOLDERS.md`), and what
would change your recommendation. Put what you find next to the option it hurts.

## 5. Decide

Wait for the user's choice. Then write the decision brief in chat:

```markdown
Problem: <what is being solved, and for whom>
Decision: <the chosen option>
Why not the others: <one line each>
Constraints: <what the user said that the plan must respect>
Open questions: <what is still unknown, and who can answer>
```

## When not to

- The request is already clear - "add a login endpoint with JWT": go to `ticket-review`.
- Something is broken: `debug`.

## Output

The decision brief, then an offer to plan it: `invoke ticket-review` with the brief as the requirement once the user
says to plan, or right away if they asked for a plan from the start. Picking an option is not that - people often
brainstorm only to decide, and a plan, with its analysis of the code, is work they may not want yet.
