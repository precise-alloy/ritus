---
name: setup
description: Use when user says "setup workflow", "configure workflow", or "init workflow" — runs interview and fills project profiles
argument-hint: Provide any known project profile answers or constraints to prefill during setup
---

# Setup

## When to use

Run when human says: `setup workflow` / `setup workflow` / `init workflow` / `initialize workflow`

---

## Behavior rules

- Ask **one question at a time**. Wait for answer before moving to the next.
- For questions with predefined options: use a structured selection tool if available (e.g., `AskUserQuestion` in Claude Code), otherwise present numbered options as plain text.
- For free-text questions: ask as plain text output.
- Do **not** write any files mid-interview — collect all answers first.
- After all questions answered: run pre-output merge check, then write files.
- If human skips a question: use the listed default and note it.
- If answer is ambiguous: ask one clarifying follow-up, then proceed.

---

## Interview

### Q1 — Project type

Ask:

> "Is this a **new project** (empty repo) or an **existing codebase**?"

Options: `new` / `existing`

Record as: `{{PROJECT_TYPE}}`

- If `existing`: repo-scan runs after setup to fill `docs/profiles/project.yml`. Remind human.
- If `new`: proceed with remaining questions.

---

### Q2 — Project name

Ask:

> "What is the **project name**? (used as slug in task files and commit scopes — lowercase, kebab-case)"

Record as: `{{PROJECT_NAME}}`

---

### Q3 — Team size

Ask:

> "What is the **team size**?"

Options:

- `solo` — 1 developer
- `small` — 2–5 developers
- `medium` — 6–20 developers
- `large` — 20+ developers

Record as: `{{TEAM_SIZE}}`

Drives: tasks/ naming, PR reviewer count, memory expiry, setup question scope.

**If `solo`: skip Q5, Q9, Q10 — auto-derive defaults (both scalar and list fields are populated) and continue to Q4.**

| Auto-derived for solo      | Value                  |
|----------------------------|------------------------|
| Q5 — Git platform          | `GitHub`               |
| Q9 — Ticket providers      | `[]` (empty list)      |
| Q10 — Workflow owner       | `developer`            |

---

### Q4 — Primary language and framework

Ask:

> "What is the **primary language and main framework**?
> (e.g. TypeScript + Next.js · Python + FastAPI · Go + Gin · Java + Spring Boot)"

Record language as: `{{PRIMARY_LANGUAGE}}`

Record framework as: `{{FRAMEWORK}}`

Pre-fills: `docs/profiles/project.yml` fields `primary_language` and `framework`.

---

### Q5 — Git platform

Ask:

> "Which **git platform** does this repo use?"

Options: `GitHub` / `GitLab` / `Azure DevOps` / `Bitbucket` / `other`

Record as: `{{GIT_PLATFORM}}`

The dispatcher creates a default git provider instance automatically using standard env var names
(`GITHUB_TOKEN`, `AZURE_DEVOPS_READONLY_PAT`, etc.).

Drives: PR template format, branch convention details.

---

### Q6 — Git workflow

Ask:

> "Which **git workflow** does the team follow?"

Options:

- `PR-based` — feature branches → PR → merge to main (most common)
- `trunk-based` — short-lived branches, frequent integration to main
- `gitflow` — main + develop + feature/release/hotfix branches

Record as: `{{GIT_FLOW}}`

Drives: tasks/ path convention, branch naming strictness.

---

### Q7 — Default base branch

Ask:

> "What is the **default base branch** for feature PRs/merges? (e.g., `main`, `develop`, `master`)"

Default if skipped: `main` (or `develop` if `{{GIT_FLOW}}` is `gitflow`).

Record as: `{{DEFAULT_BASE_BRANCH}}`

Drives: PR review diff base, team conventions in `docs/PROJECT_CONTEXT.md`.

---

### Q8 — Model cost preference

Ask:

> "What is the **model cost preference** for this project?"

Options:

- `cost-first` — maximize Haiku usage, lowest API cost
- `balanced` — Haiku for light tasks, Sonnet for complex (recommended)
- `quality-first` — Sonnet as default, Opus for architecture decisions

Default if skipped: `balanced`

Record as: `{{MODEL_BUDGET}}`

Drives: model routing table in `docs/profiles/runtime.yml`.

---

### Q9 — Ticket system(s)

Ask:

> "Does the team use a **ticket/issue tracker**? Select all that apply.
> (Jira · Azure DevOps · GitHub Issues · none)"

Accept one or more ticket systems. For each, capture:
- **type**: `jira` / `github` / `ado`

Record primary format as: `{{TICKET_FORMAT}}` (scalar, backward compat — use the first ticket system's format, e.g. `PROJ-123` or `#123`; set to `none` if no systems).

Note: GitHub Issues uses `#`-prefixed numbers (e.g. `#18`) for short refs, which requires `GITHUB_REPO_URL` in `.env.local`. Full URLs (e.g. `https://github.com/owner/repo/issues/123`) also work without `GITHUB_REPO_URL`.

After collecting the list, for each selected ticket system ask:

> "Do you have **multiple instances** of **{type}**? (e.g., two Jira servers, or multiple ADO orgs)
> (yes/no — default: no)"

#### Single instance (default)

No further questions needed. Record as: `{{TICKET_PROVIDERS}}` entry with `name: default`, no `key_prefixes`, no `env`.
Routing works by target format: `PROJ-123` → Jira, `340796` → ADO, `#18` → GitHub.

- **Single system** (e.g. "Jira"): set `{{TICKET_FORMAT}}` = `PROJ-123`, `{{TICKET_PROVIDERS}}` = `[{type: jira, name: default}]`.
- **Multiple systems** (e.g. "Jira and GitHub Issues"): set `{{TICKET_FORMAT}}` = `PROJ-123`, `{{TICKET_PROVIDERS}}` = `[{type: jira, name: default}, {type: github, name: default}]`.
- **None**: set `{{TICKET_FORMAT}}` = `none`, `{{TICKET_PROVIDERS}}` = `[]`.

#### Multiple instances

Key prefixes and custom env vars are per-instance — they enable routing between instances of the same type.

For each instance ask:

> "What **name** should this instance have? (e.g., 'primary', 'external', 'backend')"
>
> "What **key prefixes** does this instance use? (comma-separated)" (Jira only — e.g., 'AMPS' for the first, 'AMP' for the second)

The first instance uses default env var names. For additional instances, ask:

> "What **custom env var names** should this instance use for settings that differ from the first instance?"
> (Shared credentials like tokens/PATs can reuse the same env var — only instance-specific settings like base URLs need unique names.)

Example with two Jira instances (same Atlassian account, different projects):
```
{{TICKET_PROVIDERS}} = [
  {type: jira, name: primary, key_prefixes: ["AMPS"]},
  {type: jira, name: maintenance, key_prefixes: ["AMP"], env: {base_url: JIRA_AMP_BASE_URL}}
]
```
The primary instance uses default env vars (`JIRA_BASE_URL`, `JIRA_PAT`, `JIRA_EMAIL`). The maintenance instance
overrides only `base_url` — `pat` and `email` fall through to the defaults (same Atlassian account).

Drives: branch naming format, `ticket_providers` list in team.yml.

---

### Q10 — Workflow owner

Ask:

> "Who **owns the workflow config**? (who updates project rules, profiles, and approves convention changes)"

Options:

- `tech-lead` — one designated person owns it
- `team` — anyone can propose changes via PR

Record as: `{{WORKFLOW_OWNER}}`

---

### Q11 — QA mode (optional)

Ask:

> "Do you want QA impact docs generated with task files? (helps testers know what to verify)"

Options:

- `task` — `.qa.md` generated per STANDARD/EPIC task + EPIC summary in `docs/qa/`
- `epic-only` — no per-task file, EPIC QA summary only at `docs/qa/{epic-slug}.qa.md`
- `off` — no QA docs generated (default if skipped)

Default if skipped: `off`

Record as: `{{QA_MODE}}`

Drives: `.qa.md` generation in task files, DONE WHEN QA gate, EPIC QA summary.

---

## Derived values (compute after interview — do not ask human)

### tasks/ naming convention → `{{TASKS_PATH_CONVENTION}}`

| `{{GIT_FLOW}}`          | Convention                                            |
|-------------------------|-------------------------------------------------------|
| `PR-based` or `gitflow` | `tasks/{branch-slug}/{NNN-name}.md`                   |
| `trunk-based`           | `tasks/{author}/{NNN-name}.md`                        |
| `solo` team size        | `tasks/{NNN-name}.md` (flat — no subdirectory needed) |

### Branch naming format → `{{BRANCH_FORMAT}}`

```text
feat/{ticket?}-{slug}      new feature
fix/{ticket?}-{slug}       bug fix
chore/{slug}               tooling, deps, config
refactor/{slug}            code restructure, no behavior change
docs/{slug}                documentation only
test/{slug}                tests only
```

If `{{TICKET_FORMAT}}` is `none`: omit ticket segment → `feat/{slug}`.

If `{{TICKET_FORMAT}}` is set: `feat/PROJ-123-{slug}` or `feat/#123-{slug}`.

**When multiple ticket systems are configured** (`{{TICKET_PROVIDERS}}` has >1 entry): use the **first** provider's
format as the primary for branch naming. The branch format template uses only one ticket prefix style — developers
choose the relevant ticket key when creating the branch. Example: if `ticket_providers` lists Jira (PROJ, CORE)
first and GitHub Issues (#) second, the branch format uses `PROJ-123` style as the example.

### PR reviewer count → `{{PR_REVIEWERS}}`

| `{{TEAM_SIZE}}` | Required reviewers     |
|-----------------|------------------------|
| `solo`          | 0 (self-merge allowed) |
| `small`         | 1                      |
| `medium`        | 1–2                    |
| `large`         | 2                      |

### EPIC memory expiry → `{{MEMORY_EXPIRY_DAYS}}`

| `{{TEAM_SIZE}}` | Days | Rationale                                               |
|-----------------|------|---------------------------------------------------------|
| `solo`          | 60   | Long-running projects, infrequent context switches      |
| `small`         | 30   | Moderate cadence, some parallel EPICs                   |
| `medium`        | 21   | Higher PR throughput, faster EPIC cycles                |
| `large`         | 14   | Many concurrent EPICs, stale context risk rises quickly |

**Expiry action (mandatory):** when a memory file reaches expiry date, before deleting:

1. Extract all `## Decisions` entries → append to `docs/DECISIONS.md`
2. Extract any failure/lesson entries → append to `docs/LESSONS.md`
3. Write a one-line summary to `docs/CHANGELOG.md`
4. Delete the memory file

### Traceability policy → `{{TRACEABILITY_POLICY}}`

| `{{TEAM_SIZE}}` | Policy |
|-----------------|--------|
| `solo`          | Commit messages only — no ticket ID required |
| `small`         | Ticket ID in branch name and commit message |
| `medium`        | Ticket ID in branch, commit, and PR title |
| `large`         | Ticket ID in branch, commit, PR title, and task file name |

### Model routing table → `{{MODEL_ROUTING}}`

**cost-first:**

| Triage                  | Model                       | Effort | Notes                           |
|-------------------------|-----------------------------|--------|---------------------------------|
| TRIVIAL                 | `claude-haiku-4-5-20251001` | low    | Direct edits, single file       |
| SIMPLE                  | `claude-haiku-4-5-20251001` | medium | 3-section task note             |
| STANDARD                | `claude-sonnet-4-6`         | medium | Cross-module, design decision   |
| EPIC                    | `claude-sonnet-4-6`         | high   | Multi-session, new architecture |
| Batch validate (pre-PR) | `claude-haiku-4-5-20251001` | low    | Diff + task review              |

**balanced (default):**

| Triage                  | Model                                                              | Effort | Notes                         |
|-------------------------|--------------------------------------------------------------------|----|-------------------------------|
| TRIVIAL                 | `claude-haiku-4-5-20251001`                                        | low    | Direct edits, single file     |
| SIMPLE                  | `claude-haiku-4-5-20251001`                                        | medium | 3-section task note           |
| STANDARD                | `claude-sonnet-4-6`                                                | high   | Cross-module, design decision |
| EPIC                    | `claude-sonnet-4-6` · `claude-opus-4-7` (pure arch decisions only) | high   | Multi-session                 |
| Batch validate (pre-PR) | `claude-haiku-4-5-20251001`                                        | medium | Diff + task review            |

**quality-first:**

| Triage                  | Model                       | Effort | Notes                           |
|-------------------------|-----------------------------|--------|---------------------------------|
| TRIVIAL                 | `claude-haiku-4-5-20251001` | medium | Direct edits, single file       |
| SIMPLE                  | `claude-sonnet-4-6`         | medium | 3-section task note             |
| STANDARD                | `claude-sonnet-4-6`         | high   | Cross-module, design decision   |
| EPIC                    | `claude-opus-4-7`           | xhigh  | Multi-session, new architecture |
| Batch validate (pre-PR) | `claude-sonnet-4-6`         | high   | Diff + task review              |

---

## Pre-output — scaffold project files

Before writing any profile data, **invoke the `sync` skill** to create all project files. This is a **blocking
step** — do not skip it. The sync skill creates all template files (profiles, docs, scripts, .env.example).
Existing user-edited files are never overwritten.

---

## Output — fill profile data after interview

After sync creates the scaffold files, fill them with interview answers. Replace every empty string (`""`) with the
recorded value.

If `docs/profiles/*.yml` already exist with filled values, preserve them — only fill fields that are still empty.

### Step 1: Fill `docs/profiles/project.yml`

Fill these fields from interview answers:

- `project_name`, `primary_language`, `framework`

Leave empty for repo-scan or first work session:

- `source_layout.*`, `documentation.*`, `authentication.*`, `error_handling`, `testing.*`
- `build_commands.*`, `project_constraints`, `module_map`

### Step 2: Fill `docs/profiles/team.yml`

Fill these fields:

- `team_size`, `git_platform`, `git_flow`, `workflow_owner`, `ticket_format`, `qa_mode`
- `ticket_providers` (list) — populate from `{{TICKET_PROVIDERS}}`; omit (or leave commented) when empty
- Git provider instances are created automatically from the git platform's standard env vars.
- Derived fields: `memory_expiry_days`, `branch_format`, `tasks_path_convention`, `pr_reviewers`,
  `default_base_branch`, `traceability_policy` (use derivation rules from § Derived values above)

### Step 3: Fill `docs/profiles/runtime.yml`

Fill these fields:

- `ai_tools` — auto-detect from platform: `Claude Code` if `CLAUDE_PLUGIN_ROOT` is set, `GitHub Copilot` if
  `PLUGIN_ROOT` is set, otherwise ask the user
- `model_routing` — paste the correct table from § Model routing table above

### Step 4: Render `docs/PROJECT_CONTEXT.md` from all `.yml` files

Read all three profile files (project.yml, team.yml, runtime.yml) and render `docs/PROJECT_CONTEXT.md` using the template structure.

### Step 5: Fill `docs/ARCHITECTURE.md` header

Fill header only:

- Project: `{{PROJECT_NAME}}`
- Stack: `{{PRIMARY_LANGUAGE}} + {{FRAMEWORK}}`

Leave all other sections as template placeholders.

---

## Completion checklist

After writing all files, output this to human:

```text
Setup complete — {{PROJECT_NAME}}

WRITTEN:
  docs/profiles/project.yml   project config (name, language, framework)
  docs/profiles/team.yml      team config (size, git workflow, branches)
  docs/profiles/runtime.yml   runtime config (AI tools, model routing)
  docs/PROJECT_CONTEXT.md     rendered from all profiles
  docs/ARCHITECTURE.md        header filled

FILL NEXT (repo-scan or first work session):
  [ ] Auth pattern
  [ ] Error handling pattern
  [ ] Testing commands + pattern
  [ ] Project-specific constraints
  [ ] Build / lint / test / typecheck commands
  [ ] Module map          (docs/profiles/project.yml module_map field)

NEXT STEP:
  Existing repo  → "Run repo-scan"
```

---

## Hard rules

- Never guess a `{{variable}}` value — only use what human answered or what is auto-derived for solo teams (Q5, Q9, Q10).
- Never write files before the pre-output merge check is complete.
- Never skip the completion checklist output.
- If human changes an answer after files are written: surgically update the specific token and re-output only the
  affected file.
