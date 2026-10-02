# Ritus eval harness

This directory is a maintainer reference for the benchmark harness used while rewriting Ritus 3.0.0. It is not part of the installed plugin. Re-running the full benchmark requires a working Copilot CLI setup, local session logs, and the same kind of access the author used.

## Prerequisites

- Copilot CLI with a readable session store and, for collection, the corresponding session `events.jsonl`.
- Node.js 22 or later for the TinyLedger fixture projects.
- Git, including `git archive`, to build plugin arms from repository refs.
- Python 3 with PyYAML installed.
- Bun for the plugin's own TypeScript scripts.
- The external `skill-creator` skill checkout for aggregation and review-viewer scripts.


## Results

- [Evaluation results](RESULTS.md) - the 2.1.2 vs 3.0.0 comparison round behind the 3.0.0 release, per scenario group; its scrubbed summary files are in `results/v2-vs-v3/`.

## Layout

- `harness/` contains the build, collection, grading, judging, usage, contamination, scoring, publishing, trigger, static-check, generator, validation, peek, and smoke scripts.
- `fixture/` contains TinyLedger base files, layers, scenarios, mutants, reference tests, stubs, trigger queries, and the iteration-15 design note.
- `install/` contains a marketplace install/update checker. It creates throwaway marketplaces and CLI homes, installs or updates Ritus through Copilot CLI and Claude Code, and verifies that the installed plugin contains only `.claude-plugin`, `hooks`, `scripts`, `skills`, and `templates`.
- `workspace/` is created locally for generated runs, judge bundles, temporary arm copies, and generated viewers. It is git-ignored.

## Configuration

Every machine-specific value is supplied at run time. Flags override environment variables. An arm spec is either `dir:<path>` for a plugin directory or `git:<ref>` for a repository ref. For `git:<ref>`, the harness reads the `ritus` entry's `source` from that ref's marketplace manifest and archives that path. Put local values in an ignored `evals/.env.local` or pass them in the shell; do not commit them.

### Shared harness flags and environment

| Setting | Flag | Environment variable | Default | Used by |
| --- | --- | --- | --- | --- |
| Harness workspace | `--workspace <dir>` | `RITUS_EVAL_WORKSPACE` | `evals\workspace` | all harness scripts that read generated runs |
| Arm source | `--arm <name>=<spec>` | none | `old_skill=git:fcbd5d5`, `new_skill=dir:<repo>\plugin` | `build.py`, `smoke.py`, `trigger.py` |
| Copilot session events directory | `--session-dir <dir>` | `RITUS_EVAL_SESSION_DIR` | none; required for event collection | `build.py collect`, `collect-all`, `usage.py` main-thread timing, `contamination.py` |
| Copilot session store database | `--session-store <file>` | `RITUS_EVAL_SESSION_STORE` | current user's Copilot session store | `usage.py` |
| Copilot session id | `--session-id <id>` | `RITUS_EVAL_SESSION_ID` | none; required for usage collection | `usage.py` |
| skill-creator checkout | `--skill-creator <dir>` | `RITUS_EVAL_SKILL_CREATOR` | none | aggregation/viewer steps |

### Harness script-specific flags

| Script | Command | Flags | Notes |
| --- | --- | --- | --- |
| `build.py` | `round --show <name>` | - | Prints a named round's scenarios, arms, run count and reporting groups. |
| `build.py` | `build` | `--round`, `--iteration`, `--runs`, `--evals`, `--arms` | Builds run directories and agent briefs. `--round v2-vs-v3` selects the 2.1.2-vs-3.0.0 scenario set, arms, groups and default run count. `--arms` selects arm names to run; `--arm <name>=<spec>` configures their sources. A scenario that reads a PR through the remote helper (`p4`) gets its own copy of each arm whose `scripts/remote-api.ts` is the canned PR #12 stub in `fixture/stubs/`; other scenarios use the plain copies. |
| `build.py` | `collect` | `run_dirs...` | Collects named run directories; uses `--session-dir` for event-backed main-thread evidence. |
| `build.py` | `collect-all` | `--iteration` | Collects every run under the iteration. |
| `build.py` | `turn` | `run`, `--n`, `--kind approval|review|question|final|quiz|other` | Records a scripted main-thread turn. |
| `build.py` | `cleanup` | `--iteration` | Removes generated agent roots and plugin arm copies for an iteration. |
| `grade.py` | direct | `--iteration` | Writes each run's `grading.json`. |
| `judge.py` | `bundle` | `--iteration`, `--groups` | Writes blind judge bundles; `--groups` rebuilds only selected comma-separated groups. For the iteration of a named round, each round scenario is bundled once, in the latest group that judged it, so it gets its latest ground truth. |
| `judge.py` | `merge` | `--iteration` | Merges judge JSON back into `judge-results.json`. |
| `usage.py` | direct | `--iteration`, `--session` | `--session` is a deprecated alias for `--session-id`. |
| `contamination.py` | direct | `--iteration`, `--session-dir` | Writes `contamination.json`: runs whose agent, or a subagent it started, loaded a skill through the Copilot `skill` tool (the installed plugin's copy, not the arm's; failed calls are listed but don't count), read a path outside its world and arm copy, or searched with no path; also launches the runtime refused for its concurrent-agent limit. |
| `scores.py` | direct | `--iteration`, `--workspace`, `--round` | Writes `scores.json` and `scores.md` with run counts, outcome and process pass rates, and mean tokens and seconds per run, per arm, round group and scenario. When the iteration has a `contamination.json`, every table comes twice: all runs, then the clean runs without the flagged ones. With `--round`, groups and scenarios use that round's order. Without `--round`, unmarked scenarios are skipped and ordering is the matching known round's order, then first appearance in known round key lists, then alphabetical. |
| `publish.py` | direct | `--iteration`, `--name` | Copies the iteration's `benchmark.json`, `benchmark.md`, `analyst.json` and `scores.md` into `results/<name>/`, with repository, home and temp paths, the user name, world and arm-copy names, and ids replaced by placeholders; ticket keys stay. Writes nothing if machine data is left. |
| `trigger.py` | `project` | shared flags | Builds the shared trigger-eval TinyLedger project and private plugin copies. |
| `trigger.py` | `run` | `--target-arm`, `--runs`, `--ids`, `--workers`, `--variant` | Runs Claude Code trigger probes. Use `--target-arm` to select the arm; use shared `--arm <name>=<spec>` to configure sources. |
| `trigger.py` | `variant` | `name` | Creates a project variant such as `routing`, `routing2`, `setupblock`, or `setupblock2`. The setupblock variants read `skills/setup/templates/agent-routing.md` from the `new_skill` plugin copy. |
| `trigger.py` | `summary` | `--variant` | Summarizes trigger results. |
| `peek.py` | direct | `names...`, `--lines` | Shows the latest saved turn file for run agent names. |
| `static_check.py` | direct | positional `legacy_plugin_root`, `--plugin-root`, `--repo-root` | Defaults to checking `<repo>\plugin` while reading root `README.md`. |
| `smoke.py` | direct | shared flags | Parses scenarios, runs the static check, builds one worker and one main-thread world, and verifies both default arms. |

### Trigger authentication and model environment

`trigger.py` no longer commits the author's Vertex settings. It passes through existing `CLAUDE_*`, `ANTHROPIC_*`, and `CLOUD_ML_*` environment variables to Claude Code, excluding `CLAUDECODE` and `CLAUDE_CODE_ENTRYPOINT`. Set `RITUS_EVAL_TRIGGER_MODEL` and `RITUS_EVAL_TRIGGER_EFFORT` to add `--model` and `--effort`; leave them unset to use the CLI defaults.

### Install checker flags and environment

Run `python evals\install\check_install.py` to exercise local path and smart-HTTP git marketplace installs and updates for both CLIs. After pushing a layout change, maintainers run `python evals\install\check_install.py --github <owner/repo> --github-ref <branch>` to repeat the GitHub update case.

| Flag or environment | Meaning | Default |
| --- | --- | --- |
| `--copilot <command>` | Copilot CLI executable or shim. | `copilot` |
| `--claude <command>` | Claude Code executable or shim. | `claude` |
| `--old-ref <ref>` | Git ref used as the pre-3.0 old install. | `fcbd5d5` |
| `--git-http-backend <path>` | Explicit `git-http-backend` path for the smart-HTTP test server. | auto-detect |
| `--github <owner/repo>` | Enable the post-push GitHub marketplace update case. | off |
| `--github-ref <branch-or-ref>` | Ref used by the GitHub update case; required with `--github`. | none |
| `--keep` | Keep throwaway work directories for debugging. | off |
| `ProgramFiles` | Used only to find Windows `copilot.cmd` or `copilot.ps1` shims. | platform value |
| `LOCALAPPDATA` | Used only to clear Copilot's marketplace cache for this marketplace before checks. | platform value |
| inherited environment | The checker sets throwaway `COPILOT_HOME` and `CLAUDE_CONFIG_DIR`; other inherited variables are passed to subprocesses. | current shell |

## Running a round

1. Check the fixture and arm builder:
   `python evals\harness\smoke.py`
2. Build runs:
   `python evals\harness\build.py build --iteration 1 --runs 3 --evals e1,e2 --arms old_skill,new_skill`
   The named comparison round can be inspected and built with:
   `python evals\harness\build.py round --show v2-vs-v3`
   `python evals\harness\build.py build --round v2-vs-v3 --iteration 26 --runs 3`
3. Launch each run agent using the `kickoff` from its `setup.json`. Main-thread scenarios also need their scripted developer replies recorded.
4. Record main-thread turns as they happen:
   `python evals\harness\build.py turn <run-or-agent-name> --n 1 --kind approval`
5. Collect completed worker or main-thread runs:
   `python evals\harness\build.py collect-all --iteration 1 --session-dir <session-state-dir>`
6. Grade automatic checks:
   `python evals\harness\grade.py --workspace evals\workspace --iteration 1`
7. Build blind judge bundles:
   `python evals\harness\judge.py bundle --workspace evals\workspace --iteration 1`
8. Run judges, saving their JSON to the paths named inside each bundle.
9. Merge judge results:
   `python evals\harness\judge.py merge --workspace evals\workspace --iteration 1`
10. Add token and timing usage:
    `python evals\harness\usage.py --workspace evals\workspace --iteration 1 --session-id <id> --session-store <store>`
11. Flag runs that loaded a skill or read a file from outside their arm and world:
    `python evals\harness\contamination.py --workspace evals\workspace --iteration 1 --session-dir <session-state-dir>`
12. Write split outcome/process scores, with clean tables when step 11 flagged runs:
    `python evals\harness\scores.py --workspace evals\workspace --iteration 1`
13. Aggregate benchmark summaries from the skill-creator checkout, then generate the review viewer from that same checkout.
14. Write the iteration's `analyst.json` (the reading of the numbers), add its notes to `benchmark.json`, and publish the summary:
    `python evals\harness\publish.py --workspace evals\workspace --iteration 1 --name <results-folder>`
15. Clean generated agent roots and arm copies:
    `python evals\harness\build.py cleanup --workspace evals\workspace --iteration 1`

The generated `review.html` viewer and all raw run data belong under `workspace/`; they are intentionally ignored.

## Limits

The harness is a reproducible reference for maintainers, not a portable product test suite. It depends on a Copilot CLI environment with accessible session logs and a compatible session store.
