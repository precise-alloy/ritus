# Workflow: Execute Task — V1.0

## Trigger

Human sends task file path to the configured executor from `.ai/profiles/runtime.md` section `## AI tools in use`.

## Context to load

Read `.ai/exec-context.md` — this is your complete rules context.
Do **not** load `.ai/AGENTS.md` — that is architect context only.

## Steps

1. Read task file: TASK, PATTERN, CONTEXT, GOAL, STEPS, DONE WHEN, DOC UPDATE, COMMIT.
2. Read PRIOR CONTEXT if present.
3. Read CONTEXT files listed in the task. Grep for more if needed — no full repo scan.
4. **If task is a bug fix:** grep `docs/LESSONS.md` and `docs/DECISIONS.md` for affected module — load matching entries
   only.
5. Load applicable standards — **blocking step, not optional:**
    - Any code change → `.ai/standards/code-conventions.md`
    - New service / agent / endpoint / worker / bug fix → `.ai/standards/testing-policy.md`
    - Auth / billing / migration / tenant isolation / infra config / shared contracts → `.ai/standards/security.md`
    - Frontend component or page → `.ai/standards/ui-visual-testing.md`
    - Any STANDARD or EPIC task → `.ai/standards/definition-of-done.md`
6. If PATTERN set: read `docs/ARCHITECTURE.md` for the relevant checklist.
7. Grep to confirm all file paths before editing.
8. Implement STEPS. Positive instructions only — constraints are in `exec-context.md`.
9. Run smoke test if in DONE WHEN.
10. Run unit tests if in DONE WHEN.
11. Update docs per DOC UPDATE.
12. Validate against all loaded standards — **blocking gate before reporting done.**
13. Check every DONE WHEN checkbox.
14. If QA mode in `.ai/profiles/team.md` section `## Team config` is `task` (STANDARD/EPIC tasks): verify `.qa.md` is
    accurate — update affected features and risk if actual changes differ from what architect planned.
15. Report using output format from `exec-context.md` + COMMIT from task file.

If blocked: report `BLOCKED: <reason>`. Do not guess or improvise.

## Self-validation checklist

- [ ] Only `exec-context.md` loaded as rules context — not `.ai/AGENTS.md`
- [ ] Files compile
- [ ] Only CONTEXT files modified
- [ ] Auth pattern followed (per `exec-context.md`)
- [ ] All PATTERN checklist steps done or marked N/A
- [ ] All loaded standards hard gates passed — any failure blocks reporting done
- [ ] Soft gate skips documented with justification in DONE WHEN
- [ ] DOC UPDATE completed
- [ ] No claim made about existing code without citing file:line
- [ ] If QA mode in `.ai/profiles/team.md` section `## Team config` is `task`: `{task-name}.qa.md` exists, accurate,
  executor verified checkbox ticked
