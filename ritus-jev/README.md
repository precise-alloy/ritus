# ritus-jev

Coding tools for AI agents backed by [TypeSafe Jev](https://docs.typesafe.ai/introduction), exposed over MCP.
Jev is a System One model: it answers typed questions (Choice / Score / Noul) about text in about 100 ms, with
calibrated probabilities, at a fraction of an LLM's token price. ritus-jev reads files and git diffs **server-side**
and returns short, cited leads, so the agent reads only the lines that matter and spends fewer turns.

It works in any Claude Code or GitHub Copilot CLI session, and weaves into the [Ritus](../README.md) workflow
through a companion manifest when Ritus is installed.

## Tools

| Tool | Use it to | Returns |
|---|---|---|
| `sweep` | Find every passage that still states an old rule, contract, API or term after a change, in any wording | Every hit above the threshold as `path` + `lines`, the matching `line` and an excerpt, in file order, with a `count` |
| `locate` | Find where something is implemented, configured, tested or documented, or where a failure appears in a saved log | `found` / `partial` / `not_found`, ranked `path` + `lines` with a preview, and the text of confident hits |
| `check` | Verify atomic claims (DONE WHEN, acceptance criteria, "already addressed?") against files or the git diff | Per claim: `supported` / `contradicted` / `not_found` / `uncertain` / `use_search`, the method (`code` for exact phrase, count and changed-file claims; `jev` otherwise), the cited range, and an excerpt where the verdict needs a look |
| `classify` | Label many items (text, file ranges, diff hunks) | Per item: label(s), confidence, `accept` / `review`; presets `failure_kind`, `review_comment`, `change_risk`, `change_scope` |
| `ask` | Any other narrow judgment | Raw Noul / Choice / Score answers with bands |

Host tool names: Copilot CLI `jev-sweep`, `jev-locate`, `jev-check`, `jev-classify`, `jev-ask`; Claude Code
`mcp__plugin_ritus-jev_jev__sweep` and so on. Every call takes `workspace`, the absolute path of the repository.
The bundled [`jev` skill](skills/jev/SKILL.md) teaches agents when to use each tool and when a plain search is better.

How the tools use Jev follows TypeSafe's cookbooks: `sweep` screens every block with one Noul and re-checks each hit
alone (semantic find, re-ranking); `check` routes each claim first, answers exact-phrase, count and changed-file
claims in code, and judges the rest one small `{claim, passage}` Choice at a time with a confidence gate (citation
check); `locate` pairs a Choice skim with a per-candidate Noul (semantic find, re-ranking).

## Install

Requirements: [Bun](https://bun.sh) 1.4 or newer and `git` on `PATH`, and a TypeSafe API key from the
[console](https://console.typesafe.ai/keys).

Claude Code:

```text
/plugin marketplace add precise-alloy/ritus
/plugin install ritus-jev@precise-alloy-marketplace
```

GitHub Copilot CLI:

```text
/plugin marketplace add precise-alloy/ritus
/plugin install ritus-jev@precise-alloy-marketplace
```

Start a new session after installing, and approve the `jev` MCP tools when the host asks (or allow-list them).

## Enable

Put the key in the project's `.ritus/.env.local` (git-ignored by Ritus's managed ignore block):

```dotenv
TYPESAFE_API_KEY=<your key>
# Optional
TYPESAFE_DEFAULT_MODEL=jev-1.13.0
TYPESAFE_BASE_URL=https://api.typesafe.ai
HTTPS_PROXY=http://proxy.example:8080
```

The key is looked up per call: the nearest `.ritus/.env.local` from `workspace` up to the git top-level, then the
main worktree's `.ritus/.env.local` (linked worktrees do not carry ignored files), then the `TYPESAFE_API_KEY`
environment variable. The model, base URL and proxy are read only from the same place as the key, so a file checked
into a branch cannot redirect a key defined elsewhere. A `.ritus/.env.local` that git tracks (in any letter case) is
skipped and the lookup moves on to the next source; results then carry a `warning` so it can be untracked. The
`TYPESAFE_BASE_URL` must use HTTPS. When the key comes from the environment, `TYPESAFE_DEFAULT_MODEL`,
`TYPESAFE_BASE_URL` and Bun's standard `HTTPS_PROXY` handling apply from the environment too. Without a key every
tool returns `status: "disabled"` with the exact setup line and makes no network call. The default model is pinned to
`jev-1.13.0` because the thresholds are tuned against it.

Check the setup (prints the key source masked; `--ping` makes one free `GET /v1/models` call):

```bash
bun --use-system-ca <plugin-root>/dist/jev.js doctor --workspace <repo> --ping
```

## How Ritus uses it

`ritus-companion.json` registers `load` integrations, so while the Ritus workflow runs the agent loads the `jev`
skill where Jev replaces reading or catches what a search misses:

| Step | Use |
|---|---|
| requirement-analysis | when the change alters a rule, contract, API or term, `sweep` for every passage that still states the old one and list the hits in the review; `locate` when the place a behavior lives is unknown |
| task-generation | make sure a task's CONTEXT covers every `sweep` hit for a changed rule, contract, API or term |
| execute-task | `locate` failures in saved command output, and code the task's CONTEXT does not name |
| verify-task | when the task changes a rule or term, `sweep` for stale passages: hits in the task's CONTEXT files are gaps, others are observations |
| pr-review | `sweep` for passages that still state what the change replaced; `classify change_risk` on diffs with many hunks |
| address-feedback | pre-sort comments with `classify review_comment`, test "already addressed" with `check` |
| debug (Phase 1) | `locate` root-cause lines in saved logs, `classify failure_kind` |

The first real Ritus run with v0.1 showed why: its pr-review rounds 2 to final each found one more passage that still
described the replaced rule, in a different file; two sweeps over the pre-change tree return all of them in seconds.

Ritus's gates, independent verification and user approvals keep their authority: tool results are leads that the
worker confirms by reading the cited lines. Ritus core files are unchanged, and the workflow behaves identically
without this plugin or without a key.

## What is sent to TypeSafe

Only what a call needs: the query, claims, labels or questions, and the text of the files, ranges or diff hunks in
its scope. Before anything is sent:

- The default scope honors `.gitignore` (`git ls-files`); an explicitly named directory is read from disk.
- Credential and key files are never read: `.env*` (except `*.example`, `*.sample`, `*.template`), `.ritus/.env*`,
  `*.pem`, `*.key`, `id_rsa*`, `.npmrc`, `.netrc`, `credentials.*`, `secrets.*`, `.git/`, `.ssh/`, `.aws/`,
  `*.tfstate` and similar. The rule is applied to the file actually opened (after resolving symlinks, junctions and
  Windows short names), and Windows stream paths (`file::$DATA`) are rejected. Binary, vendored, minified and
  lockfiles are skipped unless named explicitly.
- Likely secrets are replaced with `[REDACTED]` (private key blocks including PGP, GitHub / AWS / Slack / Stripe /
  Google / Atlassian / GitLab / npm tokens, JWTs, `Bearer` / `Basic` credentials, URL credentials, and
  `key|secret|token|password = value` assignments such as `SECRET_KEY = '...'` or `DB_PASSWORD=...`, plus the TypeSafe
  key itself); results report a `redactions` count. Redaction is a safety net, not a guarantee: keep secrets out of
  source files.
- Only read-only `git` commands run (`ls-files`, `diff`, `rev-parse`), with argument arrays, validated refs, literal
  pathspecs and a pinned diff format. Nothing is written to the workspace; caches live in memory.

TypeSafe states that Jev is not trained on customer requests; see [TypeSafe legal](https://docs.typesafe.ai/legal)
for data processing and zero data retention terms. File content is treated as data, and every result is a lead to
confirm.

## Host notes

- Copilot CLI starts plugin MCP servers in the plugin directory without the project path, so every call passes
  `workspace` explicitly; Claude Code roots are also enforced when the host provides them.
- The server runs `bun --use-system-ca` so HTTPS works behind TLS-inspecting corporate proxies. Proxies can be set
  with `HTTPS_PROXY` in `.ritus/.env.local`.
- The five tool schemas add roughly 2.5k tokens to each session's context; disable the plugin in projects without a
  key.
- Long command output: redirect it to a file in the OS temp directory and `locate` it by absolute path.
- Every result fits a 15 KB budget, under the roughly 20 KB at which Copilot CLI diverts tool output to a temp file:
  excerpts are shortened first and the result says so in `trimmed`.
- Large scopes return `scope_too_large` with a per-directory breakdown instead of spending: `sweep` above about 400k
  tokens, `locate` above about 350k, `check` evidence above about 300k. `context` for `check` and `classify` is limited
  to 4,000 characters, `classify` takes up to 120 items, and a custom multi-label `classify` question must contain
  `{label}`.
- Diff sources: `{}` is the working tree vs HEAD plus untracked files; `{"base": "origin/main"}` is the whole branch
  (the working tree vs its merge-base with `origin/main`, committed or not); adding `head` compares commits only. A
  diff source that resolves to nothing is reported in `warnings`.
- Ritus registers the companion only when ritus-jev is installed as its own plugin. When loading it in place from a
  local checkout, point `RITUS_COMPANION_PATHS` at the `ritus-jev/` directory.

## Tuning

All question wording lives in [`server/src/questions.ts`](server/src/questions.ts) and all thresholds, budgets and
caps in [`server/src/policy.ts`](server/src/policy.ts). Starting values come from the TypeSafe cookbooks (semantic
find, re-ranking, citation check, confidence routing); adjust them against your own cases and rebuild. The model is
pinned to `jev-1.13.0`; move to a newer version deliberately, since thresholds are tuned per version.

## Development

The runtime artifact is the committed bundle `dist/jev.js` (plus `dist/THIRD_PARTY_NOTICES.txt`); Git marketplace
installs run no build. The TypeScript source and its build tooling live in `server/`, away from the plugin root, so
hosts do not install build dependencies.

```bash
cd ritus-jev/server
bun install --frozen-lockfile
bun run typecheck
bun run build     # writes ../dist/jev.js and ../dist/THIRD_PARTY_NOTICES.txt
bun run check     # fails when the committed bundle is stale
```

Every tool also runs from the command line with the same arguments and output as the MCP call, which is handy for
trying questions and thresholds:

```bash
bun --use-system-ca dist/jev.js locate --workspace <repo> --json '{"query":"where HTTP retries back off"}'
bun --use-system-ca dist/jev.js sweep --workspace <repo> --json '{"query":"a passage saying retries use a fixed delay","paths":["src","docs"]}'
bun --use-system-ca dist/jev.js check --workspace <repo> --args-file claims.json
```

Set `RITUS_JEV_DEBUG=1` to log request sizes and timings to stderr.
