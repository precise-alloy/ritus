# Setup Wizard — AI Workflow V1.0

## Trigger

Run this workflow when human says any of:
`"setup ai workflow"` · `"setup workflow"` · `"init workflow"` · `"initialize workflow"` · `"Setup AI workflow for new project"`

---

## Behavior rules

- Ask **one question at a time**. Wait for answer before moving to the next.
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

- If `existing`: repo-scan runs after setup to fill SKILLS-TODO.md. Remind human.
- If `new`: skeleton generation runs after setup.

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

**If `solo`: skip Q5, Q9, Q10 — auto-derive defaults and continue to Q4.**

| Auto-derived for solo | Value       |
|-----------------------|-------------|
| Q5 — Git platform     | `GitHub`    |
| Q9 — Ticket format    | `none`      |
| Q10 — Workflow owner  | `developer` |

---

### Q4 — Primary language and framework

Ask:

> "What is the **primary language and main framework**?
> (e.g. TypeScript + Next.js · Python + FastAPI · Go + Gin · Java + Spring Boot)"

Record language as: `{{PRIMARY_LANGUAGE}}`

Record framework as: `{{FRAMEWORK}}`

Pre-fills: SKILLS-TODO.md Language + Runtime rows → mark ✅.

---

### Q5 — Git platform

Ask:

> "Which **git platform** does the team use?"

Options: `GitHub` / `GitLab` / `Azure DevOps` / `Bitbucket` / `other`

Record as: `{{GIT_PLATFORM}}`

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

### Q7 — AI tools in use

Ask:

> "Which **AI tools** does the team use? (list all that apply)"

Options: `Claude Code` · `Cursor` · `GitHub Copilot` · `Codex` · `Cline` · `other`

Record as: `{{AI_TOOLS}}`

Drives: `.ai/profiles/runtime.md` executor and shell runner guidance.

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

Drives: model routing table in `.ai/profiles/runtime.md` and `routing.md`.

---

### Q9 — Ticket system

Ask:

> "Does the team use a **ticket/issue tracker**? If yes, what prefix format?
> (e.g. `PROJ-123` for Jira · `#123` for GitHub Issues · `none`)"

Record as: `{{TICKET_FORMAT}}` (or `none`)

Drives: branch naming format.

---

### Q10 — Workflow owner

Ask:

> "Who **owns this AI workflow config**? (who updates `.ai/AGENTS.md`, approves rule changes)"

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

### Model routing table → `{{MODEL_ROUTING}}`

**cost-first:**

| Triage                  | Model                       | Notes                           |
|-------------------------|-----------------------------|---------------------------------|
| TRIVIAL                 | `claude-haiku-4-5-20251001` | Direct edits, single file       |
| SIMPLE                  | `claude-haiku-4-5-20251001` | 2-section task note             |
| STANDARD                | `claude-sonnet-4-6`         | Cross-module, design decision   |
| EPIC                    | `claude-sonnet-4-6`         | Multi-session, new architecture |
| Batch validate (pre-PR) | `claude-haiku-4-5-20251001` | Diff + task review              |

**balanced (default):**

| Triage                  | Model                                                              | Notes                         |
|-------------------------|--------------------------------------------------------------------|-------------------------------|
| TRIVIAL                 | `claude-haiku-4-5-20251001`                                        | Direct edits, single file     |
| SIMPLE                  | `claude-haiku-4-5-20251001`                                        | 2-section task note           |
| STANDARD                | `claude-sonnet-4-6`                                                | Cross-module, design decision |
| EPIC                    | `claude-sonnet-4-6` · `claude-opus-4-7` (pure arch decisions only) | Multi-session                 |
| Batch validate (pre-PR) | `claude-haiku-4-5-20251001`                                        | Diff + task review            |

**quality-first:**

| Triage                  | Model                       | Notes                           |
|-------------------------|-----------------------------|---------------------------------|
| TRIVIAL                 | `claude-haiku-4-5-20251001` | Direct edits, single file       |
| SIMPLE                  | `claude-sonnet-4-6`         | 2-section task note             |
| STANDARD                | `claude-sonnet-4-6`         | Cross-module, design decision   |
| EPIC                    | `claude-opus-4-7`           | Multi-session, new architecture |
| Batch validate (pre-PR) | `claude-sonnet-4-6`         | Diff + task review              |

---

## Pre-output — merge existing rules

Run this check before writing any file. Preserve project-specific rules already present.

```text
1. Does root AGENTS.md contain content beyond the pointer text?
   → Extract: auth pattern, error handling, testing pattern, constraints, build commands
   → Merge extracted values into corresponding sections of `.ai/profiles/project.md`
   → Overwrite root AGENTS.md with thin pointer form after merge

2. Does .claude/CLAUDE.md contain content beyond the bootstrap text?
   → Extract any project-specific rules found
   → Merge into `.ai/profiles/project.md` project-specific constraints section
   → Overwrite .claude/CLAUDE.md with thin bootstrap form after merge

3. Do `.ai/AGENTS.md` or `.ai/profiles/*.md` already exist with filled values?
   → Preserve all filled values — do not overwrite with {{variable}} tokens
   → Only fill sections that still show unfilled {{variable}} tokens
```

---

## Output — files to write after interview

Write all files in this order. Replace every `{{variable}}` with the recorded value.
Do not leave any `{{variable}}` token in the output.

### 1. `.ai/AGENTS.md` — workflow source of truth

No project/team/runtime tokens should be filled here. Keep workflow rules reusable and point to `.ai/profiles/` for
project-specific values.

### 2. `.ai/profiles/project.md` — project profile

Fill these tokens:

- `{{PROJECT_NAME}}`
- `{{PRIMARY_LANGUAGE}}`
- `{{FRAMEWORK}}`

Leave these for repo-scan or first work session:

- `{{BUSINESS_LOGIC_PATHS}}`, `{{WEB_API_PATHS}}`, `{{MODEL_CONTRACT_PATHS}}`, `{{INTEGRATION_PATHS}}`,
  `{{FRONTEND_PATHS}}`, `{{GENERATED_ARTIFACT_PATHS}}`
- `{{TICKET_REVIEW_DOCS_PATH}}`
- `{{AUTH_PATTERN}}` and sub-fields
- `{{ERROR_HANDLING_PATTERN}}`
- `{{TESTING_PATTERN}}`
- `{{TEST_LOCATION_CONVENTIONS}}`
- `{{PROJECT_CONSTRAINTS}}`
- `{{BUILD_CMD}}`, `{{TYPECHECK_CMD}}`, `{{TEST_CMD}}`, `{{LINT_CMD}}`

### 3. `.ai/profiles/team.md` — team profile

Fill these tokens:

- `{{TEAM_SIZE}}`
- `{{GIT_PLATFORM}}`
- `{{GIT_FLOW}}`
- `{{WORKFLOW_OWNER}}`
- `{{TICKET_FORMAT}}`
- `{{MEMORY_EXPIRY_DAYS}}`
- `{{QA_MODE}}`
- `{{BRANCH_FORMAT}}`
- `{{TASKS_PATH_CONVENTION}}`
- `{{PR_REVIEWERS}}`
- `{{DEFAULT_BASE_BRANCH}}`
- `{{TRACEABILITY_POLICY}}`

### 4. `.ai/profiles/runtime.md` — runtime profile

Fill these tokens:

- `{{AI_TOOLS}}`
- `{{MODEL_ROUTING}}` — paste the correct table from §Model routing table above

### 5. Root `AGENTS.md` — thin pointer

Write exactly:

```text
# AGENTS.md
Source of truth: `.ai/AGENTS.md`
Read `.ai/AGENTS.md` before doing any work. Do not add rules here.
```

### 6. `.claude/CLAUDE.md` — bootstrap pointer

Keep the bootstrap form. Do not add rules.

### 7. `.ai/exec-context.md` — auto-generated executor context

Extract from `.ai/profiles/project.md` after filling it. Copy these sections verbatim:

- Project name (header)
- Auth pattern (`{{AUTH_PATTERN}}` and sub-fields)
- Error handling (`{{ERROR_HANDLING_PATTERN}}`)
- Build commands (`{{BUILD_CMD}}`, `{{TYPECHECK_CMD}}`, `{{TEST_CMD}}`, `{{LINT_CMD}}`)

Do not copy: triage, team config, model routing, branch conventions, pre-coding read order,
SKILLS-TODO.md discipline, memory expiry.

The static sections (role statement, golden rules, standards table, skills maintenance, output format) come from the
exec-context.md template — do not regenerate them from `.ai/AGENTS.md` or `.ai/profiles/*.md`.

### 8. `.ai/routing.md`

Ensure executor section points to `.ai/profiles/runtime.md`.
Fill `.ai/profiles/runtime.md` model routing with the correct `{{MODEL_ROUTING}}` table.

### 9. `.ai/SKILLS-TODO.md`

Pre-fill rows:

- Language → `{{PRIMARY_LANGUAGE}}` → ✅
- Runtime / framework → `{{FRAMEWORK}}` → ✅
- Leave other rows as ❓

### 10. `docs/ARCHITECTURE.md`

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
  .ai/AGENTS.md        workflow rules
  .ai/profiles/*.md    filled (project, team, runtime config)
  .ai/exec-context.md  auto-generated (auth, error handling, build commands)
  .ai/routing.md       updated (role detection, executor tools, model routing)
  .ai/SKILLS-TODO.md   pre-filled (language + framework)
  docs/ARCHITECTURE.md header filled
  root AGENTS.md       thin pointer
  .claude/CLAUDE.md    bootstrap pointer

FILL NEXT (repo-scan or first work session):
  [ ] Auth pattern
  [ ] Error handling pattern
  [ ] Testing commands + pattern
  [ ] Project-specific constraints
  [ ] Build / lint / test / typecheck commands
  [ ] Module skill files  (.ai/skills/)
  [ ] Module map          (.ai/module-map.md)

NEXT STEP:
  New project    → "Generate project skeleton"
  Existing repo  → "Run repo-scan"
```

---

## Hard rules

- Never guess a `{{variable}}` value — only use what human answered.
- Never write files before the pre-output merge check is complete.
- Never skip the completion checklist output.
- If human changes an answer after files are written: surgically update the specific token and re-output only the
  affected file.
