---
name: debug
description: Use when investigating bugs, test failures, or unexpected behavior - 4-phase investigation with evidence grading before any fix. TRIGGER - invoke when user mentions bug, broken, failing, error, crash, not working
argument-hint: Provide the symptom, exact error/log output, reproduction steps, recent changes, and any linked ticket URL/key
---

# Debug

**Core principle:** Understand before you fix. Guessing at fixes is slower than systematic investigation - every
failed guess adds noise and delays the real fix.

## When to use

Any bug, test failure, unexpected behavior, or issue investigation. Load this skill BEFORE proposing fixes.

**Especially** when under time pressure, when a "quick fix" is tempting, when prior fixes have failed, or when the
issue isn't fully understood.

When starting debug, create this TODO - **every item below, verbatim** (never a single item named after the skill) - and mark items done as you complete them:

TODO:

```markdown
- [ ] Phase 1: Root cause investigation
- [ ] Phase 2: Pattern analysis
- [ ] Phase 3: Hypothesis and testing
- [ ] Phase 4: Present the proposed fix - get user approval, then classify the fix (TRIVIAL vs SIMPLE+)
- [ ] TRIVIAL: apply the fix inline, self-verify with build + test, report to the user - done
- [ ] SIMPLE+: write the case file, load `dispatch.md`, then apply the fix - dispatch execute-task subagent
- [ ] SIMPLE+: verify the fix - dispatch verify-task subagent
- [ ] SIMPLE+: run pr-review - dispatch pr-review subagent
- [ ] SIMPLE+: if pr-review approves - invoke wrap-up
```

## Iron law

**NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST.**

Phase 1 must complete before any fix is proposed. Violating this wastes more time than following it.

## Phase 1: Root Cause Investigation (hard gate - must complete before Phase 2)

**If the bug is linked to a ticket** (a URL/key was provided or is named in the symptom), fetch it first via
`remote-api-access.md` in the `shared` skill directory - the single mechanism for fetching ticket data (it
auto-detects the provider). Pull the reported symptom, reproduction steps, expected-vs-actual behavior, comments, and
any attached screenshots or logs to ground the investigation. Treat it as *reported* context, not confirmed fact -
reproduce and confirm the actual behavior yourself (1.2), and grade a ticket claim no higher than Hypothesized until
you verify it. Skip this when no ticket is involved.

### 1.1 Read error messages carefully

- Stack traces, line numbers, file paths, error codes - read them, don't skim.
- Copy the exact error message. Note the exact file and line.

### 1.2 Reproduce consistently

- Determine exact triggering steps.
- Is it 100% reproducible or intermittent?
- If not reproducible, gather more data - do not guess.

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
2. Trace backward through the call chain - where did this value come from?
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

## Phase 2: Pattern Analysis (hard gate - must complete before Phase 3)

### 2.1 Find working examples

- Locate similar functioning code in the same codebase.
- Is there a reference implementation that works correctly?

### 2.2 Compare against references

- Read the working code line by line.
- What does the working code do differently?

### 2.3 Identify differences

Catalog every difference between working and broken code - no matter how small. Document each.

### 2.4 Understand dependencies

Map: required components, settings, configuration, environment, assumptions.

---

## Phase 3: Hypothesis and Testing (hard gate - must complete before Phase 4)

### 3.1 Form single hypothesis

- Clearly stated, specific, written down.
- "The bug occurs because X does Y when Z" - not "something is wrong with the auth."

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

<what is actually wrong and why - cite file:line>

## Evidence

- <finding 1> - Grade: Confirmed - `file:line`
- <finding 2> - Grade: Deduced - follows from finding 1
- <finding 3> - Grade: Hypothesized - needs verification

## Attempted Fixes (if any)

| # | What was tried | Result |
|---|---|---|
| 1 | <description> | Failed - <why> |

## Proposed Fix

<what should change and where - becomes the STEPS in the task file>

## Regression Test

<test that would have caught this - becomes part of DONE WHEN>
```

For a **SIMPLE+ fix this case file is required** - it is the task artifact the dispatched execute-task and verify-task
consume, reading its `Proposed Fix` as the STEPS and its `Regression Test` as the DONE WHEN. A **TRIVIAL fix skips it**:
that fix is applied inline with no dispatch (Phase 4), so there is no worker to hand an artifact to, and the commit
message captures the root cause.

---

## Phase 4: Approve the fix, then route by size

**Present the proposed fix to the user and wait for approval before any change is applied.** The user may approve,
adjust the approach, or ask for alternatives - proceed only after the user explicitly approves.

Once approved, route the fix by its size (the same TRIVIAL / SIMPLE+ criteria `triage` uses):

- **TRIVIAL** (single file, no public-contract change, clear validation, low blast radius) - apply the fix inline in
  this session, then self-verify with build + test and report to the user. The commit message captures the root
  cause; no case file and no dispatch are needed.
- **SIMPLE+** (anything larger) - write the investigation case file, then hand it to a dispatched `execute-task`
  subagent; you investigated, so a fresh context applies the fix and another fresh context (verify-task) checks it.
  The case file is the task artifact it consumes: `Proposed Fix` is the STEPS, `Regression Test` is the DONE WHEN.
  execute-task writes the failing test and applies the single fix red-green (it loads `tdd` for bug fixes);
  verify-task then verifies it independently. Your job here ends at handing the case file to the dispatch, per the TODO.

### Escalation - when the fix loop can't converge

The verify → fix cycle runs through the dispatch (verify FAIL → `execute-task` → re-verify), bounded by the circuit
breaker in `dispatch.md`. When that breaker trips - the same finding recurs, or several cycles pass without a clean
state - treat it as an architectural problem, not another fix attempt. Signs: each fix reveals new issues elsewhere,
the fix needs massive refactoring, or it creates new symptoms.

**Action:** stop the loop and discuss with the user. Write a `DECISION-NNN` entry to `docs/DECISIONS.md` capturing the
architectural finding - what was discovered, why the current approach fails, and what alternatives to consider.

---

## Exploration log

Create `docs/tasks/{branch-slug}/exploration.md` if it doesn't exist, using the header format from
`skills/ticket-review/templates/exploration.md`. Before starting, read the full log to avoid re-discovering prior work; during investigation, append codebase findings per the exploration template (append-only; flag every entry).

## Common rationalizations - STOP and return to Phase 1

| Excuse | Reality |
|---|---|
| "Let me just try this quick fix" | Quick fixes without root cause create more bugs than they solve |
| "It's a simple bug" | Simple bugs don't need guessing - they need reading. Process is fast for simple bugs. |
| "We're under time pressure" | Systematic debugging is FASTER than guess-and-check. Every failed guess wastes more time. |
| "I'll fix first, investigate later" | You'll fix the symptom and miss the cause. The bug will return. |
| "I can bundle these fixes" | You won't know which one worked. One variable at a time. |
| "It's probably X" (without evidence) | "Probably" is not evidence. Trace the data flow. |
| "I can see the symptom so I know the cause" | Symptoms mislead. The error at line 42 may originate at line 7. |
| "This fix should work" (3rd+ attempt) | Stop. This is no longer a bug - it's an architectural problem. Escalate. |

---

## Output

After the investigation phases and the approval gate, the skill produces one of:

- **TRIVIAL** - the fix applied inline and self-verified (build + test); the commit message captures the root cause.
- **SIMPLE+** - an investigation case file (`docs/tasks/{branch-slug}/investigation-{slug}.md`, the fix's task
  artifact) plus the approved fix dispatched to `execute-task` and checked by verify-task, per the TODO.

## Handoff

- **Report:** the root cause and the outcome. For a **TRIVIAL** fix - applied inline and self-verified (build + test);
  the user decides on committing. For a **SIMPLE+** fix - the approved proposed fix, report only; it is applied by the
  dispatched execute-task subagent, and the user decides on committing.
- **TODO update:** a **TRIVIAL** fix has nothing to dispatch - the round ends after the inline fix + self-verify. For a
  **SIMPLE+** fix the gates run next - `Apply the fix - dispatch execute-task subagent`, then
  `Verify the fix - dispatch verify-task subagent`, then `Run pr-review - dispatch pr-review subagent`, then
  `invoke wrap-up` once pr-review approves. The **investigation case file** is the task artifact those gates consume -
  its `Proposed Fix` is the STEPS and its `Regression Test` is the DONE WHEN; the fix's execute-task and verify-task
  both read it as the task file.
