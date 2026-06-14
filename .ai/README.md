# AI Workflow — V1.0

Developer guide for this project's AI-assisted development workflow.

## Structure

```text
AGENTS.md          ← thin pointer to .ai/AGENTS.md (workflow rules entry point)
.ai/
  AGENTS.md        ← workflow rules, triage guidelines, role detection, and other global rules
  profiles/        ← project/team/runtime config for this project
  SKILLS-TODO.md   ← tech stack registry, fill during work
  module-map.md    ← module name mappings
  routing.md       ← flow, roles, executor guide
  workflows/       ← agent runbooks (generate-tasks, execute-task, feature, bugfix)
  standards/       ← code conventions, security, testing, UI, definition of done
  skills/          ← module interface summaries (created during work)
  tasks/           ← execution task files, grouped by module (created during work)
  memory/          ← multi-session context snapshots for EPICs (created during work)
docs/
  CUTOFF.md        ← module registry (what's documented vs not)
  ARCHITECTURE.md  ← system architecture
  DECISIONS.md     ← key architecture decisions + rationale
  CHANGELOG.md     ← completed EPICs log
```

---

## Setup

**New project:**

```text
Tell your AI agent: "Setup AI workflow for new project"
→ Agent generates skeletons, profiles, SKILLS-TODO.md all ❓
→ Begin work — agent fills stack info progressively
```

**Existing project:**

```text
Tell your AI agent: "setup ai workflow" → then "run repo-scan"
→ Agent runs repo-scan → conflict check → you confirm
→ Agent merges/replaces files, fills profiles and SKILLS-TODO from scan
→ Begin work
```

See root `README.md` for copy-paste setup templates with all required fields.

---

## Daily flow

```text
1. Write requirement
   → Architect agent triages (TRIVIAL / SIMPLE / STANDARD / EPIC)

   TRIVIAL:         Executor implements directly — no task file
   SIMPLE:          Architect writes 2-section task note → send to configured executor
   STANDARD / EPIC: Architect generates task files + execution plan
                    → Run code-edit group with configured executor
                    → Run shell group with configured shell runner (if needed)

2. Review diff → commit using batch commit message → push
```

---

## Requirement template

```text
MODULE: {name — see .ai/module-map.md}
TYPE: feature | bugfix | doc-debt | migration | epic
GOAL: {1–2 sentences}
ACCEPTANCE CRITERIA:
  - {condition 1}
  - {condition 2}
SCOPE CONSTRAINTS: {optional}
RELATED FILES: {optional}
```

---

## Executor guide

| Triage level    | Action                                                              |
|-----------------|---------------------------------------------------------------------|
| TRIVIAL         | Executor implements directly — no paste needed                      |
| SIMPLE          | Send 2-section task note to configured executor                     |
| STANDARD / EPIC | Send full task file to configured code-edit tool, then shell runner |

Configured executor and shell runner live in `.ai/profiles/runtime.md` section `## AI tools in use`.

---

## Commit format

```text
type(scope): subject

- what changed and why
- key invariant enforced

Breaking: none | {what breaks}
Migration: none | {migration needed}
```

Types: `feat` | `fix` | `refactor` | `test` | `docs` | `chore`

---

## File merge strategy (when adopting into existing project)

| File/folder          | On adopt                                                                                                                             |
|----------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| `.ai/AGENTS.md`      | Workflow-only source of truth — replace/merge only when upgrading the workflow (keep project/team/runtime config in `.ai/profiles/`) |
| `.ai/profiles/*.md`  | Merge filled values, including project constraints and runtime/team config                                                           |
| `.ai/workflows/*.md` | Replace                                                                                                                              |
| `.ai/routing.md`     | Replace                                                                                                                              |
| `.ai/SKILLS-TODO.md` | Generate fresh                                                                                                                       |
| `.ai/skills/*.md`    | Append only — never overwrite                                                                                                        |
| `.ai/tasks/**`       | Never touch                                                                                                                          |
| `.ai/memory/**`      | Never touch                                                                                                                          |
| `docs/**`            | Never touch                                                                                                                          |
| `.ai/module-map.md`  | Never touch                                                                                                                          |

---

## When an agent hits a ❓ in SKILLS-TODO.md

The agent stops, asks once, fills the row, updates the relevant `.ai/profiles/` or workflow file, then continues.

---

## Memory files

Check header before an agent uses one:

```text
Auto-expire: YYYY-MM-DD
Active-until: {task ID} done
```

When EPIC done: delete file + log in `docs/CHANGELOG.md`.

---

## Optional scripts

```bash
pnpm validate-all     # batch EPIC sanity check
pnpm docs-sync        # pre-PR doc check
pnpm lint-workflows   # workflow drift check
```
