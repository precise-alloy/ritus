# Workflow: Bugfix — V1.0

## Steps

1. Read `.ai/AGENTS.md` and relevant skill/module docs.
2. Identify exact failing path — error, status code, stack trace.
3. Grep to find root cause. No assumptions.
4. Check `docs/LESSONS.md` — is a known dangerous pattern involved?
5. Check `docs/DECISIONS.md` — is a known constraint being violated?
6. Generate scoped fix task using `generate-tasks.md`. DONE WHEN: bug no longer reproduces + smoke test passes.
7. Output execution plan (usually single task).
8. Human executes. Minimal fix — abort if scope expands.
9. Commit with root cause in body.

## Rules

- Touch only the failing path.
- If bug = missing auth/guard → add rule to `.ai/AGENTS.md` + log in `docs/DECISIONS.md`.
- If same pattern appears twice → add as golden rule in `.ai/AGENTS.md`.
- If fix reveals a pattern that must never repeat → add a LESSON entry to `docs/LESSONS.md`. Not every bug — only
  dangerous patterns.