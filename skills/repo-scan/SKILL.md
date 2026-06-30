---
name: repo-scan
description: Use when user says "run repo-scan", "scan repo", "detect my stack", "analyze my codebase", "what framework am I using", or "what's my tech stack" — detects stack, conventions, and patterns from existing codebase
---

# Repo Scan

## When to use

Run when human says `run repo-scan` or `scan repo`, or after setup completes for an existing project.

---

## Behavior rules

- Grep and read entry points only — do not scan the full repo
- **Steps 1–8 are read-only** — collect findings in your working notes, do NOT write any files yet
- **Step 9** presents the scan report for human review and blocks on confirmation
- Only write files AFTER human confirms the findings (Step 10)
- Fill what you can detect with confidence; mark `❓` for anything ambiguous
- Never guess — if detection is unclear, leave `❓` and note what to ask human

---

## Step 1 — detect stack

Run these checks in parallel:

| Check | Command | Fills |
| --- | --- | --- |
| Language | Look for `package.json`, `pyproject.toml`, `*.csproj`, `go.mod`, `Cargo.toml`, `pom.xml` | Primary language |
| Runtime / framework | Read deps from detected manifest | Runtime / framework |
| Package manager | Check for `pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`, `poetry.lock`, `uv.lock` | Package manager |
| Build tool | Check `scripts` in package.json or `Makefile`, `justfile`, `build.gradle` | Build tool |
| Test framework | Grep deps for `jest`, `vitest`, `pytest`, `go test`, `rspec`, `junit` | Test framework |
| Frontend framework | Grep deps for `react`, `vue`, `svelte`, `angular`, `next`, `nuxt` | Frontend framework |
| CSS approach | Grep deps for `tailwind`, `styled-components`, `emotion`, `sass`, `css-modules` | CSS approach |
| Database | Grep deps or config for `pg`, `mysql2`, `sqlite3`, `mongodb`, `prisma`, `drizzle` | Database |
| ORM / query builder | Grep deps for `prisma`, `drizzle`, `typeorm`, `sequelize`, `sqlalchemy`, `knex` | ORM / query builder |
| Deployment target | Look for `Dockerfile`, `fly.toml`, `vercel.json`, `railway.toml`, `.github/workflows/` | Deployment target |

Collect detected values (do NOT write yet — present in scan report first). Use EXACT field names from the schema:

```yaml
primary_language: <detected>
framework: <detected>
stack:
  package_manager: <detected>
  build_tool: <detected>
  test_framework: <detected>
  frontend_framework: <detected>
  css_approach: <detected>
  database: <detected>
  orm: <detected>
  deployment_target: <detected>
```

Mark each found value. Mark each not found `❓` with a note of what to ask.

---

## Step 2 — detect auth pattern

```text
1. Grep for: middleware, auth, jwt, session, cookie, bearer, token, passport, nextauth, clerk, supabase
2. Read the top 2–3 matching files
3. Identify:
   - Auth mechanism (JWT / session cookie / API key / OAuth / third-party)
   - Where verification happens (middleware vs per-handler)
   - How tenant/workspace scoping is passed (session claim vs request body vs header)
   - Role/permission model if any
4. Collect authentication findings (do NOT write yet). Use EXACT schema names:
   authentication:
     pattern: <detected>
     token_verification: <detected>
     tenant_scoping: <detected>
     role_model: <detected>
5. If ambiguous: fill what is clear, mark rest ❓
```

---

## Step 3 — detect error handling

```text
1. Grep for: catch, error, throw, HttpException, APIError, logger, log.error
2. Read 1–2 representative files (API handler + background job if both exist)
3. Identify:
   - API error response shape
   - Logging approach (structured vs console)
   - Background job failure behavior
4. Collect error_handling finding (do NOT write yet) with a concise 2–3 line description
5. If inconsistent across the codebase: note the inconsistency, pick the dominant pattern
```

---

## Step 4 — detect test setup

```text
1. Read package.json scripts (or equivalent in detected build tool)
2. Extract: build, typecheck, test, lint commands
3. Collect build command findings (do NOT write yet):
   build_commands:
     build: <detected>
     typecheck: <detected>
     test: <detected>
     lint: <detected>
4. Look for test config files: jest.config.*, vitest.config.*, pytest.ini, etc.
5. Identify test conventions: unit vs integration separation, mock strategy, DB usage
6. Collect testing finding with the key rules (2–4 bullet points max)
7. Collect test convention findings for `docs/TEST_CONVENTIONS.md` (do NOT write yet):
   - Framework: detected test framework + assertion style (e.g., "bun:test with expect()")
   - Naming: sample 5–10 test files to detect naming pattern (e.g., "MethodName_Scenario_Expected")
   - Mocking: detect mock strategy from test files (e.g., "vi.mock() for external deps")
   - Fixtures: check for test helper/factory directories
   - Async: detect async test patterns (async/await, done callbacks, etc.)
   - If a convention cannot be confidently detected, leave it with `<!-- Not detected — fill manually -->`
```

---

## Step 5 — detect code conventions (collect for `docs/CODE_CONVENTIONS.md`)

Based on what was detected in Steps 1–4, collect findings for `docs/CODE_CONVENTIONS.md` (do NOT write yet):

```text
1. Read `docs/CODE_CONVENTIONS.md`

2. Fill "## Type system" based on detected language:
   - Read 2–3 representative source files to detect type usage patterns
   - Identify: strict mode, type annotation style, type export patterns
   - Write the dominant patterns as bullet points

3. Fill "## Naming" table:
   - Sample 5–10 source files across different directories
   - Detect: file naming (kebab-case, PascalCase, snake_case), class naming, function naming,
     variable naming, constant naming
   - Fill each row in the naming table with the detected convention

4. Fill "## Module structure":
   - From Step 7 module map + source directory structure
   - Detect: entry point patterns, import structure, layer separation
   - Write 3–5 bullet points describing the project's module conventions

5. Fill "## Error handling" table:
   - From Step 3 error handling detection
   - Map findings to the context/rule rows

6. Fill "## Logging":
   - Grep for logging imports (winston, pino, bunyan, console, log4j, serilog, slog)
   - Read 1–2 files with logging to detect: structured vs unstructured, correlation IDs, log levels
   - Write 2–4 bullet points

7. Fill "## Stack-specific rules":
   - Based on detected framework/ORM/tools from Step 1
   - Read framework config files and 1–2 usage examples
   - Write framework-specific conventions
```

If a section cannot be confidently filled, leave it with `<!-- Not detected — fill manually -->` instead of guessing.

---

## Step 6 — prepare docs/PROJECT_CONTEXT.md rendering

Note: `docs/PROJECT_CONTEXT.md` will be rendered from `.yml` data in Step 10 after human confirms findings.

---

## Step 7 — build module map

```text
1. List top-level directories in src/ (or equivalent source root)
2. For each directory: infer its domain from name + a quick grep of its entry file
3. Collect module map entries (do NOT write yet):
   module_map:
     - human_phrase: <human phrase>
       kebab_case_name: <kebab-case-name>
     - human_phrase: default
       kebab_case_name: misc
4. Do not invent modules — only map what exists
```

---

## Step 8 — prepare CUTOFF.md entries

```text
1. For each module identified in Step 7:
   - Prepare a row for the "Undocumented" table in docs/CUTOFF.md (do NOT write yet)
   - Status: "source only — read directly"
2. Leave "Documented" table empty
```

---

## Step 9 — pre-flight conflict check

Before merging any workflow files, check:

```text
1. Are there existing docs/tasks/ or docs/memory/ files?
   → If yes: never touch them — list them as "preserved"
2. Does docs/ contain existing ARCHITECTURE.md, DECISIONS.md, LESSONS.md?
   → If yes: never touch them — list as "preserved"
```

Output conflict report. **Wait for human confirmation before writing any files.**

---

## Step 10 — write findings and apply merge strategy

After human confirms, write ALL collected findings from Steps 1–8:

1. Write stack + auth + error handling + build commands + testing to `docs/profiles/project.yml`
2. Write code conventions to `docs/CODE_CONVENTIONS.md`
3. Write test conventions to `docs/TEST_CONVENTIONS.md`
4. Write module map entries to `docs/profiles/project.yml` `module_map` field
5. Populate `docs/CUTOFF.md` skeleton
6. Render `docs/PROJECT_CONTEXT.md` from `.yml` data

Then apply merge strategy (for existing projects adopting the workflow):

| File/folder | Action |
| --- | --- |
| `docs/PROJECT_CONTEXT.md` | Render from `.yml` data |
| `docs/profiles/*.yml` | Merge filled values — preserve existing user data |
| `docs/tasks/**` | Never touch |
| `docs/memory/**` | Never touch |
| `docs/CODE_CONVENTIONS.md` | Merge — repo-scan fills, user refines |
| `docs/TEST_CONVENTIONS.md` | Merge — repo-scan fills, user refines |
| `docs/CUTOFF.md` | Append new modules — never remove existing |
| `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, `docs/LESSONS.md` | Never touch — user-owned |

---

## Output — scan report

After completing all steps, output:

```text
## Repo scan complete — {{PROJECT_NAME}}

### Stack detected (written to docs/profiles/project.yml)
✅ Language: <value>
✅ Framework: <value>
✅ Package manager: <value>
... (all ✅ rows)

### Needs human input (❓ rows)
❓ <field>: <what was ambiguous and why>
...

### docs/profiles/project.yml filled
✅ Auth pattern: <summary>
✅ Error handling: <summary>
✅ Build commands: <list>
✅ Test pattern: <summary>
✅ Module map: <count> modules

### docs/PROJECT_CONTEXT.md rendered
✅ Generated from filled .yml data

### Files preserved (not touched)
- docs/tasks/** — N task files
- docs/memory/** — N memory files
- docs/** — N docs files

### Conflicts found (requires human decision)
- <file>: <conflict description>
... (or: none)

Next step: resolve ❓ rows, then begin work.
```

---

## Hard rules

- Never write files before outputting the conflict report and receiving human confirmation
- Only write to `docs/profiles/`, `docs/PROJECT_CONTEXT.md`, `docs/CODE_CONVENTIONS.md`, `docs/TEST_CONVENTIONS.md`,
  and `docs/CUTOFF.md` — never touch `docs/tasks/`, `docs/memory/`, or other user-created docs
- Never guess `❓` values — ask human once per unknown
- Scan is read-only until Step 9
