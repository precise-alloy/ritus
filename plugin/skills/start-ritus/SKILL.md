---
name: start-ritus
description: Start here with Ritus - use when the user is new to Ritus or asks what it does, says "start ritus", "how do I use this workflow", or "which Ritus skill do I need", wants to resume Ritus work on the current branch, or has a request and it is unclear which Ritus workflow fits. Checks the project's setup, orients in one screen, then hands off to the right skill.
argument-hint: What you want to do (optional)
---

# Start Ritus

The front door. Orient the user, then hand off: the specialist skills do the work and trigger on their own, so this
skill stays short and never sits in front of them as a gate.

## Look before you ask

These checks are cheap and read-only. Their answers decide what to say, so run them before asking anything:

- **Setup.** No `docs/PROJECT_CONTEXT.md` means Ritus is not set up in this repository. Planning, review, and wrap-up
  read their paths, naming, and commands from that file, so `setup` comes first: with no request it is the next step;
  with one, say why in a line and offer to run `setup` before it. If the user would rather go ahead, hand off.
- **Routing.** Set up, but no `ritus:routing` block in `CLAUDE.md`, `AGENTS.md`, or `.github/copilot-instructions.md`,
  means the specialist skills will rarely start on their own. Mention it in a line and offer to add the block
  (`skills/setup/SKILL.md` step 5).
- **Work in progress.** A `docs/tasks/{branch-slug}/` folder for the current branch (`/` replaced by `-`) means a run
  already started. Offer to resume: read the plan the task files point to, the task files (a debug case file,
  `investigation-*.md`, counts as one), `exploration.md`, and for an EPIC its memory file in `docs/memory/`. Each
  file's `Status` line says how far it got: the first one not `verified` is next, and an `implemented` one gets its
  check before anything else (older files have no Status line - judge from the diff and ask). `escalated` means a fix
  loop stopped for a design decision: present its options, and resume nothing until the user picks one. Changes are
  often uncommitted until the end, so a `todo` task whose files `git status` shows as changed was interrupted - tell
  its executor. Once the user agrees, rebuild the driving TODO for what is left (its shapes are in
  `skills/ticket-review/SKILL.md` step 7, and in `skills/debug/SKILL.md` for a case file).
- **Remote access.** `.ritus/.env.local` matters only for ticket URLs and PRs. Mention it when the request needs it.

## Hand off

If the user already said what they want, name the skill in one line and invoke it. Skip the tour.

| The user has | Skill |
|---|---|
| a ticket (Jira, Azure DevOps, GitHub), a feature request, or a change to make | `ticket-review` |
| a bug, error, crash, or failing or flaky test | `debug` |
| an idea, a choice, or a design to think through | `brainstorm` |
| review comments on a PR | `address-feedback` |
| a branch, diff, or PR to review | `pr-review` |
| finished work to close out | `wrap-up` |
| a shipped change to understand, or "quiz me" | `comprehension` |
| a repository without Ritus | `setup` |
| a plugin upgrade, or Ritus files missing | `sync` |
| a stack or conventions to detect | `repo-scan` |
| existing notes or docs to bring in | `migrate-docs` |

When two fit, pick the one that decides the approach: `debug` for a bug whose cause is unknown, even when a ticket
exists, and `brainstorm` while the user is still unsure what to build.

## Orient a new user

With no request, show one screen adapted to what you found, and end with the single most useful next step (usually
`setup`, or resuming the run). Cover:

- **What Ritus does.** It plans before it codes, scales the process to the risk of the change, and has each task
  checked by an agent that did not write it.
- **How much process.** Summarize `skills/shared/levels.md` in one line per level, including the areas that are never
  below STANDARD and how the user can lower or raise the level.
- **What needs the user.** Above TRIVIAL, nothing is implemented until they approve the plan. Commits stay theirs.
- **Where things land.** Plans in the ticket reviews path from `docs/PROJECT_CONTEXT.md`, tasks in
  `docs/tasks/{branch-slug}/`, lessons and decisions in `docs/LESSONS.md` and `docs/DECISIONS.md`.
- **Their rules win.** Their CLAUDE.md or AGENTS.md and `docs/PROJECT_CONTEXT.md` override Ritus defaults.

## When not to

- Don't give the tour to someone who asked for work. Hand off.
- Don't interview. Ask at most one question, and only when the next step depends on the answer.
- Don't restate other skills' rules here; they own them, and a copy drifts.
