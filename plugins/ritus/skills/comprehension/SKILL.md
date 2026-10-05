---
name: comprehension
description: Make sure the human understands what shipped before they commit or merge - use after wrap-up, or when the user asks to quiz them, explain this change, or walk them through what was built. Briefs the change, including the existing code it leans on, then runs a short advisory quiz.
argument-hint: The branch or base to diff against, if not the current branch and its base
---

# Comprehension

Help the person who will own this change understand it before they commit. A diff shows what changed, not the
existing callers, shared helpers, and config that decide how it behaves - and that is where the next bug hides. A
short quiz finds the gaps while asking is still cheap. It is advisory: it never blocks the commit.

Skip it for a TRIVIAL change or when nothing changed, and say so.

## 1. Brief

Gather the whole change first. In a Ritus run it is often uncommitted and its new files untracked, so no single
`git diff` shows it: start from `git status --short`, then read `git diff <base>...HEAD` for what is committed,
`git diff HEAD` for the rest, and each untracked file of the change in full. With the task files' Acceptance (DONE
WHEN in older ones) and what wrap-up promoted, say in a few sentences each:

- **What changed** - the files and the shape of the change.
- **Why** - the intent, tied to the acceptance criteria.
- **What it leans on** - the behavior the diff doesn't show: callers, shared helpers, config, downstream effects,
  cited at `file:line`.

## 2. Quiz

Ask 3 to 5 questions, one at a time, about the non-obvious behavior from the brief. Each tests a consequence, not a
fact the diff already states:

- **Predict** - "If <input or condition>, what does the code now do?"
- **What breaks** - "What would break if <this line or decision> changed?"
- **Why this way** - "Why <approach A> rather than <plausible B>?"

Give 4 or 5 options, each a misconception a reasonable person could hold, alike in length and tone so the answer
doesn't stand out by its shape. Rotate the right answer's position across the questions, and never mark one as
recommended. After each answer, say whether it was right and fill the gap in a sentence or two. If the person wants to
skip, stop.

## When the user wants something to keep

On request, write the brief as a single self-contained HTML file - no external assets, a diagram only where the flow
is hard to follow in words. Put it outside the repository unless they say where.

## Output

```text
Comprehension - <branch name>
Changed: <one line per area>
Quiz: <M> of <N> right. Gaps: <topics missed, or none>
Suggested commit: <type(scope): subject>
```

This is the last step of the chain; the human commits.
