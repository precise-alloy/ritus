---
name: jev
description: Use when you need to find where something is implemented, configured, tested or documented without reading whole files; locate the failure in long command output; check whether code or the git diff satisfies stated conditions (DONE WHEN, acceptance criteria, already-addressed review comments); or triage many failures, review comments or diff hunks. Uses the ritus-jev MCP tools locate, check, classify and ask, backed by TypeSafe Jev.
argument-hint: Describe what to find, verify or classify
---

# Jev coding tools

The ritus-jev MCP server gives you four tools backed by TypeSafe Jev, a fast judgment model. Each tool reads files
and git diffs itself and returns short, cited leads, so you read only the lines that matter and spend fewer turns.

Tool names by host:

- Copilot CLI: `jev-locate`, `jev-check`, `jev-classify`, `jev-ask`
- Claude Code: `mcp__plugin_ritus-jev_jev__locate` and the same pattern for `check`, `classify`, `ask`

## Every call

- Pass `workspace` as the absolute path of the repository you are working in.
- Write queries, claims and labels in English; Jev is most accurate in English.
- Treat results as leads: read the cited `path` + `lines` (or the included `text`) before you state a fact about the
  code, and cite that `file:line`.
- Act on `status`:
  - `ok` - use the result.
  - `disabled` - the tools are off for this workspace (the `hint` says why and how to enable them); use your ordinary
    search and read tools for the rest of the session.
  - `scope_too_large` - narrow `paths` using the returned `breakdown`, or add `terms`, then call again.
  - `rate_limited` or `unavailable` - continue with ordinary tools; retry later only when the answer still matters.
  - `auth_error` - TypeSafe rejected the key; tell the user once, then continue with ordinary tools.
  - `input_error` - fix the argument named in `error` and call again.
- When a result carries a `warning` (for example a key file that git tracks), tell the user once.

## Choose the tool

| You need | Tool |
|---|---|
| Where a behavior, setting, test or doc lives | `locate` |
| Whether code or the diff satisfies specific statements | `check` |
| Labels for many items (failures, review comments, diff hunks) | `classify` |
| Another narrow judgment over some text | `ask` |

- Use grep or LSP when you know the exact identifier or string; use `locate` when you know the behavior but not its
  name or place.
- Read small files you are about to edit directly.

## Recipes

### Find, then read

1. Call `locate` with a plain-English `query`. Scope large repositories with `paths` (directories or globs) and
   optional literal `terms`.
2. `found`: the top hits include their text - work from it and read around a hit only when you need more.
3. `partial` or `not_found`: widen or change the scope once, then conclude the behavior is absent.

### Long command output

1. Redirect verbose output to a temp file, for example `npm test *> "$env:TEMP\ritus-test.log"` in PowerShell or
   `npm test > /tmp/ritus-test.log 2>&1` in a POSIX shell, and read only the exit code.
2. Call `locate` with `paths: ["<absolute path of that file>"]` and a query such as "the first failing test and its
   assertion error".
3. When the cause category decides the next step, call `classify` with preset `failure_kind` on the located lines.

### Verify before claiming done

- Call `check` with the DONE WHEN conditions or acceptance criteria as `claims`. The default evidence is the
  working-tree diff plus untracked files; for a branch pass `evidence: [{"diff": {"base": "origin/main", "head": "HEAD"}}]`.
- Confirm each `supported` or `contradicted` verdict at its cited lines (included by default), and investigate
  `uncertain` and `not_found` claims yourself.

### Review comments

- Call `classify` with preset `review_comment`, the comments as `items` of `{id, text}`, and the pull request's intent
  in `context`.
- Call `check` with each requested change phrased as a claim about the current code (for example "`parseConfig`
  returns null for an empty file") to spot comments that are already addressed.
- Bring the resulting lists to the normal approval gate; the user decides.

### Diff scope and risk

- Call `classify` with preset `change_scope` and the task in `context` to spot out-of-scope hunks.
- Call `classify` with preset `change_risk` to flag security-sensitive hunks, and load the `security` standard when
  any label is flagged.

### Novel judgments

- Call `ask` with one atomic question per id: `noul` for the probability of yes, `choice` to pick one option, `score`
  for a position on 2-10 ordered levels.
- Refer to state fields with backticked paths such as `sources.S1`, and keep arithmetic, counting, dates and exact
  matching in code.

## Handoff

- **Report:** the decisions and `file:line` leads you used, and any non-`ok` status that changed your approach.
