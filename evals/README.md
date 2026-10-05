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
| Arm source | `--arm <name>=<spec>` | none | `old_skill=git:fcbd5d5`, `new_skill=dir:<repo>\plugins\ritus` | `build.py`, `smoke.py`, `trigger.py` |
| Copilot session events directory | `--session-dir <dir>` | `RITUS_EVAL_SESSION_DIR` | none; required for event collection | `build.py collect`, `collect-all`, `usage.py` main-thread timing, `contamination.py` |
| Copilot session store database | `--session-store <file>` | `RITUS_EVAL_SESSION_STORE` | current user's Copilot session store | `usage.py` |
| Copilot session id | `--session-id <id>` | `RITUS_EVAL_SESSION_ID` | none; required for usage collection | `usage.py` |
| Shared web fixture install | `--web-modules <dir>` | `RITUS_EVAL_WEB_MODULES` | `evals\workspace\web-modules` | `build.py`, `smoke.py`, UI checks |
| Figma stub request log | none | `FIGMA_STUB_LOG` | none | `figma_stub.mjs` |
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
| `build.py` | `web-modules` | `--web-modules` | Installs the shared TinyLedger Web browser tooling. |
| `build.py` | `environment` | `--iteration`, `--guidance-skill`, `--playwright-mcp`, `--note`, `--web-modules` | Writes `environment.json` for a frontend round and verifies the installed guidance skill matches the fixture. |
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
| `static_check.py` | direct | positional `legacy_plugin_root`, `--plugin-root`, `--repo-root` | Defaults to checking `<repo>\plugins\ritus` while reading root `README.md`. |
| `smoke.py` | direct | shared flags | Parses scenarios, runs the static check, builds one worker and one main-thread world, and verifies both default arms. |

### Trigger authentication and model environment

`trigger.py` no longer commits the author's Vertex settings. It passes through existing `CLAUDE_*`, `ANTHROPIC_*`, and `CLOUD_ML_*` environment variables to Claude Code, excluding `CLAUDECODE` and `CLAUDE_CODE_ENTRYPOINT`. Set `RITUS_EVAL_TRIGGER_MODEL` and `RITUS_EVAL_TRIGGER_EFFORT` to add `--model` and `--effort`; leave them unset to use the CLI defaults.

### Install checker flags and environment

Run `python evals\install\check_install.py` to exercise local path and smart-HTTP git marketplace installs and updates for both CLIs. After pushing a layout change, maintainers run `python evals\install\check_install.py --github <owner/repo> --github-ref <branch>` to repeat the GitHub update case.

| Flag or environment | Meaning | Default |
| --- | --- | --- |
| `--copilot <command>` | Copilot CLI executable or shim. | `copilot` |
| `--claude <command>` | Claude Code executable or shim. | `claude` |
| `--old-ref <ref>` | Git ref used as an old install source; repeat for multiple refs. | `fcbd5d5`, `a610dc5` |
| `--git-http-backend <path>` | Explicit `git-http-backend` path for the smart-HTTP test server. | auto-detect |
| `--github <owner/repo>` | Enable the post-push GitHub marketplace update case. | off |
| `--github-ref <branch-or-ref>` | Ref used by the GitHub update case; required with `--github`. | none |
| `--keep` | Keep throwaway work directories for debugging. | off |
| `ProgramFiles` | Used only to find Windows `copilot.cmd` or `copilot.ps1` shims. | platform value |
| `LOCALAPPDATA` | Used only to clear Copilot's marketplace cache for this marketplace before checks. | platform value |
| inherited environment | The checker sets throwaway `COPILOT_HOME` and `CLAUDE_CONFIG_DIR`; other inherited variables are passed to subprocesses. | current shell |

## Frontend eval

The frontend eval adds TinyLedger Web, composite Ritus-plus-companion arms, an eval-only Figma stand-in and browser-based UI graders. It is still harness-only: never run a real frontend round from a session that has extra Ritus, ritus-jev, impeccable or frontend-design guidance enabled.

### TinyLedger Web

TinyLedger Web is a no-dependency HTML/CSS/ES-module app served by a small Node dev server. The base app is in `fixture\web\base`; planted bug layers are in `fixture\web\layers`; alternative self-test implementations are in `fixture\web\selftest`; Figma stand-in data, screenshots and the `figma-design-to-code` guidance skill are in `fixture\web\design`. The web scenarios live beside the other scenarios in `fixture\scenarios\u*/`.

| Layer | Bug planted | Checked by |
| --- | --- | --- |
| `card-gap` | total-balance card spacing is 12px instead of the 16px design token | `uv1`, `ui_selftest.py` |
| `card-hex-console` | raw hex color plus a console error | `ur1`, `ui_selftest.py` |
| `transfer-overflow` | transfer page overflows at 375px | `ug1`, `uc1`, `uv2`, `ui_selftest.py` |
| `transfer-nolabel` | visible label points at the wrong input id | `ug1`, `uc1`, `uv3`, `ui_selftest.py` |
| `txn-noempty` | transactions page is missing its empty state | `uv4`, `ui_selftest.py` |

### Shared install

Run `python evals\harness\build.py web-modules` before building web worlds. The install location is resolved as: `--web-modules`, then `RITUS_EVAL_WEB_MODULES`, then `evals\workspace\web-modules`. Each web world gets a `node_modules` junction to that shared install after all fixture files are written; world rebuilds, smoke runs and cleanup remove the junction, not the install.

### Composite arms

Use `--arm name=<ritus>+<companion>`. The Ritus side accepts `dir:<path>` or `git:<ref>`; the companion side accepts `dir:<path>` or `git:<ref>:<path-in-repo>`. Composite copies are laid out as `rp-<hex>\plugins\ritus` and `rp-<hex>\plugins\<companion-name>` so the copied Ritus hook scans only its own companion, not another arm's copy. Main-thread briefs include the registry printed by that arm copy's own hook. `setup.json` records provenance for `ritus` and `companion`: spec, commit, version and tree hash. The arm-copy cache key includes the full arm spec plus the resolved Ritus and companion sources, so a re-pin or `dir:` content change creates a new copy.

### Prior-step artifacts

A scenario that starts mid-workflow receives the documents its own arm would already have produced. `common/` contains Ritus-core docs; `<arm>/` contains companion docs. In Phase 3 the old arm's docs include the figma-intake context marker and e2e-plan spec that 0.2.0 expects. `{{COMPANION}}` is substituted in per-arm `inputs.md` files when a worker must load a companion skill. Phase 4 adds the new arm's companion artifacts.

### Figma stand-in and guidance skill

The stand-in server is `evals\harness\figma_stub.mjs`. It serves file key `TLWEB0001`, node `12:34` (also accepted as `12-34` in URLs), the resource `skill://figma/figma-design-to-code/SKILL.md`, metadata, variables, screenshots and an empty code-connect map. Set `FIGMA_STUB_LOG` to a file path to log requests. Check it with `python evals\harness\figma_stub_check.py`; add `--installed-skill <path>` to compare an installed guidance skill with the fixture after newline normalization.

### UI measurements and self-test

`ui_measure.mjs` drives the web app with Playwright and axe-core. `ui_eval()` starts a copied web tree on an allocated port and runs the measurement script. `ui_verdicts()` turns those measurements into PASS/FAIL facts, and `ui_selftest.py` runs the matrix over the base, planted layers and self-test variants. Read the matrix by verdict name: the base and correct variants should pass the applicable feature checks, while the planted bug row should fail only the intended checks.

### The `frontend-baseline` round

`frontend-baseline` is iteration 27. It builds the old arm only, currently `git:6c03d3a+dir:<repo>\plugins\ritus-frontend`; before a real round, re-pin the companion to `git:<Phase 2 commit>:plugins/ritus-frontend`.

| Key | Class | Scenario | What it measures |
| --- | --- | --- | --- |
| `up1` | system | `eval-70-ui-plan` | UI planning for TLW-22 without design data |
| `ug1` | system | `eval-78-ui-gate` | gate checks find and fix mobile overflow and an unlabeled field |
| `us1` | system | `eval-79-ui-simple-empty` | end-to-end simple empty-state implementation |
| `uc1` | system | `eval-80-ui-check-standalone` | standalone mobile transfer check, a capability baseline |
| `ub1` | step probe | `eval-71-ui-build-design` | building the summary card from Figma node `12:34` |
| `uv1` | step probe | `eval-72-ui-verify-gap` | verify-task names the measured card spacing bug |
| `uv2` | step probe | `eval-73-ui-verify-overflow` | verify-task names mobile overflow |
| `uv3` | step probe | `eval-74-ui-verify-label` | verify-task names the unassociated label |
| `uv4` | step probe | `eval-75-ui-verify-empty` | verify-task names the missing empty state |
| `uv5` | step probe | `eval-76-ui-verify-clean` | verify-task passes clean UI without false defects |
| `ur1` | step probe | `eval-77-ui-review-hex-console` | pr-review requests changes for raw color and console error |

### Setting up a frontend round

1. **Pin and commit.** Commit the harness and fixtures. Re-pin the round companion to `git:<Phase 2 commit>:plugins/ritus-frontend`.
2. **Open a dedicated session** in this repository.
3. **Disable conflicting plugins and skills** for the round: installed Ritus, ritus-jev and impeccable plugins, plus any user skill that bears on frontend work, for example `frontend-design`. A skill load other than `figma-design-to-code` flags the run.
4. **Add two MCP servers** for the round, and remove them after. VS Code's current documentation says workspace `.vscode\mcp.json` uses a top-level `servers` object; the portable `.mcp.json` and Copilot portable user config use `mcpServers`. For VS Code format, the definitions are:

   ```json
   {
     "servers": {
       "playwright": {
         "type": "stdio",
         "command": "npx",
         "args": [
           "@playwright/mcp@0.0.78",
           "--isolated",
           "--caps=testing",
           "--allowed-origins",
           "http://localhost:*",
           "--output-dir",
           "<a folder under %TEMP%>"
         ]
       },
       "figma": {
         "type": "stdio",
         "command": "node",
         "args": ["<repo>\\evals\\harness\\figma_stub.mjs"]
       }
     }
   }
   ```

   In portable format, put the same two server objects under top-level `mcpServers` instead of `servers`. In the Copilot app, use the **MCP servers** setting; no app-specific file path is documented here. In the round session, verify that `browser_*` tools and `get_design_context` are listed.
5. **Install the guidance.** Copy `evals\fixture\web\design\figma-design-to-code\` as the user skill `figma-design-to-code`, then remove it after the round. In the Copilot app, user skills live in `%USERPROFILE%\.agents\skills\`; do not write there from the harness. This is required because this host exposes MCP tools but not MCP resources, and 0.2.0 blocks without the guidance.
6. **Record and build.** Run `python evals\harness\build.py web-modules`, then `python evals\harness\build.py environment --iteration <n> --guidance-skill <path> --playwright-mcp "npx @playwright/mcp@0.0.78 --isolated --caps=testing --allowed-origins http://localhost:* --output-dir <a folder under %TEMP%>" --note "<model, host app and settings>"`, then build the round.
7. **Run one run at a time,** every arm, with one model and one setting set throughout. After each run's collection, close the Playwright MCP browser with `browser_close` before the next run. The session's single MCP browser serves every subagent, so pages and console state would otherwise carry over.
8. **Finish** as for other rounds: collect, grade, judge, then run `contamination.py` and `scores.py`.

### Reading results

System-level groups carry the comparison because each arm reaches UI checks at different workflow points. Step probes are reported apart: 0.2.0 checks UI at blocking gates before pr-review, while 1.0 loads a standard into execute-task, verify-task and pr-review.

### Final comparison

Phase 5 reruns 0.2.0 next to 1.0 in one session set up exactly as above. A deployment-profile benchmark, where each arm gets its own recommended environment, is not part of this comparison.

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

The harness is a reproducible reference for maintainers, not a portable product test suite. It depends on a Copilot CLI environment with accessible session logs and a compatible session store. On Windows, deep `--workspace` paths can push generated web worlds past the 260-character path limit; keep workspaces short, for example under `evals\workspace\`.
