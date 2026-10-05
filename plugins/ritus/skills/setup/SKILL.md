---
name: setup
description: Set up or reconfigure Ritus in a repository - use when the user says setup, configure, or init the workflow or Ritus, or when docs/PROJECT_CONTEXT.md is missing. Detects what it can from the repository, asks only the rest, writes the project profiles, and adds the routing block the agents read.
argument-hint: Anything you already know - team size, ticket system, base branch - so setup doesn't ask for it
---

# Setup

Configure Ritus for this repository: the profiles every skill reads its paths, commands, and conventions from,
rendered into `docs/PROJECT_CONTEXT.md`, and the routing block that tells the agent which Ritus skill to start with.
The failure to avoid is an interview about what the repository already answers. It wastes the user's time, and an
answer typed from memory can contradict the code.

## 1. Scaffold

Run `sync` in apply mode first. It creates the profile, doc, and `.ritus/` templates that are missing and never
overwrites an existing file.

## 2. Detect

Read-only. For each setting in `references/settings.md`, look where it says: the git remote, branches, recent commits,
manifests, and the environment. Note each value with its source. A value already in `docs/profiles/*.yml` stands -
someone set it.

## 3. Confirm, then ask the rest

Show one screen: each detected value and where it came from, for the user to correct. Then ask what is still missing,
one question at a time, each with its default, so an answer of "whatever you think" or a skipped question has an
outcome. Don't write anything until the last answer is in.

## 4. Write

- The three profiles in `docs/profiles/`: fill the empty fields with the answers, and the derived fields per
  `references/derived-values.md`. Drop a `model_routing` key an older version left in `runtime.yml`: Ritus no longer
  picks models.
- `docs/PROJECT_CONTEXT.md`: render it from the profiles per `references/project-context.md`.
- `docs/ARCHITECTURE.md`, if `sync` created it from the template: fill its header - the project name, and the
  language and framework. A team's own architecture doc stays as it is.
- The routing block (step 5).

When the user changes an answer after the files exist, update that field, recompute the values derived from it and
show them next to the old ones for the user to confirm, then re-render. Leave the rest.

## 5. Add the routing block

Skills start on their own less often than they should: in testing, a model handed a ticket or a bug went straight to
reading and editing code unless the project's instruction file told it which skill to start with. Add the block in
`templates/agent-routing.md` to the file each tool in `ai_tools` reads:

- Claude Code reads `CLAUDE.md` at the repository root.
- GitHub Copilot reads `.github/copilot-instructions.md` and `AGENTS.md`: use whichever exists, else create
  `AGENTS.md`.

These files belong to the team. Append the block at the end and leave the rest untouched, line endings included;
when its markers are already there, replace only what sits between them. Show the user the block and where it went.

## Output

```text
Setup complete - <project>

Written:
  docs/profiles/project.yml, team.yml, runtime.yml
  docs/PROJECT_CONTEXT.md     rendered from the profiles
  docs/ARCHITECTURE.md        header (when it was the template)
  <CLAUDE.md / AGENTS.md>     Ritus routing block

Still empty: <fields repo-scan or the team fills: source layout, auth, error handling, commands, testing, module map>

Next: <an existing codebase - run repo-scan | a new project - start with /start-ritus>
```
