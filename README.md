# Ritus

**Pronounced:** *REE-tus* `/ˈriː.tus/`

A generic, project-agnostic AI-assisted development workflow. Skill-based architecture with on-demand loading,
chain-based routing, and independent verification. Works with Claude Code, GitHub Copilot, and any language or stack.

---

## Formula

```text
AI Agent Workflow = Primary rules + Core workflow + Project profile + Runtime context
```

| Layer | File(s) | What it does |
|-------|---------|-------------|
| Primary rules | CLAUDE.md / copilot-instructions.md | User's behavioral directives — highest authority |
| Core workflow | Skills (via plugin) | On-demand skills with subagent dispatch instructions |
| Project profile | `docs/profiles/*.yml` → `docs/PROJECT_CONTEXT.md` | Project facts rendered from YAML data |
| Runtime context | Current task file + active skill | What to work on now |

---

## Installation

### Plugin (recommended)

**Claude Code:**

1. Add marketplace
2. Install Ritus

```text
/plugin marketplace add precise-alloy/ritus#plugin
/plugin install ritus
```

**GitHub Copilot CLI:**

1. Add the marketplace
2. Fetch the plugin manifest
3. Install Ritus

```text
/plugin marketplace add precise-alloy/ritus#plugin
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

The setup skill automatically scaffolds all project files (`docs/`, `.ritus/`, `.env.local`) and runs a
10-question interview to fill your project profiles.

For existing codebases, follow up with:

```text
run repo-scan
```

This detects auth patterns, build commands, testing conventions, and coding conventions from your codebase.

### Upgrading

**Plugin:** updates automatically — skills are replaced. On next session start, the sync hook reports
missing project files. Run the setup again to create any new files. Existing user files are never overwritten.

## What gets generated

**By plugin (workflow-owned):**

| Component | What it contains |
|-----------|-----------------|
| 16 skills | On-demand workflow and standard skills (includes `start-ritus` meta-skill for auto-routing) |

**By setup / repo-scan (user-owned in target project):**

| File | What it contains |
|------|-----------------|
| `docs/PROJECT_CONTEXT.md` | Always-on project facts (rendered from profiles) |
| `docs/profiles/*.yml` | Source of truth — project, team, runtime data |
| `docs/ARCHITECTURE.md` | System architecture (header filled, rest progressive) |
| `docs/CODE_CONVENTIONS.md` | Project-specific coding conventions (filled by repo-scan) |
| `docs/TEST_CONVENTIONS.md` | Project-specific test conventions (filled by repo-scan) |

---

## Skills

Skills are self-contained SKILL.md files loaded on-demand. Each has YAML frontmatter (name + description) so the
agent scans relevance without loading the full content. Subagent dispatch (model, effort, constraints) is defined
in the `start-ritus` skill and in each skill's dispatch instructions section.

### Workflow skills

| Skill | Purpose                                                                         |
|-------|---------------------------------------------------------------------------------|
| `start-ritus` | Entry-point meta-skill — golden rules, dispatch instructions, workflow tracking |
| `brainstorm` | Explore unclear requirements — propose 2-3 approaches before triage             |
| `triage` | Classify changes by blast radius, contract impact, validation clarity           |
| `ticket-review` | Analyze requirements (plain text or ticket) → produce task files                |
| `execute-task` | Implement a task file — load context, implement steps, report                   |
| `verify-task` | Independent per-task verification (dispatched as fresh haiku subagent)          |
| `pr-review` | Adversarial review at ticket/PR level (dispatched as fresh sonnet subagent)     |
| `debug` | Systematic 4-phase root cause investigation with evidence grading               |
| `setup` | Setup interview — write YAML profiles, render docs/PROJECT_CONTEXT.md           |
| `sync` | Scaffold or check project files — create missing docs, profiles, scripts        |
| `repo-scan` | Detect stack, auth, build commands from existing codebase                       |

### Standard skills (loaded alongside workflow skills when applicable)

| Skill | Load when |
|-------|----------|
| `code-conventions` | Any code change |
| `testing-policy` | New service, endpoint, worker, or bug fix |
| `tdd` | New business logic or bug fix — enforces red-green-refactor |
| `security` | Auth, billing, migrations, tenant isolation, infra, shared contracts |
| `definition-of-done` | STANDARD or EPIC tasks |

### Skill chains

```text
Explore/brainstorm:   brainstorm → triage → ticket-review
Plan/implement:       triage → ticket-review → execute-task → verify-task (haiku subagent)
Debug/fix:            debug → execute-task → verify-task (haiku subagent)
Review:               pr-review (sonnet subagent)
```

---

## Daily workflow

```text
Write requirement
  → Agent loads triage skill → classifies (TRIVIAL / SIMPLE / STANDARD / EPIC)
  → Triage recommends model + effort from routing table

  TRIVIAL:                Agent implements directly — no task file, self-verifies
  SIMPLE / STANDARD / EPIC:
    → ticket-review produces task files (parallel groups when independent)
    → execute-task implements each task
    → verify-task subagent (haiku) reviews each task independently
    → pr-review subagent (sonnet) runs adversarial review at ticket level

  If pr-review approves → ready for merge/PR
  If pr-review rejects  → fix → re-verify → re-review until approved

  Human:
    → Reviews diff
    → Commits
    → Pushes
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
.env.example                     ← remote API credentials template
skills/
  start-ritus/SKILL.md     ← entry-point meta-skill: golden rules, dispatch instructions
  brainstorm/SKILL.md
  triage/SKILL.md
  ticket-review/SKILL.md
    templates/               ← review doc, task file, QA, EPIC memory templates
  execute-task/SKILL.md
  verify-task/SKILL.md
  pr-review/SKILL.md
  shared/
    remote-api-access.md     ← remote API rules (shared by ticket-review + pr-review)
  debug/SKILL.md
  setup/SKILL.md
  sync/SKILL.md
    script/sync.cjs              ← project file scaffolding script
  repo-scan/SKILL.md
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
.ritus/scripts/
  remote-api.ts                  ← CLI dispatcher for remote API providers
  providers/
    types.ts                     ← Provider interface and shared types
    http.ts                      ← HTTP plumbing (retry, auth, env loading)
    provider-jira.ts             ← Jira Cloud (tickets, comments, changelog, attachments)
    provider-ado.ts              ← Azure DevOps (PRs + work items)
    provider-github.ts           ← GitHub (PRs)
```

---

## Ongoing maintenance

### `docs/profiles/project.yml` — fill during work

Edit the `.yml` file. The AI agent re-reads `docs/PROJECT_CONTEXT.md` on next session start.

| YAML field | When to fill |
|------------|-------------|
| `project_constraints` | Add rules as discovered |
| `authentication.*` | During repo-scan or first auth-touching task |
| `error_handling` | During repo-scan |
| `build_commands.*` | During repo-scan |

### `docs/CODE_CONVENTIONS.md` — fill by repo-scan, refine manually

Repo-scan detects type system, naming, module structure, error handling, logging. Refine after repo-scan.

### `docs/TEST_CONVENTIONS.md` — fill by repo-scan, refine manually

Repo-scan detects test framework, naming, mocking strategy, fixtures, async patterns. Refine after repo-scan.

### `docs/ARCHITECTURE.md` — fill progressively

| Section | When |
|---------|------|
| Apps/services and purposes | During first EPIC or system overview session |
| Key flows | Each time a major flow is built |
| Runbook patterns | First time a pattern is used |

### `docs/DECISIONS.md` — record non-obvious decisions

Written automatically by `ticket-review` (architectural choices), `debug` (escalation gate), and `pr-review`
(design concerns). Also written manually for any non-obvious constraint.

### `docs/LESSONS.md` — one entry per dangerous pattern found

Two triggers: (1) after bugs that reveal "never again" patterns, (2) when an EPIC memory file expires.

### `docs/memory/` — EPIC context files expire

Expiry days set by team size (solo=60, small=30, medium=21, large=14). Before deleting an expired memory file:

1. Extract `## Decisions` → append to `docs/DECISIONS.md`
2. Extract lessons → append to `docs/LESSONS.md`
3. Write one-line summary → `docs/CHANGELOG.md`
4. Delete the memory file

---

## Key resources

| Resource | Purpose |
|----------|---------|
| [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md) | Always-on project facts |
| [docs/profiles/](docs/profiles/) | YAML data files (source of truth) |
| [docs/CODE_CONVENTIONS.md](docs/CODE_CONVENTIONS.md) | Project-specific coding conventions |
| [docs/TEST_CONVENTIONS.md](docs/TEST_CONVENTIONS.md) | Project-specific test conventions |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Architecture decisions and rationale |
| [docs/WORKFLOW_DIAGRAMS.md](docs/WORKFLOW_DIAGRAMS.md) | Visual workflow reference |
