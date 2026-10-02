---
name: sync
description: Create the Ritus project files that are missing, without the setup interview - use after installing or upgrading the plugin, or when the user asks which workflow files are missing, or to check, sync, or scaffold them. Never overwrites an existing file. For first-time configuration, use setup.
argument-hint: Provide whether to check only or apply missing project files
---

# Sync

## When to use

When you need to scaffold project files without running the full setup interview:

- After installing the plugin for the first time
- After a plugin upgrade adds new template files
- To check if any project files are missing

## Commands

The sync script lives at `skills/sync/script/sync.ts` relative to the plugin root. To find the correct path,
use the skill directory you loaded this file from - the script is at `script/sync.ts` next to this SKILL.md.

### Check (report only, no writes)

```bash
bun "<path-to-this-skill>/script/sync.ts" --check
```

### Apply (create missing files)

```bash
bun "<path-to-this-skill>/script/sync.ts" --apply
```

Replace `<path-to-this-skill>` with the absolute path of the directory containing this SKILL.md file.

## Behavior

- Creates files that don't exist in the project from plugin templates
- **Never overwrites existing files** - all project files are user-owned
- Reports what was created and what was skipped

## Output

Report the sync result to the user. If files were created, list them. If all files exist, say so.

## Handoff

- **Report:** the files created or verified.

If this was the first sync (many files created), suggest running `setup workflow` / `/setup` to fill the profile
data with project-specific values.
