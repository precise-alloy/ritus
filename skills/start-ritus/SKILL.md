---
name: start-ritus
description: Use when starting any conversation — establishes skill routing and golden rules for the workflow, requiring Skill tool invocation before ANY response including clarifying questions
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task (verify-task, pr-review, or execute-task), skip this skill entirely.
Run only the skill you were dispatched to execute.
</SUBAGENT-STOP>

<EXTREMELY-IMPORTANT>
If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill.

IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.

This is not negotiable. This is not optional. You cannot rationalize your way out of this.
</EXTREMELY-IMPORTANT>

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

After identifying the user's intent and before starting work, create a TODO list with the planned workflow steps.
This makes the plan visible to both you and the user, and prevents steps from being silently skipped.

**Skip for TRIVIAL tasks** — a single-step fix doesn't need a TODO.

For all other intents, create a TODO list based on the skill chain. Examples:

For a new requirement:
```
- [ ] Classify the requirement (triage)
- [ ] Analyze and generate task files (ticket-review)
- [ ] Present tasks for user approval
```

For a bug report:
```
- [ ] Investigate root cause (debug — 4 phases)
- [ ] Fix and verify
- [ ] Run pr-review
- [ ] Promote exploration.md entries to target docs
```

Mark each item as you complete it. The detailed execution TODO (per-task implementation) is created later by
ticket-review after the user approves the task files.

## Skill invocation

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

Parallel vs sequential grouping is determined by `ticket-review`'s execution plan. When in doubt, run sequentially.

## Standards (auto-loaded by execute-task and verify-task — not invoked directly)

| Task touches | Auto-load skill |
|-------------|----------------|
| Any code change | `code-conventions` |
| Auth, billing, migrations, tenant isolation, infra, shared contracts | `security` |
| New service, endpoint, worker, or bug fix | `testing-policy` |
| New business logic, new API endpoint, or bug fix | `tdd` |
| STANDARD or EPIC task | `definition-of-done` |

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

1. **Process skills first** (brainstorm, debug, triage) — these determine HOW to approach the task
2. **Implementation skills second** (execute-task, ticket-review) — these guide execution
3. **Standard skills alongside** (code-conventions, testing-policy, tdd, security, definition-of-done) — these are loaded by the implementation skill when applicable

## Output format

Subagents report using the output format defined in the `execute-task` skill.
