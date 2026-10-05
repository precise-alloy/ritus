# Task generation

How the main thread turns an approved plan into task files. Each task file is the executor's whole brief and the
verifier's checklist: the executor starts without this conversation, and the verifier holds the work to what the file
says. A task that leans on something only the conversation knows gets built wrong, or failed for doing what the user
allowed.

## Breakdown

- **One task per logical change that leaves the build and tests green**, so each task's diff can be checked as a unit.
- **Merge** edits that one engineer would make together in one module. **Split** when a part can't be designed until
  another part exists, or when a part is risky enough to deserve its own check.
- **In order, one at a time.** Tasks share a working tree, so they run in the order written - producers before
  consumers. There are no parallel groups.
- Place the files in `docs/tasks/{branch-slug}/`, whatever an older `Tasks path convention` in
  `docs/PROJECT_CONTEXT.md` says: resuming, verification, and wrap-up all look there. Never write into another
  branch's task folder. Name them `NNN-<name>.md`, with the ticket ID in the name when the traceability policy in
  `## Team conventions` asks for it.

## Writing each task

Use `skills/ticket-review/templates/task.md`. What makes a task file work:

- **Acceptance** lines are tagged with the plan AC they serve - `[AC2]` - and each says how to check it: a command and
  its expected result, or what a reviewer should find in the diff. Use the plan's test data where it has some.
- **A rule that shapes a value gets its own Acceptance line** - rounding, a minimum or a cap, a limit, a precision, an
  ordering - with an example at the edge where the rule decides the result: "`computeFee(1050, 'transfer')` -> 11
  (half-up)", not a round amount that any rule passes. Tests follow Acceptance: in testing, every executor tested each
  behavior its task's Acceptance named, and none tested the half-up rounding that sat only under Constraints.
- **Constraints** carry what the user said that binds this task, with its source.
- **Interfaces** give exact signatures. A `Consumes` must match its sibling's `Produces` character for character, or
  the second executor builds against a function that doesn't exist.
- **Starting points** come from the analysis - `file:line` and what changes there. They are a map, not a whitelist.
- **Decisions already made** carry the plan's decisions for this task. Write code only for a detail that is easy to get
  wrong.

## Docs each task updates

Name a doc only when the change affects how future people or agents understand, navigate, or safely change the
system. Each column is a file under `docs/`:

| Change | CUTOFF | ARCHITECTURE | DECISIONS | LESSONS | QA file |
|---|---|---|---|---|---|
| Bug fix | | | | if the cause is a pattern others will repeat | per QA mode |
| New endpoint | yes | | | | per QA mode |
| New module | yes | yes | optional | | per QA mode |
| New architecture pattern or decision | | yes | yes | | per QA mode |
| Config or env change | yes | | optional | | |
| Refactor with no contract change | | | | | per QA mode |
| Auth, error handling, or build changed | | | yes | | |

A plan decision already logged as `[DECISIONS]` in `exploration.md` reaches `docs/DECISIONS.md` through wrap-up; don't
also list it under a task's Docs.

## QA files and EPIC memory

- **QA files** follow `skills/ticket-review/templates/qa-files.md`. The QA mode is in `## Team conventions`; when it
  is absent, QA is off, and SIMPLE tasks never get one. For an EPIC that needs a closing QA summary, name it under the
  last task's Docs, to be written from the memory file's QA section.
- **EPIC memory** follows `skills/ticket-review/templates/epic-memory.md`. Create it with the task files; the main
  thread keeps its State, Tasks, and Next current as tasks pass - and its QA section, when QA is on - so a new session
  can pick the work up from it.

## Check the set before presenting it

- Every plan AC is covered by at least one Acceptance line, and every task serves an AC, a constraint, or a
  prerequisite - nothing unrequested.
- Every rule that shapes a value has an Acceptance line with an example at its edge.
- Every `Consumes` matches a `Produces` exactly: names, parameters, return types.
- Every Starting points path exists, or is marked new.
- No placeholders in the binding sections - no `TBD`, "handle errors", or "similar to task 2".
- Every task names its commands and their expected results.

Fix what fails before presenting the set: the user approves it as written, and the verifier checks against exactly
what it says.
