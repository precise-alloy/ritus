<p align="center">
  <img src="https://github.com/precise-alloy/.github/raw/main/images/ritus-banner.svg" alt="Ritus Banner" width="2142" style="max-width: 100%; height: auto;" height="500">
</p>

<div align="center">

# Ritus

</div>

Ritus ([/ˈriː.tus/](https://ipa-reader.com/?text=ri%CB%90.tus), pronounced `REE-tus`)  - from Latin, meaning a prescribed rite or procedure.

A disciplined workflow for reliable AI-assisted development. Ritus uses skill-based architecture, on-demand loading,
TODO-driven control flow, chain-based routing, and independent verification to work across Claude Code, GitHub Copilot,
and any language or stack.


---

## Formula

```text
AI Agent Workflow = Primary rules + Core workflow + Project profile + Runtime context
```

| Layer           | File(s)                                           | What it does                                                                                    |
|-----------------|---------------------------------------------------|-------------------------------------------------------------------------------------------------|
| Primary rules   | CLAUDE.md / copilot-instructions.md               | User's behavioral directives - highest authority                                                |
| Core workflow   | Skills (via plugin)                               | On-demand pure-capability skills; the main thread dispatches subagents per `plugins/ritus/skills/shared/dispatch.md` |
| Project profile | `docs/profiles/*.yml` → `docs/PROJECT_CONTEXT.md` | Project facts rendered from YAML data                                                           |
| Runtime context | Current task file + active skill                  | What to work on now                                                                             |

---

## Installation

### Plugin (recommended)

**Claude Code:**

1. Add marketplace
2. Install Ritus

```text
/plugin marketplace add precise-alloy/ritus
/plugin install ritus
```

**GitHub Copilot CLI:**

1. Add the marketplace
2. Fetch the plugin manifest
3. Install Ritus

```text
/plugin marketplace add precise-alloy/ritus
/plugin marketplace browse precise-alloy-marketplace
/plugin install ritus@precise-alloy-marketplace
```

After plugin install, start with:

```text
/start-ritus
```

It checks whether the project is set up, gives a one-screen tour, and hands off to the right skill. To go straight to
setup, run `/setup` (or tell the agent "set up Ritus").

The setup skill scaffolds the project files (`docs/`, `.ritus/.env.example`), then detects what the repository already
answers - the git remote and base branch, manifests, ticket keys in recent commits - and shows each value with where it
came from for you to correct. It asks only what is left, one question at a time with a default, then writes your
project profiles and renders `docs/PROJECT_CONTEXT.md`. It also adds a short routing block to `CLAUDE.md` (Claude Code)
and `AGENTS.md` or `.github/copilot-instructions.md` (Copilot) naming which Ritus skill to start with for a ticket, a
bug, or a review. Without it, models tend to start reading and editing code instead of invoking the skill; the block
sits between `ritus:routing` markers, and setup refreshes only what is between them.

## What gets installed

The `/sync` skill copies template files into your project. Files are never overwritten once they exist.

| Strategy             | Behavior                                    | Files                                                                                                                                                                                                                                               |
|----------------------|---------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **user-owned**       | Created once, you own it - edit freely      | `docs/profiles/project.yml`, `docs/profiles/team.yml`, `docs/profiles/runtime.yml`, `docs/PROJECT_CONTEXT.md`, `docs/ARCHITECTURE.md`, `docs/CODE_CONVENTIONS.md`, `docs/TEST_CONVENTIONS.md`, `docs/DECISIONS.md`, `docs/LESSONS.md`, `docs/CUTOFF.md`, `docs/STAKEHOLDERS.md` |
| **append-only**      | Created once, only appended to              | `docs/CHANGELOG.md`                                                                                                                                                                                                                                 |
| **scaffold**         | Directory placeholder                       | `docs/tasks/README.md`, `docs/memory/README.md`                                                                                                                                                                                                     |
| **project-specific** | Created once, you own it - extend as needed | `.ritus/.env.example`                                                                                                                                                                                                                                      |

Run `/sync check missing` to see what's missing, or `/sync create missing` to create missing files.

Ritus keeps all per-project runtime state under a `.ritus/` directory at the project root: remote API credentials at
`.ritus/.env.local` plus transient scratch such as downloaded attachments. The `/sync` skill adds a managed
`.gitignore` block that lists the runtime files to ignore (`.ritus/.env.local` and `.ritus/attachments/`), so
credentials and scratch stay out of version control while the committed template `.ritus/.env.example` and any other
tracked `.ritus/` files remain in git.

**Note for upgrading projects:** If you previously installed Ritus and have a `.ritus/scripts/` directory in your
project, it can be safely deleted. These scripts now live in `plugins/ritus/scripts/` and are no longer copied
into consuming projects.

For existing codebases, follow up with:

```text
run repo-scan
```

This detects auth patterns, build commands, testing conventions, and coding conventions from your codebase, each with
the file it came from, and writes them once you confirm.

### Upgrading

**Plugin:** updates automatically - skills are replaced. When a new version adds project files, `/sync create missing`
creates them (`/setup` runs it too). Existing user files are never overwritten.

### Upgrading from 2.x to 3.0.0

3.0.0 rewrites the skills for current models: 14 skills instead of 22, each stating its goal and the reasons behind
its rules rather than a script of steps, with fewer stops for approval and the same floor for risky changes. Your
profiles, docs, and a run already in progress keep working.

**After upgrading:**

1. Run `/setup` once, or accept the offer `/start-ritus` makes. It keeps every value already in your profiles and adds
   the routing block described under [Installation](#plugin-recommended) - without it, the planning, debugging, and
   review skills rarely start on their own.
2. If you invoked a removed skill directly, see the table below: planning starts with `ticket-review` now, and the
   standards are docs the workers read on their own, with nothing to invoke.
3. Companion manifests are read when the driving TODO is built, once the plan is approved, so the earliest point a
   companion can name is `after task-generation` (once the task files exist). Move an integration that names `triage`
   or `requirement-analysis` there or later: planning itself no longer takes companion steps.
4. Delete `.ritus/scripts/` if it is still in the project (see the note above).
5. The plugin source now lives in `plugins/ritus/`; marketplace installs pick it up on update with nothing to do.
6. Model routing is gone: every subagent runs on the session model, or whatever your tool is set to use for
   subagents. `/setup` drops the `model_routing` key from `docs/profiles/runtime.yml` and the `## Model routing`
   section from `docs/PROJECT_CONTEXT.md`; until you run it, the agents ignore both.

**Where the removed skills went:**

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

**What behaves differently:**

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

## What gets generated

**By plugin (workflow-owned):**

| Component | What it contains                                               |
|-----------|----------------------------------------------------------------|
| 14 skills | Workflow skills, plus shared standards and templates they read |

**By setup / repo-scan (user-owned in target project):**

| File                       | What it contains                                          |
|----------------------------|-----------------------------------------------------------|
| `docs/PROJECT_CONTEXT.md`  | Always-on project facts (rendered from profiles)          |
| `docs/profiles/*.yml`      | Source of truth - project, team, runtime data             |
| `docs/ARCHITECTURE.md`     | System architecture (header filled, rest progressive)     |
| `docs/CODE_CONVENTIONS.md` | Project-specific coding conventions (filled by repo-scan) |
| `docs/TEST_CONVENTIONS.md` | Project-specific test conventions (filled by repo-scan)   |

---

## Skills

Skills are self-contained SKILL.md files loaded on-demand. Each has YAML frontmatter (name + description) so the
agent scans relevance without loading the full content. Skills are pure capabilities - they describe *what* to do,
not who runs next; the main thread drives them via a TODO and dispatches subagents (inputs, tools, constraints)
using the single contract in `plugins/ritus/skills/shared/dispatch.md`.

### Workflow skills

| Skill                  | Purpose                                                                                |
|------------------------|----------------------------------------------------------------------------------------|
| `start-ritus`          | Front door - checks setup, offers to resume the branch's run, orients new users, hands off to the right skill |
| `brainstorm`           | Think an open question through - one question at a time, 2-3 real options grounded in the code, a blind-spot pass, then a decision brief for `ticket-review` |
| `ticket-review`        | Plan before coding - size the change (TRIVIAL to EPIC), read the code (an analysis subagent for STANDARD/EPIC), write the plan and task files, one approval (EPIC: two) |
| `execute-task`         | Implement one task file against its acceptance criteria; report with evidence          |
| `verify-task`          | Independent per-task check in a fresh context - re-runs the commands itself, probes each acceptance rule past its example, and names the test that guards each part |
| `pr-review`            | Adversarial review of a branch or PR against its plan or ticket, in a fresh subagent; reports only defects it can demonstrate |
| `address-feedback`     | Weigh PR review comments against the code, fix what holds up, draft replies for the rest; one approval, then the user commits and posts |
| `wrap-up`              | Close out an approved run - promote the exploration log into the docs, check the doc updates the tasks promised, draft the PR description |
| `comprehension`        | Brief the human on the change and the existing code it leans on, then a short advisory quiz before commit; an HTML brief on request |
| `debug`                | Root-cause investigation with graded evidence; proposes the fix for approval (a fix that adds no logic goes straight in) |
| `setup`                | Detect-first setup - confirm what the repository shows, ask only the rest, write the profiles and `docs/PROJECT_CONTEXT.md`, add the routing block |
| `sync`                 | Check or create missing project files (docs, profiles, `.ritus/.env.example`) without setup's questions; never overwrites |
| `repo-scan`            | Detect stack, commands, auth, conventions, and module map, with evidence for each value; writes after you confirm |
| `migrate-docs`         | Sort existing notes and docs into the Ritus docs; shows where every section goes before writing |

### Standards (shared docs the workers read, not skills)

| File                                     | Applies when                                                                   |
|------------------------------------------|--------------------------------------------------------------------------------|
| `plugins/ritus/skills/shared/standards/engineering.md` | Any code change - what "done" means, and the few opinions that differ from defaults |
| `plugins/ritus/skills/shared/standards/testing.md`     | Any code change - which tests a change needs, what makes a test count, and how a checker tests the tests |
| `plugins/ritus/skills/shared/standards/security.md`    | Auth, user data, outside input, rendering, URL fetching, secrets or config, billing, migrations, shared contracts |
| `plugins/ritus/skills/shared/standards/writing.md`     | Text people read or post as written - review replies, PR descriptions, entries promoted into the docs |

`execute-task` reads the first three before implementing; `verify-task` and `pr-review` apply them again.
`address-feedback` and `wrap-up` follow `writing.md`. The project's own `docs/CODE_CONVENTIONS.md` and
`docs/TEST_CONVENTIONS.md` win where they disagree.

### Skill chains

```text
Start:                start-ritus → the matching skill (new users, resuming a run, or unsure which fits)
Explore/brainstorm:   brainstorm → ticket-review
Plan/implement:       ticket-review → execute-task → [verify-task per task, STANDARD+] → pr-review → wrap-up → comprehension
Debug/fix:            debug → [TRIVIAL: fix + self-check] | execute-task → [verify-task, STANDARD+] → pr-review → wrap-up → comprehension
Review:               pr-review (fresh subagent) → verdict  (wrap-up only within a task-driven run)
Address feedback:     address-feedback → execute-task → verify-task → [pr-review if a re-review is asked → wrap-up → comprehension]
                      (at SIMPLE the re-review replaces verify-task)
Iterate:              wrap-up → comprehension; then user feedback → ticket-review or brainstorm (new run)
```

---

## Control flow (TODO-driven)

The orchestrating skills build a driving TODO - one item per step, each naming its contract: `invoke <skill>` runs
inline, `dispatch <skill> subagent` runs in a fresh subagent - and the main thread marks each item done as it goes.
This keeps a long-running agent on the rails: it never stops mid-chain, never skips a step, and always shows the
human exactly where it is.

The TODO is the single control surface. Each skill ends by reporting its result, and the main thread applies it to
that TODO:

- **Orchestrators** (`ticket-review`, `address-feedback`, `debug`) create/own the driving TODO and apply TODO updates from worker verdicts.
- **Routing** (`start-ritus`, `brainstorm`, `wrap-up`) direct to the next skill (typically `invoke <skill>`).
- **Workers** (`execute-task`, `verify-task`, `pr-review`) end at their report; the main thread applies the outcome.
- The **analysis agent** is a read-only subagent that `ticket-review` dispatches for STANDARD/EPIC before a plan exists (not a driving-TODO item); the main thread writes the plan and task files from its report.
- The **main thread** owns and walks the TODO top to bottom - dispatching each `dispatch <skill> subagent` item as
  a fresh, independent subagent and running each `invoke <skill>` item inline.

Because the main thread is the only dispatcher, subagents never spawn other subagents - the workflow behaves
identically on Claude Code, GitHub Copilot, or any host, with no nested-subagent support required. The full dispatch
contract lives in one place: [`plugins/ritus/skills/shared/dispatch.md`](./plugins/ritus/skills/shared/dispatch.md).

---

## Daily workflow

```text
Write requirement (or run /start-ritus)
  → ticket-review sizes it: TRIVIAL / SIMPLE / STANDARD / EPIC (plugins/ritus/skills/shared/levels.md)

  TRIVIAL:                Agent implements directly - no plan, no task file, self-verifies
  SIMPLE:
    → ticket-review reads the code, puts a short plan in chat and writes one task file → you approve
    → the main thread implements it (execute-task, inline)
    → pr-review subagent reviews it and re-runs the acceptance commands + build/test
  STANDARD / EPIC:
    → analysis subagent (read-only) reads the code and reports
    → the main thread writes the plan + task breakdown → you approve (EPIC: again once the task files exist)
    → execute-task subagent implements each task, one at a time
    → verify-task subagent (fresh context) checks each task independently
    → pr-review subagent runs adversarial review at ticket level

  If pr-review approves → wrap-up (promote exploration, check doc updates, draft the PR description) → ready for merge/PR
  If pr-review rejects  → fix → re-review (up to 3 cycles, then escalate — dispatch circuit breaker)

  Human:
    → Reviews diff
    → Commits + pushes
    → If PR receives review comments → address-feedback → fix → verify → local commit
    → Or provides follow-up changes → workflow restarts from ticket-review/brainstorm
```

For the full workflow diagram, see [docs/WORKFLOW_DIAGRAMS.md](./docs/WORKFLOW_DIAGRAMS.md).

---

## Repository structure

```text
marketplace.json                 ← Copilot marketplace manifest
.claude-plugin/
  marketplace.json               ← Claude marketplace manifest
package.json                     ← npm package manifest (publishes plugins/ritus/, README.md, LICENSE)
README.md                        ← this file
docs/                            ← repository docs for maintainers; not installed with the plugin
  COMPANION_PLUGINS.md
  WORKFLOW_DIAGRAMS.md           ← visual workflow reference (human-only)
evals/                           ← maintainer-only eval harness and results; not installed with the plugin
plugins/                         ← plugin sources
  ritus/                         ← installed Ritus plugin source
    .claude-plugin/
      plugin.json                ← Claude Code plugin manifest
    templates/.ritus/.env.example ← remote API credentials template (scaffolded as .ritus/.env.example)
    skills/
      start-ritus/SKILL.md       ← front door: setup check, resume, orientation, hand-off
      brainstorm/SKILL.md
      ticket-review/SKILL.md     ← planning hub: size, analyze, plan, approve, task files, driving TODO
        references/              ← analysis brief (read by the analysis subagent), task-generation rules
        templates/               ← plan, task, exploration, QA, EPIC memory templates
      execute-task/SKILL.md
      verify-task/SKILL.md
      pr-review/SKILL.md
        references/              ← review rubric; finding types, severities, and how they set the verdict
      address-feedback/SKILL.md
        templates/skip-reasons.md ← the keep bar and skip categories for review comments
      wrap-up/SKILL.md
      comprehension/SKILL.md
      shared/
        dispatch.md              ← TODO dispatch contract (modes by level, outcomes, resume, models)
        levels.md                ← TRIVIAL / SIMPLE / STANDARD / EPIC, and never-below-STANDARD areas
        remote-api-access.md     ← remote API rules (ticket-review + pr-review + address-feedback)
        standards/               ← engineering, testing, security, and writing standards
      debug/SKILL.md
        templates/case-file.md   ← the investigation case file, which is the fix's task file
      setup/SKILL.md
        references/              ← settings to detect or ask, derived values, PROJECT_CONTEXT rendering
        templates/agent-routing.md ← routing block setup adds to CLAUDE.md / AGENTS.md
      sync/SKILL.md
        script/sync.ts           ← project file scaffolding script
      repo-scan/SKILL.md
      migrate-docs/SKILL.md
    hooks/
      hooks.json                 ← Claude Code hook wiring
    scripts/                     ← remote API integration scripts (plugin-owned)
      remote-api.ts              ← CLI dispatcher for remote API providers
      companion-bootstrap.ts     ← companion discovery hook
      providers/                 ← Jira, Azure DevOps, GitHub, and shared HTTP/provider types
  ritus-frontend/                ← frontend companion plugin; 0.2.0 baseline being rewritten (install 0.1.0 from precise-alloy/ritus-frontend until 1.0.0)
```

---

## Remote API - provider-agnostic dispatch

The `plugins/ritus/scripts/remote-api.ts` CLI supports three providers (Jira, Azure DevOps, GitHub) and two invocation
modes: auto-detected and explicit.

### Auto-detected (recommended)

In the examples, `<plugin-root>` is the installed plugin directory: Copilot CLI uses
`~/.copilot/installed-plugins/<marketplace>/ritus`, Claude Code uses
`~/.claude/plugins/cache/<marketplace>/ritus/<version>`, and a clone of this repository uses `plugins/ritus/`.

The dispatcher infers the provider from the target format:

```bash
bun run "<plugin-root>/scripts/remote-api.ts" <action> <target> [extra]
```

Examples:

```bash
# Jira - detected from bare key format (PROJ-123)
bun run "<plugin-root>/scripts/remote-api.ts" issue PROJ-123

# ADO work item - detected from bare numeric ID or full URL
bun run "<plugin-root>/scripts/remote-api.ts" issue 12345
bun run "<plugin-root>/scripts/remote-api.ts" issue https://dev.azure.com/org/project/_workitems/edit/12345

# GitHub - detected from #-prefixed number (requires GITHUB_REPO_URL in .ritus/.env.local)
bun run "<plugin-root>/scripts/remote-api.ts" pr '#18'
bun run "<plugin-root>/scripts/remote-api.ts" comments '#18'
bun run "<plugin-root>/scripts/remote-api.ts" issue '#7'

# GitHub - detected from full URL
bun run "<plugin-root>/scripts/remote-api.ts" pr https://github.com/owner/repo/pull/42
bun run "<plugin-root>/scripts/remote-api.ts" issue https://github.com/owner/repo/issues/7

# ADO PR - detected from dev.azure.com URL
bun run "<plugin-root>/scripts/remote-api.ts" pr https://dev.azure.com/org/project/_git/repo/pullrequest/1
```

Target format conventions (each provider has a distinct short-ref format - no ambiguity):

| Provider | Short ref   | Example                              |
|----------|-------------|--------------------------------------|
| Jira     | Key prefix  | `PROJ-123`                           |
| ADO      | Bare number | `12345`                              |
| GitHub   | `#` prefix  | `'#18'` (requires `GITHUB_REPO_URL`) |

**Note:** The `#` prefix must be quoted in bash to prevent shell comment interpretation:

```bash
bun run "<plugin-root>/scripts/remote-api.ts" pr '#18'   # correct
bun run "<plugin-root>/scripts/remote-api.ts" pr #18     # fails - shell treats #18 as comment
```

Detection precedence:

1. **Explicit provider** - if the first CLI argument matches a provider name (`jira`, `ado`, `github`),
   use that provider directly.
2. **Auto-detect from target** - filter credentialed providers by `canHandleTarget(action, target)`.
   Exactly one match uses that provider. Zero matches produces an error listing configured providers.
   Multiple matches produces an ambiguous error with explicit disambiguation commands.
3. **`team.yml` instance routing** - when `ticket_providers` lists are defined in
   `docs/profiles/team.yml`, instance-level filtering narrows candidates by key prefix (Jira),
   org/project (ADO), or hostname (GitHub).

### How instance routing works

When multiple instances of the same provider are configured in `team.yml`, the dispatcher routes by
matching the target against each instance's identifying attributes:

- **Jira** - matches the instance whose `key_prefixes` list contains the ticket's project key
  (e.g., ticket `CORE-42` routes to the instance with `key_prefixes: ["CORE"]`).
- **Azure DevOps** - matches the instance whose org and project match the target URL.
- **GitHub** - matches the instance whose hostname matches the target URL
  (`github.com` for public, custom hostname for Enterprise).

If the target matches **zero** instances, an error lists all configured instances. If the target
matches **multiple** instances, a hard error lists the candidates and prompts you to disambiguate
via `team.yml` configuration (key prefixes, hostnames, or org/project).

Single-instance setups require no `team.yml` changes - the default env var names work as before.

### Explicit provider (override)

Use when auto-detection is ambiguous or you want to bypass detection:

```bash
bun run "<plugin-root>/scripts/remote-api.ts" <provider> <action> <target> [extra]
```

Examples:

```bash
bun run "<plugin-root>/scripts/remote-api.ts" jira issue PROJ-123
bun run "<plugin-root>/scripts/remote-api.ts" github pr https://github.com/owner/repo/pull/42
bun run "<plugin-root>/scripts/remote-api.ts" ado pr https://dev.azure.com/org/project/_git/repo/pullrequest/1
```

### Multi-instance configuration

For teams using multiple instances of the same provider (e.g., two Jira tenants, github.com + GitHub
Enterprise), configure `docs/profiles/team.yml` with named instances:

```yaml
ticket_providers:
  - type: jira
    name: primary
    key_prefixes: [ "PROJ", "CORE" ]
    # omit env: → uses default env var names (JIRA_BASE_URL, JIRA_PAT, JIRA_EMAIL)
  - type: jira
    name: external
    key_prefixes: [ "EXT" ]
    env:
      base_url: JIRA_EXT_BASE_URL
      pat: JIRA_EXT_PAT
      email: JIRA_EXT_EMAIL
```

Then set credentials in `.ritus/.env.local` using the env var names declared in `team.yml`:

```env
JIRA_EXT_BASE_URL=https://other.atlassian.net
JIRA_EXT_PAT=yyy
JIRA_EXT_EMAIL=user@other.com
```

Default instances (those without an `env:` block) use the standard env var names from `.ritus/.env.example`.
The `check-env` command reports per-instance credential status when `team.yml` lists are present.

### Environment check

```bash
bun run "<plugin-root>/scripts/remote-api.ts" check-env
```

Reports which providers (or instances) are configured and which env vars are missing.

---

## Ongoing maintenance

### `docs/profiles/project.yml` - fill during work

Edit the `.yml` file, then have `docs/PROJECT_CONTEXT.md` re-rendered from it - `/setup` and `/repo-scan` both do - since
that rendered file is what the skills read.

| YAML field            | When to fill                                 |
|-----------------------|----------------------------------------------|
| `project_constraints` | Add rules as discovered                      |
| `authentication.*`    | During repo-scan or first auth-touching task |
| `error_handling`      | During repo-scan                             |
| `build_commands.*`    | During repo-scan                             |

### `docs/CODE_CONVENTIONS.md` - fill by repo-scan, refine manually

Repo-scan detects type system, naming, module structure, error handling, logging. Refine after repo-scan.

### `docs/TEST_CONVENTIONS.md` - fill by repo-scan, refine manually

Repo-scan detects test framework, naming, mocking strategy, fixtures, async patterns. Refine after repo-scan.

### `docs/ARCHITECTURE.md` - fill progressively

| Section                    | When                                         |
|----------------------------|----------------------------------------------|
| Apps/services and purposes | During first EPIC or system overview session |
| Key flows                  | Each time a major flow is built              |
| Runbook patterns           | First time a pattern is used                 |

### `docs/DECISIONS.md` - record non-obvious decisions

Written by `wrap-up` from `[DECISIONS]` entries that `ticket-review` (plan decisions) and the executors log in the
branch's exploration log, and by tasks that introduce an architecture decision; `debug` logs the direction the user
chooses when a fix loop escalates. `pr-review` names decisions worth recording. Also written manually for any
non-obvious constraint.

### `docs/LESSONS.md` - one entry per dangerous pattern found

Two triggers: (1) after bugs that reveal "never again" patterns, (2) when an EPIC memory file expires.

### `docs/memory/` - EPIC context files expire

Expiry days set by team size (solo=60, small=30, medium=21, large=14). Before deleting an expired memory file:

1. Extract `## Decisions` → append to `docs/DECISIONS.md`
2. Extract lessons → append to `docs/LESSONS.md`
3. Write one-line summary → `docs/CHANGELOG.md`
4. Delete the memory file

---

## Key resources

| Resource                                               | Purpose                              |
|--------------------------------------------------------|--------------------------------------|
| `docs/PROJECT_CONTEXT.md`                              | Always-on project facts              |
| `docs/profiles/`                                        | YAML data files (source of truth)    |
| `docs/CODE_CONVENTIONS.md`                              | Project-specific coding conventions  |
| `docs/TEST_CONVENTIONS.md`                              | Project-specific test conventions    |
| `docs/ARCHITECTURE.md`                                  | System architecture                  |
| `docs/DECISIONS.md`                                    | Architecture decisions and rationale |
| [docs/WORKFLOW_DIAGRAMS.md](docs/WORKFLOW_DIAGRAMS.md) | Visual workflow reference            |
