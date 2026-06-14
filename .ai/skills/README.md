# skills/ — Module interface summaries

Each file = condensed interface for one module.
Agents read these instead of scanning source on every task.

## Format (keep under 150 lines)

```markdown
# <module> — Interface Summary
_Last updated: YYYY-MM-DD_
_Stack: <language/framework>_

## Exports / API surface
- FunctionName(params): ReturnType — description

## Key types
- TypeName — description

## Patterns & constraints
- rule or constraint specific to this module

## Files
- path/to/entry.ts — what it does
```

## When to create
After first time a module is worked on.

## When to update
When executor emits `SKILL_STALE: <module> — <what changed>`.

## When adopting workflow into existing project
Existing skill files are NEVER overwritten — only appended.
