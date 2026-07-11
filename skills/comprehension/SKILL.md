---
name: comprehension
description: Use after wrap-up completes, as the final step before the human commits - brief the human on the change and run an advisory comprehension quiz so they understand what shipped. TRIGGER - invoke after wrap-up (skip for TRIVIAL).
argument-hint: Provide the branch slug and the base branch to diff the change against
user-invocable: false
---

# Comprehension

**Core principle:** Understand the change before you merge. Reading a diff gives only a shallow
picture - much of the behavior depends on existing code paths the diff doesn't show. A short quiz
surfaces what you don't yet understand while it's still cheap to ask.

## When to use

The terminal skill in the workflow chain - invoked by `wrap-up` after it finishes promoting
exploration entries and verifying doc updates, and **before the human commits or merges**.

A single-file, fully-understood fix needs no quiz. If the change diff is empty (nothing to explain), skip gracefully and say so.

This is **advisory, not a gate**: the quiz flags what the human missed, but never blocks the commit.

When starting comprehension, create this TODO - **every item below, verbatim** (never a single item named after the skill) - and mark items done as you complete them:

TODO:

```markdown
- [ ] Gather the change context (diff + DONE WHEN + task files)
- [ ] Brief the human on the change
- [ ] Run the advisory quiz (one question at a time)
- [ ] Report the comprehension summary
```

## Step 1: Gather the change context

Assemble what the human needs to understand:

- **The diff** - `git diff <base>...HEAD` for committed work, or the working tree (`git diff HEAD`)
  if the change is still uncommitted. If the diff is empty, skip to a graceful exit.
- **The task DONE WHEN conditions** - read the task files in `docs/tasks/{branch-slug}/` to recover
  the intended behavior each change was meant to produce.
- **The promoted findings** - if any exploration entries were promoted to `docs/DECISIONS.md` or
  `docs/LESSONS.md` during wrap-up, note the non-obvious decisions they captured.

## Step 2: Brief the human

Before quizzing, give the human the context to succeed. In a few sentences each:

- **What changed** - the files touched and the shape of the change.
- **Why** - the intent behind each change, tied back to the DONE WHEN conditions.
- **Which existing code paths it leans on** - the behavior that isn't visible in the diff (callers,
  shared helpers, config, downstream effects). This is where comprehension gaps hide; cite
  `file:line` when describing existing code.

## Step 3: Run the advisory quiz

Ask **3-5 multiple-choice questions, one at a time**, targeting the non-obvious behavior from Step 2 -
not trivia the diff answers directly.

**Every question must be a higher-order question** - one that tests understanding of a *consequence*,
not recall of a fact. Use these types only:

- **Predict-the-consequence** - "If <input or condition>, what does the change now do?"
- **What-breaks-if** - "What would break if <this line or decision> were changed or removed?"
- **Trade-off rationale** - "Why was <approach A> chosen over <plausible approach B>?"

Do **not** ask definitional or recall questions ("what does X stand for", "which file was added") -
the diff already answers those.

**Option rules - make the wrong answers tempting:**

- Give **4-5 options** per question.
- Every option must be plausible - draw distractors from real misconceptions a reasonable person
  could hold about this change. Keep all options parallel in length, specificity, and tone so the
  correct one is not obvious by shape.
- **Rotate the correct answer's position across the questions** - never default it to the first slot,
  and never mark it as `recommended`. Cycle deterministically (e.g. Q1 -> B, Q2 -> D, Q3 -> A,
  Q4 -> C, Q5 -> B) so the position is never predictable. Before asking, self-check that the correct
  answers are spread across positions, not clustered in one slot.

After each answer:

- Say whether it was right, and fill the gap with a short explanation.
- Ask the next question.

**Advisory only** - never block, never gate the commit, never loop until the human "passes". If they
want to skip the quiz, let them.

## Step 4: Report the comprehension summary

Report to the human:

```text
## Comprehension summary

### Change recap
- <one line per changed area>

### Quiz
- <N> questions asked, <M> answered correctly
- Gaps surfaced: <topics the human missed, or "none">

### You're clear to commit
- Suggested commit: <type(scope): subject>  (from the task COMMIT blocks)
```

## Hard rules

- Advisory, never blocking - the human always decides when to commit.
- Skip for TRIVIAL and for an empty diff.
- Multiple-choice only, 4-5 plausible options - rotate the correct answer's position across questions; never default it to the first slot, never mark it `recommended`.
- Base the briefing and questions on the actual diff and task files - no invented behavior; cite
  `file:line` when describing existing code paths.

## Handoff

- **Report:** the comprehension summary (change recap, quiz result, gaps surfaced, suggested commit).
- Terminal skill - **no TODO update.** The workflow chain ends here; the human commits/merges.
