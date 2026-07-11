---
name: start-ritus
description: Use when starting any conversation - establishes skill routing and golden rules for the workflow, requiring skill invocation before ANY response including clarifying questions
argument-hint: Provide the user's request so the router can choose the next applicable skill
---

> **Subagent guard:** If you were dispatched as a subagent to run a worker skill per `skills/shared/dispatch.md` (verify-task, pr-review, execute-task, or requirement-analysis), skip this skill entirely.
> Run only the skill you were dispatched to execute.
>
> **Mandatory skill check:** Before responding to any task - including clarifying questions - check whether an available skill applies. If a skill covers your task, you **must** invoke it via your platform's skill mechanism. Do not skip this check. This is not optional.

# Ritus

> Source of truth: this skill + workflow skills. Project data: `docs/PROJECT_CONTEXT.md`.
> User behavioral rules: CLAUDE.md / copilot-instructions.md (override workflow defaults).

## Instruction priority

1. User's explicit instruction in the current conversation
2. Primary rules (CLAUDE.md / copilot-instructions.md)
3. Project context (`docs/PROJECT_CONTEXT.md`)
4. Active skill instructions
5. This skill (workflow defaults)

## Golden rules (defaults - primary rules can override)

1. Classify before loading context - triage first.
2. Minimal change - no unsolicited refactors.
3. Grep before edit - confirm paths exist before touching files.
4. No hallucinated features - if unclear, stop and ask.
5. Stop on errors - compile fail, test fail, 4xx/5xx.
6. Grep before claiming - cite `file:line` when asserting facts about existing code.

## Workflow tracking

**MANDATORY:** When a core workflow skill (brainstorm/triage/ticket-review/requirement-analysis/execute-task/verify-task/pr-review/address-feedback/wrap-up/comprehension/debug) is invoked, its **first action** - before any work - is to create a todo list containing **every step in that skill's own `TODO:` block, copied verbatim**, ending with the handoff to the next skill. Mark items done as you go. This ensures you never stop mid-chain and never skip steps in long context windows.

**Never collapse a skill into one todo item** (e.g. a single `Brainstorm: <task>` item) and **never build a one-item-per-skill chain checklist.** Each invoked skill contributes its own full list of steps; the chain advances because a skill's last step invokes the next skill, which then creates its own step list.

**Skip for TRIVIAL tasks** - a single-step fix doesn't need a TODO.

### Expected workflow chains (reference map only - NOT a todo template; each skill creates its own step TODO)

- **Requirement with ticket:** triage → ticket-review → user approval → execute + verify → pr-review → wrap-up → comprehension
- **Exploratory question:** brainstorm → triage → ticket-review → user approval → execute + verify → pr-review → wrap-up → comprehension
- **Bug report:** debug (investigate + approve fix) → execute + verify → pr-review → wrap-up → comprehension
- **PR review feedback:** address-feedback → execute + verify → [pr-review re-check → wrap-up → comprehension]

## Skill invocation

> **Terminology:** "Invoke" = trigger a skill via your platform's skill mechanism (user or system action). "Load" = a skill reading another skill's content as a companion standard (skill-to-skill action).

Before starting work, check which skill matches the user's intent by reading the available skill descriptions.
Invoke the matching skill via your platform's skill mechanism. Each skill's `## Handoff` section defines what it returns and its TODO
update - follow it, do not pre-plan the full chain.

## Dispatch

The dispatch contract - the spawn-then-invoke rule, how a "dispatch `<skill>` subagent" TODO item runs, fix-task creation, the circuit
breaker, and per-worker run config (model / effort / tools) - lives in `skills/shared/dispatch.md`. Load it before
walking a driving TODO. It is the single source; worker skills never load it, keeping dispatch out of subagents.

Shared reference docs under `skills/shared/` (e.g. `dispatch.md`, `remote-api-access.md`) are static within a session.
Load each the first time you need it and reuse it from context afterward - when a shared doc is already in your context,
work from that copy instead of re-reading it.

## Red flags - stop and check for applicable skills

These thoughts mean STOP - you're rationalizing:

| Thought | Reality |
|---------|---------|
| "This is just a simple question" | Questions are tasks. Check for skills. |
| "I need more context first" | Skill check comes BEFORE clarifying questions. |
| "Let me explore the codebase first" | Skills tell you HOW to explore. Check first. |
| "I can check git/files quickly" | Files lack conversation context. Check for skills. |
| "This doesn't need a formal skill" | If a skill exists, use it. |
| "I remember this skill" | Skills evolve. Read current version. |
| "The skill is overkill" | Simple things become complex. Use it. |
| "I'll just do this one thing first" | Check BEFORE doing anything. |
| "I know how to debug this" | Use the `debug` skill. It prevents confirmation bias. |

## Skill priority

When multiple skills could apply, use this order:

1. **Process skills first** (brainstorm, debug, triage, address-feedback) - these determine HOW to approach the task
2. **Implementation skills second** (execute-task, ticket-review) - these guide execution
3. **Standard skills alongside** (code-conventions, testing-policy, tdd, security, definition-of-done) - these are loaded by the implementation skill when applicable

## Output format

Each subagent reports using the output format defined in its own skill (`execute-task`, `verify-task`, `pr-review`, etc.).
