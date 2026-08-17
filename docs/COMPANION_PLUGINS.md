# Companion Plugins & Skills

Companion plugins and skills extend the Ritus workflow **without editing any core Ritus files**.
You ship a small `ritus-companion.json` manifest; at the start of every session a Ritus hook
discovers it and injects a compact **Ritus Companion Registry** into the agent's context - one line
per companion, pointing at the manifest on disk. When the agent builds the workflow TODO it reads
each manifest and applies your instructions at the workflow points you describe.

Core rule: **Ritus core owns the workflow; companion manifests own their registrations.**
You never patch a core skill or `dispatch.md` per companion — you write a manifest.

## How it works

1. On `SessionStart`, Ritus runs `scripts/companion-bootstrap.ts` (wired through `hooks/hooks.json`).
2. The hook discovers every `ritus-companion.json` it can find (see [Discovery](#discovery)).
3. The hook returns one **Ritus Companion Registry** section as `additionalContext`: one line per
   companion with its manifest path - your prompts stay on disk, out of session-start context.
4. When the agent builds or updates the workflow TODO, it reads each manifest and applies the
   integrations at their workflow points (see "Companion weaving" in `skills/shared/dispatch.md`).

> Requirements: [Bun](https://bun.sh) must be on `PATH`. The registry refreshes on each configured
> `SessionStart` lifecycle event (`startup`, `resume`, `clear`, `compact`, `fork`) — i.e. at session
> start and again after compaction.

## Manifest format

Create a file named `ritus-companion.json`:

```json
{
  "name": "my-companion",
  "integrations": [
    {
      "skill": "my-skill",
      "prompt": "When a task changes X, after task-generation: dispatch the my-skill subagent."
    }
  ]
}
```

| Field                   | Type   | Required | Description                                                       |
|-------------------------|--------|----------|-------------------------------------------------------------------|
| `name`                  | string | yes      | Short companion name; used as the registry heading.               |
| `integrations`          | array (nonempty) | yes | One entry per skill you want to wire into the workflow (at least one entry). |
| `integrations[].skill`  | string | yes      | The skill's name — identifies the integration.                    |
| `integrations[].prompt` | string | yes      | A short instruction, read verbatim from the manifest when the agent builds the workflow TODO (the where / when / what). |

Each `prompt` is **read verbatim** from your manifest when the TODO is built - keep it short. Two common shapes:

- **Add a step** at a boundary —
  `When <condition>, <before/after a step>: dispatch the <skill> subagent.`
- **Add knowledge** to a running step —
  `While <worker skill> runs<, on <condition>>: load the <skill> skill and apply it.`

Use Ritus's own step names so the agent can place your step precisely:
`triage → ticket-review → task-generation → execute-task → verify-task → pr-review → wrap-up`.

## Discovery

The hook looks for `ritus-companion.json` in three places:

1. **Your project / repo** — a `ritus-companion.json` at the **repo root**. Only the root is
   checked (`<repo>/ritus-companion.json`); subfolders are not scanned.
2. **Installed companion plugins** — sibling plugins in the same marketplace (both the Claude and
   Copilot install layouts are handled).
3. **Explicit override** — set `RITUS_COMPANION_PATHS` to a list of files or directories,
   separated by the OS path-list separator (`;` on Windows, `:` elsewhere).

All discovered manifests are merged; up to 25 are used.

## Placement examples

- Project root: `./ritus-companion.json` (must be at the repo root — subfolders are not scanned)
- Companion plugin: `<plugin-root>/ritus-companion.json`

## Example: ritus-frontend

The `ritus-frontend` companion wires browser verification into the workflow:

```json
{
  "name": "ritus-frontend",
  "integrations": [
    {
      "skill": "e2e-plan",
      "prompt": "When a task changes frontend files, after task-generation: dispatch the e2e-plan subagent."
    },
    {
      "skill": "visual-verify",
      "prompt": "When a task changes frontend files, before pr-review: dispatch the visual-verify subagent; block on failure."
    }
  ]
}
```

Its registry entry renders as:

```text
- ritus-frontend (2 integrations): <plugin-root>/ritus-companion.json
```

The agent reads the manifest itself when it builds the workflow TODO, so the full prompts reach
context only in sessions that actually run the Ritus workflow.

## Example: adding knowledge to a worker skill

A companion prompt can also target a **worker skill** (`execute-task`, `verify-task`,
`pr-review`, etc.) so its skill is loaded as extra knowledge *while that step runs*, instead of
adding a separate step. Use `load` (one skill reading another as a standard) rather than
`dispatch`, and name the worker skill as the point:

```json
{
  "name": "acme-standards",
  "integrations": [
    {
      "skill": "api-conventions",
      "prompt": "While execute-task runs on API or endpoint code, load the api-conventions skill and follow its rules."
    },
    {
      "skill": "security-review",
      "prompt": "During pr-review, load the security-review skill and apply its checklist before giving a verdict."
    },
    {
      "skill": "coverage-standards",
      "prompt": "While verify-task runs, load the coverage-standards skill and hold the change to its coverage bar."
    }
  ]
}
```

Its registry entry:

```text
- acme-standards (3 integrations): <plugin-root>/ritus-companion.json
```

Use this shape when the companion is a **standard** (conventions, checklist, or domain knowledge)
that an existing step should honor — not a new step to schedule. The agent adds a TODO to load
and apply the skill when that worker step runs.

## Verifying

Start a new session and confirm a `## Ritus Companion Registry` section appears in context, listing
one line per companion with its manifest path. On the CLIs you can inspect the hook output directly:

- **Claude:** `claude -p ping --output-format stream-json --include-hook-events --verbose` →
  look for the `SessionStart` `hook_response`.
- **Copilot:** run with `--log-level debug --log-dir <dir>` and grep the log for `hook stdout`.

If nothing appears: ensure `bun` is on `PATH`, the manifest is valid JSON with `name` and
`integrations`, and that you started a **new** session.
