---
name: jev
description: Use when a change alters a rule, contract, API or term and every passage that still states the old one must be found; when you need where a behavior lives across many files or in long command output; when you check whether code or the git diff satisfies specific statements (DONE WHEN, acceptance criteria, already-addressed review comments); or when many failures, review comments or diff hunks need triage. Uses the ritus-jev MCP tools sweep, locate, check, classify and ask, backed by TypeSafe Jev.
argument-hint: Describe what to find, verify or classify
---

# Jev coding tools

The ritus-jev MCP server gives you five tools backed by TypeSafe Jev, a fast, low-cost judgment model. Each tool reads
files and git diffs itself and returns short, cited leads. Use them where they replace reading or find what a search
cannot; use ordinary search and reading where exact matching or a small, known file settles the question.

Tool names by host:

- Copilot CLI: `jev-sweep`, `jev-locate`, `jev-check`, `jev-classify`, `jev-ask`
- Claude Code: `mcp__plugin_ritus-jev_jev__sweep` and the same pattern for `locate`, `check`, `classify`, `ask`

## Every call

- Pass `workspace` as the absolute path of the repository you are working in.
- Write queries, claims and labels in English; Jev is most accurate in English.
- Treat results as leads: read the cited `path` + `lines` (or the included excerpt) before you state a fact about the
  code, and cite that `file:line`.
- Act on `status`:
  - `ok` - use the result.
  - `disabled` - the tools are off for this workspace (the `hint` says why and how to enable them); use your ordinary
    search and read tools for the rest of the session.
  - `scope_too_large` - narrow `paths` using the returned `breakdown`, or add `exclude` or `terms`, then call again.
  - `rate_limited` or `unavailable` - continue with ordinary tools; retry later only when the answer still matters.
  - `auth_error` - TypeSafe rejected the key; tell the user once, then continue with ordinary tools.
  - `input_error` - fix the argument named in `error` and call again.
- Act on `warnings`: an empty diff source means the evidence you meant is missing (for example drop `head` to include
  uncommitted work); a file named in a claim but missing from `evidence` needs adding.
- When a result carries a `warning` about a tracked key file, tell the user once.

## Choose the tool

| You need | Tool |
|---|---|
| Every passage that still states an old rule, contract, API or term, in any wording | `sweep` |
| Where a behavior, setting, test or doc lives, when the file is unknown | `locate` |
| The failure in long command output saved to a file | `locate` |
| Whether files or the diff satisfy specific statements | `check` |
| Labels for many items (failures, review comments, diff hunks) | `classify` |
| Another narrow judgment over some text | `ask` |

Use a search or a direct read instead when:

- The task already names the files: read them.
- You know the exact identifier or string: use grep or LSP.
- The statement is a count, an exact phrase, a formatting rule or a list of changed files: use `rg`,
  `git diff --name-only` or the task's VERIFY commands (`check` answers quoted phrases and changed-file claims exactly,
  and returns `use_search` for formatting rules).
- The diff has a few hunks: read it.

## Recipes

### Sweep after changing a rule, contract, API or term

1. Describe the passages to find directly, one behavior per sweep: the old wording or behavior, for example "a passage
   saying that a worker is dispatched in a fresh subagent" or "a passage saying that review fixes are handled by
   generating a fix task file". Jev reads literally, so describe the old text rather than the new rule.
2. Scope with `paths` (for example `skills`, `docs`, `src`, `README.md`) and leave out archives with `exclude` (for
   example `docs/tasks`); add `terms` only when every stale passage must contain one of them.
3. Read each hit at its `line`; update the passages that state the old behavior and keep the ones the new rule allows.
4. Sweep again for each other old behavior, and once more after editing to confirm no hit remains.

### Find, then read

1. Call `locate` with one plain-English behavior per `query`; run several queries in parallel for several topics.
   Scope large repositories with `paths` (directories or globs) and optional literal `terms`.
2. `found`: the top hits include their text - work from it and read around a hit only when you need more.
3. `partial` or `not_found`: widen or change the scope once, then conclude the behavior is absent.

### Long command output

1. Redirect verbose output to a temp file, for example `npm test *> "$env:TEMP\ritus-test.log"` in PowerShell or
   `npm test > /tmp/ritus-test.log 2>&1` in a POSIX shell, and read only the exit code.
2. Call `locate` with `paths: ["<absolute path of that file>"]` and a query such as "the first failing test and its
   assertion error".
3. When the cause category decides the next step, call `classify` with preset `failure_kind` on the located lines.

### Verify statements

- Call `check` with one atomic claim per statement. Quote exact phrases in backticks: `literal` and `count` claims are
  then answered by exact search, and claims about which files changed are answered from the diff (`method: "code"`).
- Evidence defaults to the working-tree diff plus untracked files, plus the files the claims name. For a whole branch,
  committed or not, pass `evidence: [{"diff": {"base": "origin/main"}}]`; add `head` only for a commits-only range.
- Act on each verdict: `supported` with `method: "code"` is exact; confirm other `supported` verdicts at the cited lines
  when they decide something; read the excerpt of `contradicted` and `uncertain` claims; for `not_found`, make sure the
  evidence covers the claim; for `use_search`, run the search the `hint` suggests.

### Review comments

- Call `classify` with preset `review_comment`, the comments as `items` of `{id, text}`, and the pull request's intent
  in `context`.
- Call `check` with each requested change phrased as a claim about the current code (for example "`parseConfig`
  returns null for an empty file") to spot comments that are already addressed.
- Bring the resulting lists to the normal approval gate; the user decides.

### Diff scope and risk

- On diffs with many hunks, call `classify` with preset `change_scope` and the task in `context` to spot out-of-scope
  hunks, or with preset `change_risk` to flag security-sensitive hunks; load the `security` standard when any label is
  flagged.

### Novel judgments

- Call `ask` with one atomic question per id: `noul` for the probability of yes, `choice` to pick one option, `score`
  for a position on 2-10 ordered levels.
- Refer to state fields with backticked paths such as `sources.S1`, and keep arithmetic, counting, dates and exact
  matching in code.

## Handoff

- **Report:** the decisions and `file:line` leads you used, every `sweep` hit you acted on or kept, and any non-`ok`
  status that changed your approach.
