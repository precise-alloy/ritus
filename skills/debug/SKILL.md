---
name: debug
description: Use when investigating bugs, test failures, or unexpected behavior — 4-phase investigation with evidence grading before any fix. TRIGGER — invoke when user mentions bug, broken, failing, error, crash, not working
argument-hint: Provide the symptom, exact error/log output, reproduction steps, and recent changes
---

# Debug

**Core principle:** Understand before you fix. Guessing at fixes is slower than systematic investigation — every
failed guess adds noise and delays the real fix.

## When to use

Any bug, test failure, unexpected behavior, or issue investigation. Load this skill BEFORE proposing fixes.

**Especially** when under time pressure, when a "quick fix" is tempting, when prior fixes have failed, or when the
issue isn't fully understood.

## Iron law

**NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST.**

Phase 1 must complete before any fix is proposed. Violating this wastes more time than following it.

## Phase 1: Root Cause Investigation (hard gate — must complete before Phase 2)

### 1.1 Read error messages carefully

- Stack traces, line numbers, file paths, error codes — read them, don't skim.
- Copy the exact error message. Note the exact file and line.

### 1.2 Reproduce consistently

- Determine exact triggering steps.
- Is it 100% reproducible or intermittent?
- If not reproducible, gather more data — do not guess.

### 1.3 Check recent changes

```bash
git log --oneline -20
git diff HEAD~5
```

- What changed recently? New dependencies? Config changes? Environment changes?

### 1.4 Gather evidence at component boundaries

For multi-component systems (API chains, CI pipelines, layered services):

- Add diagnostic logging at each layer boundary.
- Run once to identify the failing boundary.
- Focus investigation at that boundary.

### 1.5 Trace data flow

For errors deep in the call stack, trace backward from the bad value to its origin:

1. Find where the bad value is used (the symptom).
2. Trace backward through the call chain — where did this value come from?
3. At each step, verify: is the value correct here? If yes, move one step forward. If no, move one step backward.
4. The point where the value goes from correct to incorrect is the root cause location.

**Fix at source, not at symptom.**

### Evidence grading

As you investigate, grade each finding:

| Grade | Meaning | Criteria |
|-------|---------|----------|
| **Confirmed** | Verified with evidence | Reproducible, observed in logs/debugger, cited with `file:line` |
| **Deduced** | Logically follows from confirmed evidence | Not directly observed but follows from confirmed findings |
| **Hypothesized** | Suspected but unverified | Plausible theory, needs testing |

---

## Phase 2: Pattern Analysis (hard gate — must complete before Phase 3)

### 2.1 Find working examples

- Locate similar functioning code in the same codebase.
- Is there a reference implementation that works correctly?

### 2.2 Compare against references

- Read the working code line by line.
- What does the working code do differently?

### 2.3 Identify differences

Catalog every difference between working and broken code — no matter how small. Document each.

### 2.4 Understand dependencies

Map: required components, settings, configuration, environment, assumptions.

---

## Phase 3: Hypothesis and Testing (hard gate — must complete before Phase 4)

### 3.1 Form single hypothesis

- Clearly stated, specific, written down.
- "The bug occurs because X does Y when Z" — not "something is wrong with the auth."

### 3.2 Test minimally

- Smallest possible change to test the hypothesis.
- One variable at a time.
- Never bundle multiple fixes into one test.

### 3.3 Evaluate

- If hypothesis confirmed → proceed to Phase 4.
- If hypothesis rejected → form a new hypothesis. Do NOT layer additional fixes.

### 3.4 When you don't know

Admit it. Ask for help. Research. Do not pretend to understand.

---

## Investigation case file

After Phase 1-3, produce `docs/tasks/{branch-slug}/investigation-{slug}.md`:

```markdown
# Investigation: <issue summary>

Date: <YYYY-MM-DD>
Status: investigating | root-cause-found | fix-verified | escalated

## Symptom

<exact error, behavior, or failure observed>

## Root Cause

Grade: Confirmed | Deduced | Hypothesized

<what is actually wrong and why — cite file:line>

## Evidence

- <finding 1> — Grade: Confirmed — `file:line`
- <finding 2> — Grade: Deduced — follows from finding 1
- <finding 3> — Grade: Hypothesized — needs verification

## Attempted Fixes (if any)

| # | What was tried | Result |
|---|---|---|
| 1 | <description> | Failed — <why> |

## Proposed Fix

<what should change and where — becomes the STEPS in the task file>

## Regression Test

<test that would have caught this — becomes part of DONE WHEN>
```

For SIMPLE+, this case file is referenced in the task file's CONTEXT section. For TRIVIAL, it's optional — commit
message captures the root cause.

---

## Phase 4: Fix and Verify

**Present the investigation case file and proposed fix to the user and wait for approval before applying any
changes.** The user may approve, adjust the approach, or ask for alternatives. Do NOT proceed until the user
explicitly approves.

### 4.1 Create failing test case

Write a test that reproduces the bug. Must fail before the fix, pass after. Reference the `testing-policy` skill for
test conventions.

### 4.2 Apply a single fix

Fix the root cause directly. One fix, one variable. Do not bundle improvements or "while I'm here" refactoring.

After applying the fix:

1. Run the failing test — it must now pass.
2. Run the full test suite — no regressions.
3. Run the build — it must succeed.

If the fix fails, return to Phase 3 with new information. Form a new hypothesis. Do NOT layer additional fixes on top.

### 4.3 Escalation gate — 3 failed fixes

If 3 fix attempts have failed, **stop**.

This is no longer a bug — it's likely an architectural problem. Signs:

- Each fix reveals new issues elsewhere.
- Fix requires massive refactoring.
- Fix creates new symptoms.

**Action**: stop fixing. Document findings. Discuss with the user before any further attempts. The architecture may
need to change, not the code.

Write a `DECISION-NNN` entry to `docs/DECISIONS.md` documenting the architectural finding — what was discovered,
why the current approach fails, and what alternatives should be considered.

---

## Exploration log

During investigation, append codebase findings to `docs/tasks/{branch-slug}/exploration.md` per the exploration
template. Read the log first to avoid re-discovering what prior agents already found.

## Common rationalizations — STOP and return to Phase 1

| Excuse | Reality |
|---|---|
| "Let me just try this quick fix" | Quick fixes without root cause create more bugs than they solve |
| "It's a simple bug" | Simple bugs don't need guessing — they need reading. Process is fast for simple bugs. |
| "We're under time pressure" | Systematic debugging is FASTER than guess-and-check. Every failed guess wastes more time. |
| "I'll fix first, investigate later" | You'll fix the symptom and miss the cause. The bug will return. |
| "I can bundle these fixes" | You won't know which one worked. One variable at a time. |
| "It's probably X" (without evidence) | "Probably" is not evidence. Trace the data flow. |
| "I can see the symptom so I know the cause" | Symptoms mislead. The error at line 42 may originate at line 7. |
| "This fix should work" (3rd+ attempt) | Stop. This is no longer a bug — it's an architectural problem. Escalate. |

---

## Output

After completing all four phases, the skill produces:

1. **Investigation case file** — `docs/tasks/{branch-slug}/investigation-{slug}.md`
2. **The fix itself** — applied, tested

## Next

Report the fix: root cause, what changed, and test results. Do NOT commit — the user decides when to commit.

After the fix is verified, dispatch a fresh subagent (model: haiku, effort: medium) to run the `verify-task` skill for
adversarial review of the changes.
