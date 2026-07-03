---
name: start-ritus
description: Use when starting any conversation — establishes skill routing and golden rules for the workflow, requiring Skill tool invocation before ANY response including clarifying questions
argument-hint: Provide the user's request so the router can choose the next applicable skill
---

> **Subagent guard:** If you were dispatched as a subagent to execute a specific task (verify-task, pr-review, or execute-task), skip this skill entirely.
> Run only the skill you were dispatched to execute.
>
> **Mandatory skill check:** Before responding to any task — including clarifying questions — check whether an available skill applies. If a skill covers your task, you **must** invoke it via the Skill tool. Do not skip this check. This is not optional.

# Ritus

> Source of truth: this skill + workflow skills. Project data: `docs/PROJECT_CONTEXT.md`.
> User behavioral rules: CLAUDE.md / copilot-instructions.md (override workflow defaults).

## Instruction priority

1. User's explicit instruction in the current conversation
2. Primary rules (CLAUDE.md / copilot-instructions.md)
3. Project context (`docs/PROJECT_CONTEXT.md`)
4. Active skill instructions
5. This skill (workflow defaults)

## Golden rules (defaults — primary rules can override)

1. Classify before loading context — triage first.
2. Minimal change — no unsolicited refactors.
3. Grep before edit — confirm paths exist before touching files.
4. No hallucinated features — if unclear, stop and ask.
5. Stop on errors — compile fail, test fail, 4xx/5xx.
6. Grep before claiming — cite `file:line` when asserting facts about existing code.

## Workflow tracking

**MANDATORY:** Every workflow skill creates its TODO as the **first action** before any work begins. The TODO lists
the skill's internal steps with the chain to the next skill as the last item. Mark items as you complete them.
This ensures you never stop mid-chain and never skip steps in long context windows.

**Skip for TRIVIAL tasks** — a single-step fix doesn't need a TODO.

### Expected workflow chains (reference only — each skill creates its own TODO)

- **Requirement with ticket:** triage → ticket-review → user approval → execute + verify → pr-review → wrap-up
- **Exploratory question:** brainstorm → triage → ticket-review → user approval → execute + verify → pr-review → wrap-up
- **Bug report:** debug (4 phases) → pr-review → wrap-up
- **PR review feedback:** address-feedback → execute + verify → [pr-review re-check] → wrap-up → local commit (human pushes)

## Skill invocation

> **Terminology:** "Invoke" = trigger a skill via the Skill tool (user or system action). "Load" = a skill reading another skill's content as a companion standard (skill-to-skill action).

Before starting work, check which skill matches the user's intent by reading the available skill descriptions.
Invoke the matching skill via the Skill tool. Each skill's `## Next` section defines what happens after — follow
it, do not pre-plan the full chain.

## Subagent configs

The **orchestrating session** is whatever agent loaded start-ritus — typically the main conversation session.
When a skill says to dispatch, spawn a **fresh subagent** and instruct it to load the target skill.
Never use a skill name as the agent type — skill names are not agent types.

| Subagent | Model | Effort | Key constraints |
|----------|-------|--------|-----------------|
| `execute-task` | per triage | per triage | Implement STEPS exactly; do not redesign |
| `verify-task` | haiku | medium | Read-only except build/test/lint; never fix; never trust implementer claims |
| `pr-review` | sonnet | high | Adversarial; never apply fixes; use `origin/` refs; default to "Request changes" |
| `address-feedback` | per triage | per triage | Fetch PR comments, generate fix task, dispatch execute-task; never push |

Parallel vs sequential grouping is determined by `ticket-review`'s execution plan. When in doubt, run sequentially.

## Red flags — stop and check for applicable skills

These thoughts mean STOP — you're rationalizing:

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

1. **Process skills first** (brainstorm, debug, triage, address-feedback) — these determine HOW to approach the task
2. **Implementation skills second** (execute-task, ticket-review) — these guide execution
3. **Standard skills alongside** (code-conventions, testing-policy, tdd, security, definition-of-done) — these are loaded by the implementation skill when applicable

## Output format

Each subagent reports using the output format defined in its own skill (`execute-task`, `verify-task`, `pr-review`, etc.).
