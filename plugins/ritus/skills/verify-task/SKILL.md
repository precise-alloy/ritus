---
name: verify-task
description: Independently check an implemented Ritus task against its acceptance criteria, in a fresh context that did not write the code - use after execute-task (normally as a freshly started subagent), or when asked to verify a task file or debug case file. Read-only apart from build, test, lint, and a spot check it undoes.
argument-hint: Task file path and the implementer's report
---

# Verify Task

Authors grade their own work generously; that is why this runs in a context that did not write the change. Establish
from the repository, and from commands you run yourself, whether the task is done. The implementer's report tells you
where to look, not what is true.

If this context wrote the change, say so and stop: a verdict from the author's context is not independent.

## What to establish

1. **Every acceptance condition holds.** Prove each with `file:line` evidence or a command you ran, compared against
   the expected result in the task. What you cannot prove is not met. An example in an acceptance line is one case of
   its rule, and code can pass the example yet break the rule. So for each line that states a rule - a value, a limit,
   a refusal, a format, a set of cases - run its example, then at least one input the rule covers that the example
   doesn't: another value or position, the other side, the input just past the edge, a second input that must be
   refused. Read the rule from the line and from the source the task quotes - a review comment, the ticket text in its
   Goal, a case file's Symptom and Affected paths: a line can be narrower than the words it came from, and a case the
   source plainly covers that fails is a FAIL, quoted with the source.
2. **The contract held.** Constraints satisfied; non-goals untouched; `Produces` signatures exist exactly as written
   in the real API or tree (including generated code); `Consumes` used as given.
3. **The change is the task's change.** Read the whole working tree (`git status`, including untracked files), not
   just the files in the report. Earlier tasks of the same plan may still be uncommitted: their files belong to their
   task files, not to scope creep. Flag edits that neither this task nor an earlier one accounts for. New tests, docs
   named by the task, and appends to `exploration.md` are expected; changes to existing tests are checked in step 5.
   Inside the files, look for code the task doesn't need (`engineering.md` "Build what the task asks"): an option or
   parameter no caller passes, an abstraction with one implementation, a dependency the task doesn't name. Show it with
   a search for its callers. It is a FAIL when it adds behavior no acceptance line covers - nothing checks that
   behavior - and a note under Scope otherwise.
4. **It meets the done bar.** Run build, test, and lint from `docs/PROJECT_CONTEXT.md`, then the task's own commands.
   An unconfigured command is reported as skipped, never as passed. Apply "Done means" and the change-type rows of
   `skills/shared/standards/engineering.md`, `testing.md` to the tests, every extra standard passed in the dispatch
   input, and every check in `security.md` when the change hits one of its triggers. Extra standards add checks; they
   do not relax this skill's read-only rule.
5. **The tests would catch a regression.** Read the diff of every existing test file: a deleted or skipped test, a
   loosened or removed assertion, or an expected value changed to what the code now returns needs a reason the task or
   plan gives - without one it is a FAIL, whatever the suite reports. Then run the spot check in `testing.md`
   "Checking someone else's tests", aimed where a gap hides: set the breaks the implementer named against the
   acceptance lines whose check is a test, and break a part of a line that no named break, and no assertion you can
   point to, covers. A probe shows the behavior works now; only an assertion keeps it working. A break no test catches
   is a FAIL against the test standard, and its acceptance line is not met.
6. **The docs it names are updated,** including a QA file when it names one - checked against
   `skills/ticket-review/templates/qa-files.md`.

Other task shapes: in an older task file, DONE WHEN and VERIFY are the acceptance, STEPS are decisions already made,
and CONTEXT files plus DOC UPDATE paths are the expected scope. In a debug case file (`investigation-*.md`), the
Regression Test is the acceptance and the Proposed Fix is the decision.

## What this is not

This is not the review of the whole change - `pr-review` does that once: how the tasks fit together, callers outside
this task, the security sweep, edge cases no rule speaks to. Probe the rules this task states; don't invent new ones.
A defect is one you can name, run, and show wrong - against a rule the task or its source states, or wrong on any
reading: a crash, lost or corrupted data. That is a FAIL. Behavior no rule covers goes under `Outside the task` in the
report, not into the verdict: failing it would send the executor to build what nobody asked for.

## Gotchas

- Re-run commands instead of trusting pasted output, including your own from an earlier check: a fix can break what
  passed before.
- A PASS resting on an unrun check is worse than a FAIL: it cancels the fix loop that would have caught the problem.
- Green tests are weak evidence when the new tests would also pass on the old code.
- A refusal is proven by the state after it as well as by the error: check that nothing was written or moved.
- A changed signature, return type, or nullability can break callers the build does not see - dynamic code,
  reflection, templates, config. Search for them.
- Stay read-only apart from build, test, lint, and the spot check's break, which you undo right after its run. Run
  probes on throwaway state - a temp directory or the project's test helpers - never the project's own data. A fix
  you make yourself would go unverified.

## Report

```text
VERIFY: PASS | FAIL
Acceptance:
- [x] <condition> - <evidence>; asserted by: <test:line for each part, when the check is a test>; probe: <input past the example> -> <result>
- [ ] <condition> - NOT MET: <gap + evidence>
Contract: ok | <violation - evidence>
Scope: ok | <path or code - what no task accounts for, with the search that shows it unused>
Standards: ok | <gate - what fails, file:line>
Commands: build <result> | test <N passed, M failed> | lint <result> | task checks <results>
Tests: <break you made> -> caught by <test> | NOT CAUGHT: <break> | weakened: <test - what changed>, one per line
Defects: none | <file:line - input -> actual vs expected>
Outside the task: none | <input -> what happens; no rule the task or its source states covers it>
```