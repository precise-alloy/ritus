# Changelog

All notable changes to the Ritus plugin, newest first. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).
The UI companion, ritus-frontend, has its own changelog: [docs/RITUS_FRONTEND_CHANGELOG.md](./docs/RITUS_FRONTEND_CHANGELOG.md).

## [3.0.0]

3.0.0 rewrites the skills for current models: 14 skills instead of 22, each stating its goal and the reasons behind
its rules rather than a script of steps, with fewer stops for approval and the same floor for risky changes. Your
profiles, docs, and a run already in progress keep working. The comparison with 2.1.2 is in
[evals/RESULTS.md](./evals/RESULTS.md#212-vs-300).

### Upgrading from 2.x

1. Run `/setup` once, or accept the offer `/start-ritus` makes. It keeps every value already in your profiles and adds
   the routing block described under [Installation](./README.md#plugin-recommended) - without it, the planning,
   debugging, and review skills rarely start on their own.
2. If you invoked a removed skill directly, see [Removed](#removed) below: planning starts with `ticket-review` now,
   and the standards are docs the workers read on their own, with nothing to invoke.
3. Companion manifests are read when task files are written and when the driving TODO is built. Companions can now load
   standards at task generation, `verify-task`, `pr-review`, and `wrap-up` (see
   [docs/COMPANION_PLUGINS.md](./docs/COMPANION_PLUGINS.md)); a dispatched step still goes no earlier than
   `after task-generation`. Move an integration that names `triage` or `requirement-analysis` to one of those points:
   sizing and analysis take no companion steps.
4. Delete `.ritus/scripts/` if it is still in the project. Since 2.0.4 the scripts live in the plugin
   (`plugins/ritus/scripts/`) and are no longer copied into consuming projects.
5. The plugin source now lives in `plugins/ritus/`; marketplace installs pick it up on update with nothing to do.
6. Model routing is gone: every subagent runs on the session model, or whatever your tool is set to use for
   subagents. `/setup` drops the `model_routing` key from `docs/profiles/runtime.yml` and the `## Model routing`
   section from `docs/PROJECT_CONTEXT.md`; until you run it, the agents ignore both.

### Changed

- **One approval per run.** The plan and the task breakdown are approved together; an EPIC gets a second approval once
  its task files exist. A TRIVIAL change - one obvious edit that adds no logic - needs none.
- **SIMPLE changes run inline.** The main thread implements the one task, and the `pr-review` subagent re-runs its
  acceptance commands in place of `verify-task`.
- **"Just do it" lowers the level,** except for changes in the risk areas
  `plugins/ritus/skills/shared/levels.md` lists, which never go below STANDARD. "Full process" raises it.
- **Plans lead with the decisions** that need you and the blocking questions, then the summary, acceptance criteria,
  and task breakdown.
- **Task files are contracts** - goal, acceptance, constraints, non-goals - with a `Status` line, so a run can resume
  after a restart. Task files written by 2.x still work; `/start-ritus` judges their progress from the diff.
- **`debug` writes a case file** (`investigation-*.md`) that serves as the fix's task file. A fix that adds no logic
  goes straight in; any other waits for your approval.
- **`pr-review` reports only defects it can demonstrate,** each with its cause. A clean review is a valid result;
  concerns it can't demonstrate go under Questions.
- **Tests are checked, not just run.** The executor names the break each new test catches and never weakens an
  existing test to get green; `verify-task` and `pr-review` read the diff of existing tests and break the key logic
  once to confirm a test fails. `verify-task` also names the assertion behind each part of an acceptance line that a
  test must check, and breaks a part nothing guards: a part no test catches leaves the line unmet. Add your mutation
  tool to `docs/TEST_CONVENTIONS.md` if you run one.
- **Each rule is probed past its example.** `verify-task` runs an acceptance line's example, then an input the rule
  covers that the example doesn't, and checks the change against the review comment or ticket text the task quotes.
  Behavior no rule covers is noted for `pr-review`, not failed.
- **Built to the task, not beyond it.** The executor stops when the acceptance is met and names extras as follow-ups;
  an unused option, a single-use abstraction, or an unrequested file or dependency is a `scope` finding, blocking when
  it adds behavior no test covers.
- **`setup` detects before it asks,** and **`wrap-up` drafts the PR description.**
- **Companion discovery** skips a Claude Code version folder marked `.orphaned_at`, so a replaced companion version no
  longer shows in the registry next to the current one.

### Removed

| 2.x                                          | 3.0.0                                                                                                     |
|----------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| `triage`                                     | `ticket-review` sizes the change; the levels are in `plugins/ritus/skills/shared/levels.md`                      |
| `requirement-analysis`                       | The analysis subagent `ticket-review` dispatches for STANDARD and EPIC, briefed by `plugins/ritus/skills/ticket-review/references/analysis-brief.md` |
| `task-generation`                            | `ticket-review` writes the task files once the plan is approved (`plugins/ritus/skills/ticket-review/references/task-generation.md`, `plugins/ritus/skills/ticket-review/templates/task.md`) |
| `code-conventions`, `definition-of-done`     | `plugins/ritus/skills/shared/standards/engineering.md`                                                           |
| `testing-policy`, `tdd`                      | `plugins/ritus/skills/shared/standards/testing.md`                                                               |
| `security`                                   | `plugins/ritus/skills/shared/standards/security.md`                                                              |
| `plugins/ritus/skills/ticket-review/templates/review-document.md` | `plugins/ritus/skills/ticket-review/templates/plan.md` - the plan keeps its path in your project       |
| `plugins/ritus/skills/pr-review/templates/finding-types.md`       | `plugins/ritus/skills/pr-review/references/findings.md`                                                |

## Earlier versions

Versions before 3.0.0 have no changelog. Their history is in the git tags `v1.0.0` to `v2.0.5` and the commit log.
