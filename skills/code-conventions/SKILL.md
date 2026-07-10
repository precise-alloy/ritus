---
name: code-conventions
description: Loaded automatically by execute-task and verify-task for any code change - covers comments, abstraction limits, dependency rules, and project-specific conventions from docs/CODE_CONVENTIONS.md. Do not invoke standalone unless the user specifically asks about coding conventions
argument-hint: Provide the task or ticket identifier and the files/modules likely to change
user-invocable: false
---

# Code Conventions

## When to use

Auto-loaded by execute-task and verify-task for any code change. Validate against these conventions before reporting
done. If the user asks about conventions directly, invoke this skill standalone.

## Universal principles

### Comments

Write a comment only when WHY is non-obvious: hidden constraint, subtle invariant, specific bug workaround.
Never explain what the code does. Never reference the task, PR, or callers.

### Abstraction limits

- Three similar lines is better than a premature abstraction.
- No helper extraction unless used in 3+ places.
- No feature flags or backwards-compat shims - change the code directly.

### Dependencies

- No circular imports between modules.
- Prefer explicit imports over wildcard/glob imports.

## Project-specific conventions

Read `docs/CODE_CONVENTIONS.md` for this project's conventions: type system, naming, module structure, error handling,
logging, and stack-specific rules. That file is filled by repo-scan and maintained by the team.

Project-specific rules in `docs/CODE_CONVENTIONS.md` override the universal principles above when they conflict.

## Handoff

- **Report:** the standard applied to the parent skill's work.
