---
name: sync
description: Use when scaffolding or checking project files — creates missing docs, profiles, scripts without the full setup interview. TRIGGER — invoke when user says "check project files", "sync files", "what files am I missing", or after a plugin upgrade. For first-time setup with interview, use setup instead
argument-hint: Provide whether to check only or apply missing project files
---

# Sync

## When to use

When you need to scaffold project files without running the full setup interview:

- After installing the plugin for the first time
- After a plugin upgrade adds new template files
- To check if any project files are missing

## Commands

The sync script lives at `skills/sync/script/sync.cjs` relative to the plugin root. To find the correct path,
use the skill directory you loaded this file from — the script is at `script/sync.cjs` next to this SKILL.md.

### Check (report only, no writes)

```bash
node "<path-to-this-skill>/script/sync.cjs" --check
```

### Apply (create missing files)

```bash
node "<path-to-this-skill>/script/sync.cjs" --apply
```

Replace `<path-to-this-skill>` with the absolute path of the directory containing this SKILL.md file.

## Behavior

- Creates files that don't exist in the project from plugin templates
- **Never overwrites existing files** — all project files are user-owned
- Reports what was created and what was skipped

## Output

Report the sync result to the user. If files were created, list them. If all files exist, say so.

## Next

If this is the first time syncing (many files created), suggest running `setup workflow` or `/setup` to fill the profile
data with project-specific values.
