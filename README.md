# AI Workflow — V1.0

A generic, project-agnostic AI-assisted development workflow. Covers role detection, triage, task generation, execution,
standards enforcement, and doc discipline. Works with any language, stack, or team size.

---

## How to adopt

Two paths — pick one.

| Situation                | Do this                                                                                            |
|--------------------------|----------------------------------------------------------------------------------------------------|
| New project (empty repo) | Copy `.ai/` and `.github/` folders into repo root → say "setup ai workflow"                        |
| Existing codebase        | Copy `.ai/` and `.github/` folders into repo root → say "setup ai workflow" → then "run repo-scan" |

That's it. The AI agent runs an interactive setup interview — no templates to paste.

---

## What the setup interview asks

The AI agent asks one question at a time. Have these ready before starting:

| #   | Question                     | Notes                                                                          |
|-----|------------------------------|--------------------------------------------------------------------------------|
| Q1  | New or existing project?     | Determines whether repo-scan runs after setup                                  |
| Q2  | Project name                 | Lowercase kebab-case — used in task file slugs and commit scopes               |
| Q3  | Team size                    | `solo` / `small` / `medium` / `large` — drives tasks/ naming and memory expiry |
| Q4  | Primary language + framework | e.g. `TypeScript + Next.js`, `Python + FastAPI`                                |
| Q5  | Git platform                 | `GitHub` / `GitLab` / `Azure DevOps` / other — skipped if solo                 |
| Q6  | Git workflow                 | `PR-based` / `trunk-based` / `gitflow`                                         |
| Q7  | AI tools in use              | `Claude Code` / `Cursor` / `Codex` / `Cline` / other                           |
| Q8  | Model cost preference        | `cost-first` / `balanced` (default) / `quality-first`                          |
| Q9  | Ticket format                | e.g. `PROJ-123` / `#123` / `none` — skipped if solo                            |
| Q10 | Workflow owner               | `tech-lead` / `team` — skipped if solo                                         |
| Q11 | QA mode (optional)           | `task` / `epic-only` / `off` (default) — generates `.qa.md` docs for testers   |

---

## What gets generated

After the interview, the AI agent writes these files automatically:

| File                      | What it contains                                                                                                     |
|---------------------------|----------------------------------------------------------------------------------------------------------------------|
| `.ai/AGENTS.md`           | **Workflow source of truth** — role detection, triage, read order, golden rules, standards, output format            |
| `.ai/profiles/project.md` | Project-specific technical facts — language, source layout, auth/error/testing patterns, build commands, constraints |
| `.ai/profiles/team.md`    | Team process config — ticket format, branch/PR conventions, QA mode, traceability policy, review defaults            |
| `.ai/profiles/runtime.md` | Runtime config — AI tools, model routing, mandatory Bun remote API helper rules                                      |
| `.ai/exec-context.md`     | Auto-generated executor context — thin subset generated from project profile + reusable executor rules               |
| `.ai/routing.md`          | Role detection flow, context-by-role map, runtime profile pointer                                                    |
| `.ai/SKILLS-TODO.md`      | Tech stack registry — language + framework pre-filled, rest as ❓                                                     |
| `docs/ARCHITECTURE.md`    | Header filled — rest populated progressively during work                                                             |
| `AGENTS.md` (root)        | Thin pointer → `.ai/AGENTS.md`                                                                                       |
| `.claude/CLAUDE.md`       | Bootstrap pointer + setup/repo-scan triggers                                                                         |

**Filled later by repo-scan or first work session:**

- Project profile: auth pattern, error handling, testing pattern, project constraints
- Team profile: branch/PR defaults, QA mode, traceability policy
- Runtime profile: AI tools, model routing, Bun remote API helper config
- Build / lint / test / typecheck commands
- Module skill files (`.ai/skills/`)
- Module map (`.ai/module-map.md`)

---

## Role system

The AI agent detects its role from the message before loading any context.

| Role          | Triggered by                                                                  | Context loaded                              | Output                      |
|---------------|-------------------------------------------------------------------------------|---------------------------------------------|-----------------------------|
| **Architect** | `design`, `plan`, `break down`, `analyze`, `brainstorm`, `review and propose` | `.ai/AGENTS.md` + targeted profile sections | Task files + execution plan |
| **Executor**  | `implement`, `fix`, `build`, `create`, `refactor`, `update X`                 | `exec-context.md` only (~75% fewer tokens)  | Code changes + DONE WHEN    |

The AI agent also acts as executor when the message is execution-intent — it loads `exec-context.md` instead of
`AGENTS.md`. Configured external tools always run as executor.

Ambiguous message → defaults to **Architect**. The agent never switches role mid-task silently — stops and asks if
unclear.

---

## Daily workflow

```text
Write requirement
  → Agent detects role (architect or executor)

  ARCHITECT:
    → Triage (TRIVIAL / SIMPLE / STANDARD / EPIC)
    → TRIVIAL: Executor implements directly
    → SIMPLE:  2-section task note → send to executor tool
    → STANDARD/EPIC: task files + execution plan → send to executor tool

  EXECUTOR (configured code-edit tool or shell runner):
    → Reads exec-context.md + task file + applicable standards
    → Implements STEPS
    → Validates DONE WHEN + standards gates
    → Updates .qa.md if QA mode is on
    → Reports done

  Human:
    → Reviews diff
    → Commits using batch commit message
    → Pushes
```

---

## QA docs (when QA mode is active)

For STANDARD and EPIC tasks, the architect agent generates a paired `.qa.md` alongside each task file.

```text
.ai/tasks/feat-auth/001-add-login.md        ← task (for executor)
.ai/tasks/feat-auth/001-add-login.qa.md     ← QA impact doc (for tester)
```

Each `.qa.md` contains: affected features, regression risk (low/medium/high), test scenarios, regression checks, and
what testers can safely skip.

When an EPIC closes, a summary is generated at `docs/qa/{epic-slug}.qa.md` consolidating all impacted features in
recommended test order.

---

## Bundled skills

This workflow includes two repository skills under `.github/skills/`:

| Skill           | Use for                                                                                              | Reads project-specific guidance from                                                                          |
|-----------------|------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|
| `ticket-review` | Fetching/reviewing tickets, extracting requirements, creating review docs, and generating task files | `.ai/profiles/project.md`, `.ai/profiles/team.md`, `.ai/profiles/runtime.md`, `.ai/standards/stakeholders.md` |
| `pr-review`     | Reviewing remote PRs or local pre-PR changes against ticket requirements and task DONE WHEN gates    | `.ai/profiles/project.md`, `.ai/profiles/team.md`, `.ai/profiles/runtime.md`, `.ai/standards/stakeholders.md` |

Both skills use `.ai/profiles/runtime.md` section `## Remote API access` for Jira/Azure DevOps access. Bun and
`.github/scripts/remote-api.ts` are mandatory for those remote calls.

---

## Repository structure

```text
AGENTS.md                    ← thin pointer to .ai/AGENTS.md (do not add rules here)
README.md                    ← this file
.claude/
  CLAUDE.md                  ← Claude Code bootstrap (setup trigger, pointer to .ai/AGENTS.md)
.ai/
  AGENTS.md                  ← workflow source of truth — role, triage, read order, golden rules
  profiles/
    project.md               ← project-specific technical facts and commands
    team.md                  ← team process, branch/PR, QA, traceability policy
    runtime.md               ← AI tools, model routing, remote API helper
  exec-context.md            ← auto-generated executor context
  SKILLS-TODO.md             ← tech stack registry (❓ rows filled during work)
  module-map.md              ← phrase → module name mappings
  routing.md                 ← role detection, context-by-role, model routing
  workflows/
    setup.md                 ← setup interview; fills AGENTS.md + profiles
    repo-scan.md             ← existing project scan; fills project profile + SKILLS-TODO.md
    generate-tasks.md        ← architect: triage, task formats, QA file formats
    execute-task.md          ← executor: implementation steps, DONE WHEN gates
    feature.md               ← feature workflow
    bugfix.md                ← bugfix workflow
  standards/
    code-conventions.md      ← naming, structure, error handling, logging
    security.md              ← auth, secrets, tenant isolation, audit logging
    testing-policy.md        ← test type matrix, unit/integration rules
    ui-visual-testing.md     ← component, page, accessibility checks
    definition-of-done.md    ← hard gates, per-change-type checklists
    stakeholders.md          ← stakeholder ownership and escalation template
  skills/                    ← module interface summaries (created during work)
  tasks/                     ← execution task files (created during work)
  memory/                    ← multi-session EPIC context snapshots
.github/
  skills/
    ticket-review/           ← ticket analysis and task planning skill
    pr-review/               ← PR/local-diff adversarial review skill
  scripts/
     remote-api.ts            ← Bun helper for Jira/Azure DevOps remote API access
docs/
  ARCHITECTURE.md            ← system architecture (filled progressively)
  CUTOFF.md                  ← module registry — documented vs code-only
  DECISIONS.md               ← architecture decisions and rationale
  CHANGELOG.md               ← completed EPICs log
  LESSONS.md                 ← dangerous patterns discovered from bugs
  qa/                        ← EPIC QA summaries (created when EPICs close)
```

---

## File merge strategy (existing projects)

| File / folder         | On adopt                                                                                                                             |
|-----------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| `.ai/AGENTS.md`       | Workflow-only source of truth — replace/merge only when upgrading the workflow (keep project/team/runtime config in `.ai/profiles/`) |
| `.ai/profiles/*.md`   | Merge project/team/runtime values — keep existing project constraints                                                                |
| `.ai/exec-context.md` | Regenerate from filled `.ai/profiles/project.md` after merge                                                                         |
| `AGENTS.md` (root)    | Overwrite with thin pointer after extracting any project-specific rules                                                              |
| `.claude/CLAUDE.md`   | Overwrite with bootstrap form after extracting any project-specific rules                                                            |
| `.ai/workflows/*.md`  | Replace                                                                                                                              |
| `.ai/routing.md`      | Replace                                                                                                                              |
| `.ai/SKILLS-TODO.md`  | Generate fresh from repo-scan                                                                                                        |
| `.ai/skills/*.md`     | Append only — never overwrite                                                                                                        |
| `.ai/tasks/**`        | Never touch                                                                                                                          |
| `.ai/memory/**`       | Never touch                                                                                                                          |
| `docs/**`             | Never touch                                                                                                                          |
| `.ai/module-map.md`   | Never touch                                                                                                                          |

---

## Ongoing maintenance

### `.ai/profiles/project.md` — fill during work

| Section                                       | When to fill                                                        |
|-----------------------------------------------|---------------------------------------------------------------------|
| `## Project-specific constraints`             | Add rules as discovered — one rule per line                         |
| `## Testing` / `## Test location conventions` | After first test — project-specific commands and rules              |
| `## Authentication`                           | During repo-scan or first auth-touching task                        |
| `## Error handling`                           | During repo-scan                                                    |
| `## Build commands`                           | During repo-scan or correct after setup if auto-detection was wrong |

### `.ai/profiles/team.md` — fill during setup or process changes

| Section                        | When to fill                                         |
|--------------------------------|------------------------------------------------------|
| `## Team config`               | During setup interview                               |
| `## Branch conventions`        | During setup interview or when git workflow changes  |
| `## Pull request requirements` | During setup interview or when PR process changes    |
| `## Review defaults`           | During setup or review process changes               |
| `## Traceability policy`       | When ticket/commit/comment traceability rules change |

### `.ai/profiles/runtime.md` — fill during setup or tool changes

| Section                | When to fill                                                                                          |
|------------------------|-------------------------------------------------------------------------------------------------------|
| `## AI tools in use`   | During setup interview or when tools change                                                           |
| `## Model routing`     | During setup interview or when model budget changes                                                   |
| `## Remote API access` | When Jira/Azure DevOps remote access is needed; Bun and `.github/scripts/remote-api.ts` are mandatory |

### `docs/ARCHITECTURE.md` — fill progressively

| Section                    | When                                                          |
|----------------------------|---------------------------------------------------------------|
| Apps/services and purposes | During first EPIC or system overview session                  |
| Key flows                  | Each time a major flow is built                               |
| Runbook patterns           | First time a pattern is used (new endpoint, new module, etc.) |

### `docs/DECISIONS.md` — one entry per non-obvious constraint

Write a `DECISION-NNN` block each time a rule is added to `.ai/AGENTS.md` or `.ai/profiles/` that needs rationale.

### `docs/LESSONS.md` — one entry per dangerous pattern found

Two triggers: (1) after bugs that reveal "never again" patterns, (2) when an EPIC memory file expires — extract
failure/lesson entries before deleting the memory file.

### `docs/CHANGELOG.md` — one entry per completed EPIC

One line per EPIC. Delete the corresponding `.ai/memory/` file after logging.

### `.ai/memory/` — EPIC context files expire

Expiry days set by team size (solo=60, small=30, medium=21, large=14). Before deleting an expired memory file:

1. Extract `## Decisions` → append to `docs/DECISIONS.md`
2. Extract lessons → append to `docs/LESSONS.md`
3. Write one-line summary → `docs/CHANGELOG.md`
4. Delete the memory file

### `docs/qa/` — EPIC QA summaries (when QA mode is active)

Generated automatically when an EPIC closes. One file per EPIC: `docs/qa/{epic-slug}.qa.md`. Testers use this as the
primary reference for what to verify and in what order.

### `.ai/skills/{module}.md` — create on first touch

Written by the agent when a module's interface is first encountered. Max 150 lines. Updated when public interface
changes.

---

## Key resources

| Resource                                                                       | Purpose                                                              |
|--------------------------------------------------------------------------------|----------------------------------------------------------------------|
| [.ai/AGENTS.md](.ai/AGENTS.md)                                                 | Workflow rules, triage, read order, standards, output format         |
| [.ai/profiles/project.md](.ai/profiles/project.md)                             | Project-specific technical facts, auth/error/testing, build commands |
| [.ai/profiles/team.md](.ai/profiles/team.md)                                   | Team process, branch/PR, QA, traceability, review defaults           |
| [.ai/profiles/runtime.md](.ai/profiles/runtime.md)                             | AI tools, model routing, remote API helper rules                     |
| [.ai/routing.md](.ai/routing.md)                                               | Role detection, context-by-role map, executor guide                  |
| [.ai/exec-context.md](.ai/exec-context.md)                                     | Executor context generated from project profile + reusable rules     |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)                                   | System architecture, runbook patterns                                |
| [docs/CUTOFF.md](docs/CUTOFF.md)                                               | What is documented vs what exists only in code                       |
| [.ai/standards/](.ai/standards/)                                               | Code conventions, security, testing, UI, definition of done          |
| [.github/skills/ticket-review/SKILL.md](.github/skills/ticket-review/SKILL.md) | Ticket analysis, review docs, and task planning                      |
| [.github/skills/pr-review/SKILL.md](.github/skills/pr-review/SKILL.md)         | PR/local-diff review against ticket requirements                     |
| [docs/qa/](docs/qa/)                                                           | EPIC QA summaries for testers                                        |
