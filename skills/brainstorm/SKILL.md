---
name: brainstorm
description: Use when requirements are vague or exploratory — proposes 2-3 approaches with tradeoffs before triage. TRIGGER — invoke when user says "explore", "what should we build", "what are our options", "compare approaches", "pros and cons", "how should we approach this", "I'm not sure how to do this", or any open-ended design question
argument-hint: Provide the idea, problem, or design question to explore, plus known constraints
---

# Brainstorm

**Core principle:** Explore before you commit. Never let a vague requirement become a concrete task without
examining at least two genuine alternatives first.

## When to use

When the user's intent is vague or exploratory: "improve performance", "add better auth", "rethink the error handling",
"what should we do about X". These aren't ready for triage — they need exploration first.

**Skip this skill** when the requirement is already clear ("add login endpoint with JWT", "fix the null reference in
UserService"). Go directly to triage.

## Hard gates

1. **Do NOT proceed to triage until the user has approved an approach.** Exploration before commitment.
2. **Do NOT present a single recommendation.** If you can only think of one approach, you haven't explored enough —
   dig deeper into the codebase, question assumptions, or consider the opposite tradeoff. Two genuine alternatives
   is the minimum.

## Process

When starting brainstorm, create this TODO and mark items as you complete them:

TODO:

```markdown
- [ ] Understand the problem (clarifying questions)
- [ ] Explore the codebase
- [ ] Propose 2-3 approaches
- [ ] User picks an approach
- [ ] Classify the chosen approach (invoke triage)
```

### Step 1: Understand the problem

Ask clarifying questions **one at a time**. Focus on:

- What problem are you solving? (not what solution do you want)
- What does success look like?
- What constraints exist? (performance, compatibility, timeline, team size)
- What have you already tried or considered?

Prefer multiple-choice questions when possible — easier to answer than open-ended.

### Step 2: Explore the codebase

Before proposing approaches, ground your thinking in what actually exists:

- Grep for related code, patterns, and existing implementations in the affected area
- Read entry points and key files — understand how the system currently handles related concerns
- Identify dependencies, integration points, and existing patterns the team follows
- Note reusable code that any approach could leverage

Do NOT do a full repo scan. Focused exploration only — but every proposed approach must reference real code paths,
not abstract architecture.

### Step 3: Propose 2-3 approaches

For each approach, present a structured comparison:

- **Name** — one-line summary
- **How it works** — 2-3 sentences grounded in the codebase (reference specific files/patterns found in Step 2)
- **Effort** — small / medium / large, with rough scope (e.g., "3 files, ~200 lines" or "new module + migration")
- **Risk** — what could go wrong? (breaking changes, performance regression, migration complexity)
- **Reversibility** — easy to undo, hard to undo, or one-way door

Lead with your recommended approach and explain why — but give the alternatives genuine consideration, not
strawman options designed to make the recommendation look good.

### Step 4: User picks

Wait for the user to choose. If they want to explore further, go back to Step 1.

If they pick an approach, summarize the chosen direction in 3-5 sentences — this becomes the input context for
triage. Include: what was chosen, why it was chosen over the alternatives, and any constraints that shaped the
decision.

## Output

A brief design note (in chat, not a file) that captures:

1. The problem being solved
2. The chosen approach and why (including why alternatives were rejected)
3. Key constraints or decisions made
4. Any open questions deferred to implementation

This output feeds directly into triage as the requirement description.

## Common rationalizations

| Excuse | Reality |
|---|---|
| "Let me just start coding" | You don't know what to code yet. Code without exploration is rework. |
| "The user said X so let's do X" | Users describe solutions, not problems. Understand WHY — there may be a better way. |
| "There's only one way to do this" | If you can't find an alternative, you haven't explored the codebase enough. |
| "This is too simple to brainstorm" | The user asked an exploratory question. They want exploration, not a shortcut. |
| "Here's option A (recommended) and option B (worse)" | Strawmen waste everyone's time. Present genuine alternatives or admit you need to research more. |

## Next

After the user approves an approach, load `triage` to classify the work. Brainstorm is the one exception to
ritus's "triage first" rule — exploratory requirements need brainstorm before they're clear enough to
classify. Triage's `## Next` section handles the rest of the chain.
