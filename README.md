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
| Core workflow   | Skills (via plugin)                               | On-demand pure-capability skills; the main thread dispatches subagents per `skills/shared/dispatch.md` |
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

After plugin install, tell your AI agent:

```text
setup ai work flow
```

or just

```text
/setup
```

The setup skill automatically scaffolds all project files (`docs/`, `.ritus/.env.example`) and runs an
11-question interview to fill your project profiles.

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
project, it can be safely deleted. These scripts now live in the plugin's `scripts/` directory and are no longer copied
into consuming projects.

For existing codebases, follow up with:

```text
run repo-scan
```

This detects auth patterns, build commands, testing conventions, and coding conventions from your codebase.

### Upgrading

**Plugin:** updates automatically - skills are replaced. On next session start, the sync hook reports
missing project files. Run the setup again to create any new files. Existing user files are never overwritten.

## What gets generated

**By plugin (workflow-owned):**

| Component | What it contains           |
|-----------|----------------------------|
| 21 skills | Workflow + standard skills |

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
not who runs next; the main thread drives them via a TODO and dispatches subagents (model, effort, constraints)
using the single contract in `skills/shared/dispatch.md`.

### Workflow skills

| Skill                  | Purpose                                                                                |
|------------------------|----------------------------------------------------------------------------------------|
| `start-ritus`          | Entry-point meta-skill - golden rules, dispatch instructions, workflow tracking        |
| `brainstorm`           | Explore unclear requirements - propose 2-3 approaches before triage                    |
| `triage`               | Classify changes by blast radius, contract impact, validation clarity                  |
| `ticket-review`        | Analyze requirements (plain text or ticket) → produce task files                       |
| `requirement-analysis` | Read-heavy analysis + draft review doc (dispatched by ticket-review for STANDARD/EPIC) |
| `execute-task`         | Implement a task file - load context, implement steps, report                          |
| `verify-task`          | Independent per-task verification (dispatched as fresh cheap model subagent)            |
| `pr-review`            | Adversarial review at ticket/PR level (dispatched as fresh standard model subagent)     |
| `address-feedback`     | Read PR review comments, generate fix tasks; user reviews the diff and commits         |
| `wrap-up`              | Post-review cleanup - promote exploration entries, verify docs, report status          |
| `comprehension`        | Post-wrap-up advisory quiz - brief the human on the change, check understanding before commit |
| `debug`                | Systematic 4-phase root cause investigation with evidence grading                      |
| `setup`                | Setup interview - write YAML profiles, render docs/PROJECT_CONTEXT.md                  |
| `sync`                 | Scaffold or check project files - create missing docs, profiles, scripts               |
| `repo-scan`            | Detect stack, auth, build commands from existing codebase                              |
| `migrate-docs`         | Migrate pre-existing docs/notes into the ritus document standard - runs after setup/repo-scan |

### Standard skills (loaded alongside workflow skills when applicable)

| Skill                | Load when                                                                      |
|----------------------|--------------------------------------------------------------------------------|
| `code-conventions`   | Any code change                                                                |
| `testing-policy`     | New service, endpoint, worker, or bug fix                                      |
| `tdd`                | New business logic, new API endpoint, or bug fix - enforces red-green-refactor |
| `security`           | Auth, billing, migrations, tenant isolation, infra, shared contracts           |
| `definition-of-done` | STANDARD or EPIC tasks                                                         |

### Skill chains

```text
Explore/brainstorm:   brainstorm → triage → ticket-review
Plan/implement:       triage → ticket-review → execute-task → verify-task → pr-review → wrap-up → comprehension
Debug/fix:            debug → execute-task → verify-task → pr-review → wrap-up → comprehension
Review:               pr-review (standard model subagent) → verdict  (wrap-up only within a task-driven run)
Address feedback:     address-feedback → execute-task → verify-task → [pr-review re-check → wrap-up → comprehension]
Iterate:              wrap-up → comprehension; then user feedback → triage or brainstorm (new run)
```

---

## Control flow (TODO-driven)

Every workflow skill starts by writing its own step list as a TODO - verbatim, one item per step - and marks each
item done as it goes. This keeps a long-running agent on the rails: it never stops mid-chain, never skips a step,
and always shows the human exactly where it is.

The TODO is the single control surface. Each skill ends with a `## Handoff` that (1) reports its result and
(2) updates that TODO:

- **Orchestrators** (`ticket-review`, `address-feedback`, `debug`) create/own the driving TODO and apply TODO updates from worker verdicts.
- **Routing** (`start-ritus`, `brainstorm`, `triage`) direct to the next skill (typically `invoke <skill>`).
- **Workers** (`execute-task`, `verify-task`, `pr-review`) run as dispatched subagents and only report a verdict + follow-up.
- **Intra-skill worker** (`requirement-analysis`) is dispatched by `ticket-review` (not a driving-TODO item).
- The **main thread** owns and walks the TODO top to bottom - dispatching each `dispatch <skill> subagent` item as
  a fresh, independent subagent and running each `invoke <skill>` item inline.

Because the main thread is the only dispatcher, subagents never spawn other subagents - the workflow behaves
identically on Claude Code, GitHub Copilot, or any host, with no nested-subagent support required. The full dispatch
contract lives in one place: [`skills/shared/dispatch.md`](./skills/shared/dispatch.md).

---

## Daily workflow

```text
Write requirement
  → Agent loads triage skill → classifies (TRIVIAL / SIMPLE / STANDARD / EPIC)
  → Triage recommends model + effort from routing table

  TRIVIAL:                Agent implements directly - no task file, self-verifies
  SIMPLE / STANDARD / EPIC:
    → ticket-review produces task files (parallel groups when independent)
    → execute-task implements each task
    → verify-task subagent (cheap model) reviews each task independently
    → pr-review subagent (standard model) runs adversarial review at ticket level

  If pr-review approves → wrap-up (promote exploration, verify docs) → ready for merge/PR
  If pr-review rejects  → fix → re-verify → re-review (up to 3 attempts, then escalate — dispatch circuit breaker)

  Human:
    → Reviews diff
    → Commits + pushes
    → If PR receives review comments → address-feedback → fix → verify → local commit
    → Or provides follow-up changes → workflow restarts from triage/brainstorm
```

For the full workflow diagram, see [docs/WORKFLOW_DIAGRAMS.md](./docs/WORKFLOW_DIAGRAMS.md).

---

## Repository structure

```text
marketplace.json                 ← Copilot marketplace manifest
.claude-plugin/
    marketplace.json       ← Claude marketplace manifest
    plugin.json   ← Claude Code plugin manifest
README.md                        ← this file
templates/.ritus/.env.example        ← remote API credentials template (scaffolded into target project as .ritus/.env.example)
skills/
  start-ritus/SKILL.md     ← entry-point meta-skill: golden rules, dispatch instructions
  brainstorm/SKILL.md
  triage/SKILL.md
  ticket-review/SKILL.md
    templates/               ← review doc, task file, QA, EPIC memory templates
  requirement-analysis/SKILL.md  ← read-heavy analysis worker (dispatched by ticket-review)
  execute-task/SKILL.md
  verify-task/SKILL.md
  pr-review/SKILL.md
  address-feedback/SKILL.md
  wrap-up/SKILL.md
  shared/
    dispatch.md              ← TODO dispatch contract (spawn-then-invoke, run configs, Handoff convention)
    remote-api-access.md     ← remote API rules (shared by ticket-review + pr-review + address-feedback)
  debug/SKILL.md
  setup/SKILL.md
  sync/SKILL.md
    script/sync.ts               ← project file scaffolding script
  repo-scan/SKILL.md
  migrate-docs/SKILL.md
  code-conventions/SKILL.md
  testing-policy/SKILL.md
  tdd/SKILL.md
  security/SKILL.md
  definition-of-done/SKILL.md
docs/                            ← user-owned (scaffolded into target project)
  PROJECT_CONTEXT.md             ← always-on project facts (rendered from profiles)
  profiles/
    project.yml                  ← project data (source of truth)
    team.yml                     ← team data
    runtime.yml                  ← runtime data
  tasks/                         ← execution task files (created during work)
  memory/                        ← multi-session EPIC context snapshots
  ARCHITECTURE.md
  CODE_CONVENTIONS.md
  TEST_CONVENTIONS.md
  CUTOFF.md
  DECISIONS.md
  CHANGELOG.md
  LESSONS.md
  WORKFLOW_DIAGRAMS.md           ← visual workflow reference (human-only)
  qa/                            ← EPIC QA summaries (when QA mode is active)
scripts/                         ← remote API integration scripts (plugin-owned)
  remote-api.ts                  ← CLI dispatcher for remote API providers
  providers/
    types.ts                     ← Provider interface and shared types
    http.ts                      ← HTTP plumbing (retry, auth, env loading)
    provider-jira.ts             ← Jira Cloud (tickets, comments, changelog, attachments)
    provider-ado.ts              ← Azure DevOps (PRs + work items)
    provider-github.ts           ← GitHub (PRs + Issues)
templates/                       ← plugin-owned (source templates, not copied to projects)
```

---

## Remote API - provider-agnostic dispatch

The `scripts/remote-api.ts` CLI supports three providers (Jira, Azure DevOps, GitHub) and two invocation
modes: auto-detected and explicit.

### Auto-detected (recommended)

The dispatcher infers the provider from the target format:

```bash
bun run scripts/remote-api.ts <action> <target> [extra]
```

Examples:

```bash
# Jira - detected from bare key format (PROJ-123)
bun run scripts/remote-api.ts issue PROJ-123

# ADO work item - detected from bare numeric ID or full URL
bun run scripts/remote-api.ts issue 12345
bun run scripts/remote-api.ts issue https://dev.azure.com/org/project/_workitems/edit/12345

# GitHub - detected from #-prefixed number (requires GITHUB_REPO_URL in .ritus/.env.local)
bun run scripts/remote-api.ts pr '#18'
bun run scripts/remote-api.ts comments '#18'
bun run scripts/remote-api.ts issue '#7'

# GitHub - detected from full URL
bun run scripts/remote-api.ts pr https://github.com/owner/repo/pull/42
bun run scripts/remote-api.ts issue https://github.com/owner/repo/issues/7

# ADO PR - detected from dev.azure.com URL
bun run scripts/remote-api.ts pr https://dev.azure.com/org/project/_git/repo/pullrequest/1
```

Target format conventions (each provider has a distinct short-ref format - no ambiguity):

| Provider | Short ref   | Example                              |
|----------|-------------|--------------------------------------|
| Jira     | Key prefix  | `PROJ-123`                           |
| ADO      | Bare number | `12345`                              |
| GitHub   | `#` prefix  | `'#18'` (requires `GITHUB_REPO_URL`) |

**Note:** The `#` prefix must be quoted in bash to prevent shell comment interpretation:

```bash
bun run scripts/remote-api.ts pr '#18'   # correct
bun run scripts/remote-api.ts pr #18     # fails - shell treats #18 as comment
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
bun run scripts/remote-api.ts <provider> <action> <target> [extra]
```

Examples:

```bash
bun run scripts/remote-api.ts jira issue PROJ-123
bun run scripts/remote-api.ts github pr https://github.com/owner/repo/pull/42
bun run scripts/remote-api.ts ado pr https://dev.azure.com/org/project/_git/repo/pullrequest/1
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
bun run scripts/remote-api.ts check-env
```

Reports which providers (or instances) are configured and which env vars are missing.

---

## Ongoing maintenance

### `docs/profiles/project.yml` - fill during work

Edit the `.yml` file. The AI agent re-reads `docs/PROJECT_CONTEXT.md` on next session start.

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

Written automatically by `ticket-review` (architectural choices), `debug` (escalation gate), and `pr-review`
(design concerns). Also written manually for any non-obvious constraint.

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
| [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md)     | Always-on project facts              |
| [docs/profiles/](docs/profiles/)                       | YAML data files (source of truth)    |
| [docs/CODE_CONVENTIONS.md](docs/CODE_CONVENTIONS.md)   | Project-specific coding conventions  |
| [docs/TEST_CONVENTIONS.md](docs/TEST_CONVENTIONS.md)   | Project-specific test conventions    |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)           | System architecture                  |
| [docs/DECISIONS.md](docs/DECISIONS.md)                 | Architecture decisions and rationale |
| [docs/WORKFLOW_DIAGRAMS.md](docs/WORKFLOW_DIAGRAMS.md) | Visual workflow reference            |
