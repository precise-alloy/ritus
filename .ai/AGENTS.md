# AGENTS.md — AI Workflow V1.0

> **Workflow source of truth.** Root `AGENTS.md` and `.claude/CLAUDE.md` point here.
> Project-specific configuration lives in `.ai/profiles/`.

## Profiles

Load profiles only when their scope is relevant:

| Profile                   | Purpose                                                                                                                                                                         |
|---------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `.ai/profiles/project.md` | `## Project identity`, `## Language policy`, `## Source layout`, `## Authentication`, `## Error handling`, `## Testing`, `## Build commands`, `## Project-specific constraints` |
| `.ai/profiles/team.md`    | `## Team config`, `## Branch conventions`, `## tasks/ path convention`, `## Pull request requirements`, `## Review defaults`, `## Traceability policy`                          |
| `.ai/profiles/runtime.md` | `## AI tools in use`, `## Model routing`, `## Remote API access`                                                                                                                |

---

## Role detection (run before triage — before any further context load)

Detect role from message intent. Load the rest of this file only if ARCHITECT.

**ARCHITECT** — message signals: `design` · `plan` · `architect` · `break down` · `generate tasks` ·
`review and propose` · `brainstorm` · `analyze` · `how should we` · `what's the approach` · `what should we`

→ Continue loading this file. Run triage. Generate task files or fix directly per triage level.

**EXECUTOR** — message signals: `implement` · `fix` · `build` · `add` · `create` · `write` · `refactor` ·
`update <specific thing>` · `change <specific thing>`

→ Stop loading this file. Load `.ai/exec-context.md` instead. Implement task directly.

**Default:** ambiguous message → **ARCHITECT**. Plan before acting.

**Mid-task rule:** if role becomes unclear during work — stop and ask. Never switch context mid-task silently.

---

## Triage (mandatory — before any context load)

Classify every incoming change before loading context or generating tasks.
See `.ai/workflows/generate-tasks.md` TRIAGE section for full rules.

| Level    | Criteria                                                                    | Output                           |
|----------|-----------------------------------------------------------------------------|----------------------------------|
| TRIVIAL  | Single file, no public contract change, clear validation, low blast radius  | Direct fix — no task file        |
| SIMPLE   | ≤2 files, no cross-module contract, clear path, low blast radius            | Task note: TASK + DONE WHEN only |
| STANDARD | Cross-file, design decision, public contract changed, or validation unclear | Full task file                   |
| EPIC     | Multi-session, multiple modules, new architecture pattern                   | Full task file + memory file     |

**Safety override — force STANDARD regardless of above when touching:**
auth / session / tokens · payment / billing · database migrations · tenant isolation · infra / runtime config · shared
contracts (types exported across modules)

---

## Pre-coding read order (load per classification — not always all steps)

**TRIVIAL:** `.ai/AGENTS.md` golden rules + grep target file only. Load only `.ai/profiles/project.md` section
`## Build commands` or `## Project-specific constraints` if needed.

**SIMPLE:** `.ai/AGENTS.md` + relevant sections from `.ai/profiles/project.md` + `.ai/skills/<module>.md` only.
Stale check: grep-verify 1–2 key names the skill file claims exist. If missing: flag ⚠️ before trusting.

**STANDARD / EPIC:**

1. `.ai/AGENTS.md`
2. `.ai/profiles/project.md` — load only sections relevant to touched paths, auth/error/testing, build commands, or
   project constraints
3. `.ai/profiles/team.md` — load only sections relevant to branch, PR, ticket, QA, traceability, or escalation rules
4. `.ai/profiles/runtime.md` — load only sections relevant to model/tool routing, or remote API helper
   rules
5. `docs/LESSONS.md` — grep module/file name; load matching entries only. **Load before skill files** — known failure
   patterns must inform how you read them. If no match: skip.
6. `docs/CUTOFF.md`
7. `.ai/SKILLS-TODO.md` — check ❓ rows before starting; if ❓ found: stop, ask human once, fill, update this file,
   continue
8. `.ai/skills/{module}.md` — **stale check required**: grep-verify 2+ key claims (function names, exports, types) exist
   in source before trusting. If any missing: flag ⚠️ stale, note which claims are outdated, re-read source for those
   only.
9. `docs/modules/{module}/` — only if in CUTOFF.md AND no skill file
10. `docs/ARCHITECTURE.md` — only if task involves new resource/endpoint/module
11. `.ai/memory/{branch-slug}-{feature-slug}-context.md` — only if resuming multi-session

**Token cap:** when task touches > 3 modules, load skill files only for directly modified modules. For others: grep
entry point only — do not load full skill file.

**Skill file refresh trigger:** if stale check fails on 3+ claims, rewrite the skill file from source before proceeding.
Do not patch a partially-wrong skill file — rewrite it clean.

Do not scan the entire repo.

---

## Task-first rule

Check `.ai/tasks/` for a matching task before creating new work.
If found: execute or update. Do NOT create duplicates.

---

## Golden rules

1. Triage before context load — classify first, load only what the level requires.
2. Minimal change — no unsolicited refactors.
3. Grep before edit — confirm paths exist before touching files.
4. No hallucinated features — if unclear, stop and ask.
5. One final report — no intermediate dumps.
6. Stop on errors (compile fail, test fail, 4xx/5xx).
7. Done = DONE WHEN conditions met AND applicable standards hard gates pass. Both are required.
8. Update docs only when the change affects how future humans or agents understand, navigate, or safely modify the
   system — use the doc trigger matrix in `generate-tasks.md`.
9. Task STEPS use positive instructions only.
10. Grep before claiming — before asserting any fact about existing codebase behavior, grep or read the source. If
    unverifiable in current context, say so explicitly. Never infer. Cite `file:line` when making a claim about code.

---

## Skills/ maintenance

After any task that changes a module's public interface:

- Check if `.ai/skills/{module}.md` exists
- If yes: add update to DOC UPDATE section of the task
- If no: create a stub skill file after the task completes

Skill files stay under 150 lines. Interface summary only — not a replacement for ARCHITECTURE.md.

---

## SKILLS-TODO.md discipline

When a ❓ row is encountered mid-task:

1. Stop
2. Ask human once: "What is `<role>` for this project?"
3. Human answers → fill the row → mark ✅
4. Update the relevant `.ai/profiles/` or `.ai/AGENTS.md` section
5. Continue task

Never guess a ❓ value. Never ask more than one question at a time.

---

## Model routing

See `.ai/profiles/runtime.md` section `## Model routing`.

---

## Branch & PR conventions

See `.ai/profiles/team.md` sections `## Branch conventions`, `## tasks/ path convention`, and
`## Pull request requirements`.

### DONE WHEN gate (added for all STANDARD / EPIC tasks)

```text
[ ] No claim made about existing code without citing file:line
```

---

## Standards

Load relevant standards before implementation. Match to task type — not all for every task.

| Task touches                                                                | Load                                  |
|-----------------------------------------------------------------------------|---------------------------------------|
| Any code change                                                             | `.ai/standards/code-conventions.md`   |
| Auth, billing, migrations, tenant isolation, infra config, shared contracts | `.ai/standards/security.md`           |
| New service / endpoint / worker / bug fix                                   | `.ai/standards/testing-policy.md`     |
| Frontend component or page                                                  | `.ai/standards/ui-visual-testing.md`  |
| Any STANDARD or EPIC task                                                   | `.ai/standards/definition-of-done.md` |

Validate against loaded standards before reporting done. Standards are part of DONE WHEN.

---

## Authentication

See `.ai/profiles/project.md` section `## Authentication`.

---

## Error handling

See `.ai/profiles/project.md` section `## Error handling`.

---

## Testing

Full test policy: see `.ai/standards/testing-policy.md`

Project-specific test commands and conventions: see `.ai/profiles/project.md` sections `## Testing`,
`## Test location conventions`, and `## Build commands`.

---

## Project-specific constraints

See `.ai/profiles/project.md` section `## Project-specific constraints`.

---

## Build commands

See `.ai/profiles/project.md` section `## Build commands`.

---

## Output format (mandatory)

```text
Files changed:
- path — summary

Docs updated:
- path — what changed   (or: none required)

Commit message:
type(scope): subject

- what changed and why
- key invariant enforced (if any)

Breaking: none | <what breaks>
Migration: none | <migration needed>

DONE WHEN verified: ✓ all conditions met
```

Commit types: `feat` | `fix` | `refactor` | `test` | `docs` | `chore`
