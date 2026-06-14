# SKILLS-TODO.md — Tech stack registry

Auto-filled by repo-scan. Updated by agents during work when new info is discovered.

## Rule for agents

- ❓ = unknown. If a task requires this info: ask human once, then fill here + update relevant skill file.
- ✅ = confirmed. Use directly.
- When human answers an ❓: update status to ✅ and fill value immediately.

---

## Stack

Stability levels:

- `core` — stable for the life of the repo. Fill once from repo-scan. Never re-detect.
- `module` — stable per module. Fill when first touching that module.

| Role                | Stability | Status | Value |
|---------------------|-----------|--------|-------|
| Primary language    | core      | ❓      | —     |
| Runtime / framework | core      | ❓      | —     |
| Package manager     | core      | ❓      | —     |
| Build tool          | core      | ❓      | —     |
| Test framework      | core      | ❓      | —     |
| Frontend framework  | core      | ❓      | —     |
| CSS approach        | core      | ❓      | —     |
| Database            | core      | ❓      | —     |
| ORM / query builder | module    | ❓      | —     |
| Auth pattern        | module    | ❓      | —     |
| Deployment target   | module    | ❓      | —     |

**Rule:** If all rows needed for a task are `core` ✅, skip loading SKILLS-TODO.md for that task entirely.

---

## Module skill files

| Module               | Skill file               | Status |
|----------------------|--------------------------|--------|
| _filled during work_ | `.ai/skills/<module>.md` | ❓      |

---

## How agents fill this file

**From repo-scan:**

1. Detect `package.json` / `*.csproj` / `pyproject.toml` / etc. → fill Language + Package manager
2. Detect framework deps → fill Runtime / framework
3. Detect test deps → fill Test framework
4. Detect auth middleware → fill Auth pattern

**During work (when ❓ is encountered):**

1. Stop task
2. Ask human: "What is `<role>` for this project?"
3. Human answers
4. Fill value here → update status to ✅
5. Update the relevant `.ai/profiles/` or `.ai/skills/` file
6. Continue task
