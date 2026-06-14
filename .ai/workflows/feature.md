# Workflow: Feature — V1.0

## Steps

1. Triage first — classify as TRIVIAL / SIMPLE / STANDARD / EPIC per generate-tasks.md TRIAGE section. Apply safety
   override if needed.
2. Load context per classification level only — do not default to full read order.
3. Check SKILLS-TODO.md for ❓ rows (STANDARD/EPIC only) — fill before proceeding.
4. Apply pattern matching from ARCHITECTURE.md if new resource/endpoint/module (STANDARD/EPIC only).
5. Generate task files using generate-tasks.md (SIMPLE: task note only; TRIVIAL: skip).
6. Output execution plan + batch commit message (STANDARD/EPIC only).
7. Human executes per plan. Watch scope.
8. Human reviews diff → commits → pushes.
9. Log in CHANGELOG.md. Delete memory file if EPIC done.

## Rules

- No executor in task files.
- Positive instructions only in STEPS.
- Tests inline in DONE WHEN — not separate tasks.
- Execution plan is mandatory output.