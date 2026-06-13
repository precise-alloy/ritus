# AI Routing — V1.0

## Entry point — role detection

Every message goes through role detection first. Role determines context loaded and output produced.

```text
Message received
  → Detect role from message intent

  ARCHITECT signals:
    design · plan · architect · break down · generate tasks
    review and propose · brainstorm · analyze
    how should we · what's the approach · what should we

  EXECUTOR signals:
    implement · fix · build · add · create · write
    refactor · update <thing> · change <thing>

  Ambiguous → ARCHITECT (default — plan before acting)
```

---

## Context loaded by role

| Role                   | Loads                                                                   | Does NOT load     |
|------------------------|-------------------------------------------------------------------------|-------------------|
| **ARCHITECT**          | Full `.ai/AGENTS.md` + read order per triage level                      | `exec-context.md` |
| **EXECUTOR**           | `exec-context.md` + task CONTEXT files + standards                      | `.ai/AGENTS.md`   |
| **EXECUTOR (bug fix)** | `exec-context.md` + grep `LESSONS.md` + grep `DECISIONS.md` + standards | `.ai/AGENTS.md`   |

---

## Architect flow

```text
ARCHITECT role
  → Load .ai/AGENTS.md
  → Triage (TRIVIAL / SIMPLE / STANDARD / EPIC)

  TRIVIAL:
    → Implement directly (no task file)
    → Human reviews diff → commit → push

  SIMPLE:
    → Generate 2-section task note
    → Human runs → executor
    → Human reviews diff → commit → push

  STANDARD / EPIC:
    → Generate task files + execution plan
    → Human runs code-edit group → executor
    → Human runs shell group → terminal (if needed)
    → Human reviews diff → batch commit → push
```

## Executor flow

```text
EXECUTOR role
  → Load exec-context.md
  → Read task file (TASK, CONTEXT, STEPS, DONE WHEN, DOC UPDATE, COMMIT)
  → Load applicable standards (per exec-context.md standards table)
  → [Bug fix only] grep LESSONS.md + DECISIONS.md for affected module
  → Implement STEPS
  → Validate all DONE WHEN + standards gates
  → Report using exec-context.md output format
```

---

## Roles

| Actor                      | Role                                                                     | Context loaded                               |
|----------------------------|--------------------------------------------------------------------------|----------------------------------------------|
| Architect agent            | Design, triage, task generation, execution plan                          | `.ai/AGENTS.md` + triage-level read order    |
| Executor agent             | Implement task directly when message is execution-intent                 | `exec-context.md` + task CONTEXT + standards |
| Configured code-edit tools | Code edits — see `.ai/profiles/runtime.md` section `## AI tools in use`  | `exec-context.md` + task CONTEXT + standards |
| Shell runner               | Shell tasks — see `.ai/profiles/runtime.md` section `## AI tools in use` | Task file only                               |
| Human                      | Gate: watch scope, diff review, auth/schema skim, PR approve             | —                                            |

---

## Model routing

See `.ai/profiles/runtime.md` section `## Model routing`.

**Rule:** Never upgrade model without updating `.ai/profiles/runtime.md` section `## Model routing`.

---

## Human gates

| Gate           | When                           |
|----------------|--------------------------------|
| Watch executor | Always — abort if scope drifts |
| Diff review    | Before every commit            |
| Task skim      | Auth / schema tasks only       |

---

## Setup flow (one-time per project)

```text
Human: "Setup AI workflow for new project"
  → Run .ai/workflows/setup.md
  → Interview (10 questions, fewer for solo)
  → Generate: .ai/AGENTS.md + .ai/profiles/*.md + exec-context.md + routing.md + SKILLS-TODO.md + ARCHITECTURE.md

  NEW PROJECT:
    → Generate skeletons with placeholders
    → SKILLS-TODO.md all ❓
    → Fill progressively during work

  EXISTING PROJECT:
    → Run .ai/workflows/repo-scan.md
    → Pre-flight conflict check → human confirms
    → Merge/replace per strategy → fill SKILLS-TODO.md + exec-context.md from scan
```

---

## File merge strategy (existing projects)

| File/folder           | On adopt                                                                                                                             |
|-----------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| `.ai/AGENTS.md`       | Workflow-only source of truth — replace/merge only when upgrading the workflow (keep project/team/runtime config in `.ai/profiles/`) |
| `.ai/profiles/*.md`   | Merge filled values, including project constraints and runtime/team config                                                           |
| `.ai/exec-context.md` | Auto-generated - regenerate from project profile + reusable executor rules after merge                                               |
| `.ai/workflows/*.md`  | Replace                                                                                                                              |
| `.ai/routing.md`      | Replace                                                                                                                              |
| `.ai/SKILLS-TODO.md`  | Generate fresh                                                                                                                       |
| `.ai/skills/*.md`     | Append only                                                                                                                          |
| `.ai/tasks/**`        | Never touch                                                                                                                          |
| `.ai/memory/**`       | Never touch                                                                                                                          |
| `docs/**`             | Never touch                                                                                                                          |
| `.ai/module-map.md`   | Never touch                                                                                                                          |

---

## Optional scripts

```bash
pnpm validate-all     # batch EPIC sanity check
pnpm docs-sync        # pre-PR doc check
pnpm lint-workflows   # workflow drift check
```

---

## Doc paths

| What            | Path                     |
|-----------------|--------------------------|
| Module registry | `docs/CUTOFF.md`         |
| Architecture    | `docs/ARCHITECTURE.md`   |
| Decisions       | `docs/DECISIONS.md`      |
| Changelog       | `docs/CHANGELOG.md`      |
| Lessons         | `docs/LESSONS.md`        |
| Skills          | `.ai/skills/{module}.md` |
