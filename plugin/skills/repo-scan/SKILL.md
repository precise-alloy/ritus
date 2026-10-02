---
name: repo-scan
description: Detect a repository's stack, commands, conventions, and module map into the Ritus profiles - use when the user asks to scan the repo, detect the stack, or analyze the codebase, or right after setup on an existing codebase. Read-only until the user confirms what it found.
argument-hint: The repository path or the areas to scan, if not the whole current workspace
---

# Repo Scan

Fill the Ritus profiles and convention docs from what the code shows, not from memory. Every later run reads these
values - a wrong build command or auth pattern in `docs/PROJECT_CONTEXT.md` misleads each of them - so each value
comes with its evidence, and a value you can't establish is marked `❓` instead of guessed.

## What to find

Look at manifests, config, entry points, and a sample of files - not the whole tree.

| Area | Fields (`docs/profiles/project.yml` unless noted) | Where to look |
|---|---|---|
| Stack | `primary_language`, `framework`, `stack.*`: package manager, build tool, test framework, frontend framework, CSS approach, database, ORM, deployment target | Manifests, lockfiles, dependency lists, `Dockerfile`, CI workflows |
| Source layout | `source_layout.*`: business logic, web/API, models, integrations, frontend, generated | The top-level source directories and what their entry files do |
| Commands | `build_commands.*`: build, typecheck, test, lint | Package scripts, `Makefile`, CI steps |
| Authentication | `authentication.*`: pattern, token verification, tenant scoping, role model | The 2 or 3 files that match auth, session, token, or middleware |
| Error handling | `error_handling`, in 2 or 3 lines | An API handler and a background job |
| Testing | `testing.pattern`, `testing.location_conventions` | Test config and a sample of test files |
| Module map | `module_map`: one entry per real module, with a `misc` catch-all only if real files remain | Source directories; never invent a module |
| Test conventions | `docs/TEST_CONVENTIONS.md`: framework and assertions, naming, mocking, fixtures, async, the mutation tool if one is configured | 5 to 10 test files, and the manifests' dev dependencies |
| Code conventions | `docs/CODE_CONVENTIONS.md`: types, naming, module structure, error handling, logging, stack-specific rules | 5 to 10 source files across directories |
| Undocumented modules | `docs/CUTOFF.md`: one "source only - read directly" row per module | The module map |

When the codebase is inconsistent, take the dominant pattern and note the exceptions.

## Confirm before writing

Present the report and wait for the user's confirmation:

- Each value found, with its evidence (a file, or `file:line`).
- Each `❓`, with the one question that would settle it. Ask each of them once; an unanswered one stays empty.
- Each value that differs from one already in the profiles: both, for the user to choose. Until they do, the
  existing value stays.
- The files you will write, and the existing ones you will leave alone: `docs/tasks/`, `docs/memory/`,
  `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, `docs/LESSONS.md`.

## Write

After confirmation:

- `docs/profiles/project.yml`: fill empty fields. Replace a value already set only where the user chose the detected
  one at the gate.
- `docs/CODE_CONVENTIONS.md`, `docs/TEST_CONVENTIONS.md`: fill empty sections; a section you couldn't establish gets
  `<!-- Not detected - fill manually -->`.
- `docs/CUTOFF.md`: append new modules, never remove a row.
- `docs/PROJECT_CONTEXT.md`: re-render it from the profiles per `skills/setup/references/project-context.md`.

Write nothing else.

## Output

```text
Repo scan - <project>
Found: <field> = <value> (<evidence>), one per line
Needs an answer: <field> - <question>, one per line (or none)
Written: <files>
Left alone: <files>
```
