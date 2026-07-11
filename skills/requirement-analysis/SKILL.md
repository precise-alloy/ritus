---
name: requirement-analysis
description: Dispatched by ticket-review for STANDARD/EPIC changes - does the read-heavy requirement analysis (check existing work, fetch the ticket, explore the code, flag ambiguities) and drafts the review document. Not invoked directly by the user; ticket-review owns the human gates.
argument-hint: Provide the requirement source (plain description or ticket URL/key), the intake context gathered by ticket-review, and the branch slug / search key
user-invocable: false
---

# Requirement Analysis

**Core principle:** Understand the requirement completely - from live data and real code, not assumptions - before
any task is generated. You run non-interactively: you never ask the user; every open question becomes a written
marker for the human gate that follows.

## When to use

Dispatched as a fresh subagent by `ticket-review` for STANDARD/EPIC changes, to keep the read-heavy analysis (ticket
body, existing files, codebase exploration) out of the main thread's context. The parent (`ticket-review`) gathered
the input and owns the human gates; you produce the analysis and the drafted review document, then return.

Not invoked directly by the user. For SIMPLE changes `ticket-review` does a light inline analysis instead of
dispatching you.

When starting requirement-analysis, create this TODO - **every item below, verbatim** (never a single item named after the skill) - and mark items done as you complete them:

TODO:

```markdown
- [ ] Check existing work (review / task / memory files)
- [ ] Fetch the ticket (if a ticket URL was provided)
- [ ] Analyze requirements (criteria, code, images, ambiguities, concerns)
- [ ] Draft the review document
- [ ] Report the analysis back to ticket-review
```

## Operating constraints

- **Read-only, with four exceptions:** you may write/update the **review document**, append to the
  `docs/tasks/{branch-slug}/exploration.md` **exploration log**, append `DECISION-NNN` entries to `docs/DECISIONS.md`,
  and download ticket attachments into the transient runtime scratch `.ritus/attachments/{TICKET_KEY}/` (throwaway
  images you read during analysis - runtime data, not part of the deliverable; safe to gitignore). Touch nothing else -
  no source files, no task files (those come after human approval).
- **Fully non-interactive** - you cannot talk to the user. Never ask a question, never wait for input. Every
  ambiguity becomes a `[NEEDS CLARIFICATION: <question>]` marker; every default becomes an `[ASSUMPTION: <why>]`
  marker. The parent presents them at its review gate.
- **Return findings, not dumps** - cite `file:line` (or a source URL for online research); never paste raw file
  contents or fetched web pages into your report.

## Step 1: Check existing work

Determine the search key: ticket ID (e.g. `PROJ-123`) if a ticket URL was provided, else the branch slug (e.g.
`feat-add-login`). Then check for prior work before analyzing from scratch:

1. A review document in the ticket reviews path (`docs/PROJECT_CONTEXT.md` `## Documentation layout`) matching the key.
2. Any task files in `docs/tasks/` matching the key.
3. Any context files in `docs/memory/` matching the key.

### If a review file exists → incremental update

1. Read the existing review file and note its `Last Reviewed` datetime (UTC).
2. **Ticket source:** fetch the ticket's changelog and comments since that datetime via `remote-api-access.md` in the
   `shared` skill directory - identify description updates, new comments, status changes, acceptance-criteria updates.
3. **Plain requirement:** compare the current description against the existing review - identify what changed.
4. Reflect changes into the review document: move answered questions from "Open Questions" to "Decisions"; update
   confirmed/invalidated assumptions; adjust task lists if scope changed; set `Last Reviewed` to the current UTC time.
5. **Compute a diff summary** of what changed, and set an `up-to-date` flag when there are no changes. Do **not** ask
   the user anything - return the diff summary and flag; the parent decides whether a full re-review is wanted.

### If no existing files → full analysis

Proceed to Step 2.

## Step 2: Fetch the ticket (if a ticket URL or ticket key was provided)

**Skip if the user provided a plain requirement.**

Read `remote-api-access.md` in the `shared` skill directory for the helper instructions - this helper is the single
mechanism for fetching ticket data (it auto-detects the provider). Live ticket data is required
before drafting the review - never analyze from stale or partial data.

Parse keys/IDs per `docs/PROJECT_CONTEXT.md` `## Team conventions`.

The provider is auto-detected from the key/URL shape:

```bash
bun run "<plugin-root>/scripts/remote-api.ts" issue "<TICKET_KEY_OR_URL>" [fields]
```

If auto-detection fails, fall back to the explicit provider syntax (e.g., `jira issue`, `ado issue`, `github issue`).

Provider-specific fields to request (the `[fields]` parameter format varies by provider - pass field names
matching that provider's API):

- **Jira:** `"summary,description,status,issuetype,comment,acceptance_criteria"`
- **Azure DevOps:** `"System.Title,System.Description,System.State,System.WorkItemType,System.Tags"` (also fetch
  comments separately: `bun run "<plugin-root>/scripts/remote-api.ts" comments "<WORK_ITEM_URL_OR_ID>"`)
- **GitHub Issues:** no field filter needed (returns full issue by default)

If the provider returns `401`, `403`, or a permission-style `404`, stop and report the access failure back to
ticket-review - do not continue with stale or partial data.

Apply `docs/PROJECT_CONTEXT.md` `## Requirement source precedence`.

## Step 3: Analyze requirements

### 3.1 Identify requirements

From the requirement source (ticket description + comments, or plain requirement text), extract:

1. **Acceptance criteria** - what must be true for the work to be done.
2. **Expected behavior** - how the feature/fix should work.
3. **Test data** - specific values, scenarios, or edge cases mentioned.
4. **Constraints** - performance, security, compatibility notes.

### 3.2 Analyze related code

You are the read-only research context, so explore the code **inline** (semantic search, grep, file reads) across the
source layout in `docs/PROJECT_CONTEXT.md` `## Source layout`. Identify and cite at `file:line`:

- **Existing code** implementing related functionality.
- **Entry points** (controllers, API endpoints, blocks, pages) affected.
- **Services and helpers** that will need changes.
- **Models and DTOs** that may need updates.
- **Configuration** files or constants involved.

Record what you find in `docs/tasks/{branch-slug}/exploration.md` (create it with the header from
`skills/ticket-review/templates/exploration.md` if missing, then append - append-only) and summarize it in your
report - do not dump raw file contents.

### 3.3 Check for UI changes

If the requirements involve UI updates (new components, layout, styling, frontend behavior):

1. Inspect frontend/UI paths from `docs/PROJECT_CONTEXT.md` `## Source layout`.
2. Skip generated artifact paths listed there.

### 3.4 Analyze attached images

If the ticket or requirement includes image attachments (screenshots, mockups, annotated images), download them into
the transient runtime scratch first (throwaway - see Operating constraints):

```bash
bun run "<plugin-root>/scripts/remote-api.ts" jira attachment-download "<TICKET_KEY>" ".ritus/attachments/<TICKET_KEY>"
```

Then read each downloaded image with the `Read` tool (the command returns a JSON list of `{ filename, path }` - use
the `path` values). If the download fails or returns nothing, add a `[NEEDS CLARIFICATION: share the screenshots]`
marker. After downloading:

1. Read the ticket description and acceptance criteria FIRST - understand what is expected.
2. THEN examine each image against that context: **What I see** (specific elements - count items, read text, note
   states) vs **What the ticket says should happen** (from 3.1) vs **The gap**.
3. For annotated images (arrows, circles, highlights): identify the specific element the annotation points at, and
   infer intent from the ticket context.
4. Document image findings in the review document under `## Visual References`.

**Do NOT** describe images in isolation - always cross-reference against the ticket requirements.

### 3.5 Review existing documentation

Check documentation paths in `docs/PROJECT_CONTEXT.md` `## Documentation layout` for existing docs related to the
feature area.

### 3.6 Research technical options

**Conditional** - only when the work involves a new external dependency/library, a new integration with an unfamiliar
system, an architectural pattern not yet used here, a technology choice with multiple viable options, or a requirement
that must conform to an external standard/spec (accessibility, security, a protocol, compliance) whose authority lives
outside the codebase. Skip for bug fixes, refactors, and features that extend existing patterns.

When triggered, route each question to the source that actually holds the answer:

1. **Reuse what the codebase already has** - for a library or pattern the project may already use, search the code
   first; if an existing solution fits, use it, and propose alternatives only when it can't meet the requirements.
2. **Go to the authoritative source when the answer lives outside the code** - an industry standard or spec
   (accessibility → W3C/WCAG, security → OWASP, a protocol → its RFC) or an unfamiliar library's official docs. Read
   the canonical source directly; the codebase won't contain it, and blog posts only paraphrase it.
3. **Keep online research cheap** - lead with a web search and work from the result snippets; open a full page only
   when a snippet can't answer it, and fetch it with a **specific query** so only the relevant section loads, not the
   whole page. Prefer one official source over several tutorials; budget ~2–3 fetches for the investigation; record
   the URL + the conclusion you drew - the review and exploration log get the finding, never the page contents.
4. **Investigate options** - for genuinely new choices, research 2-3 options, noting stack compatibility (from
   `docs/PROJECT_CONTEXT.md`), maintenance status, relevant performance characteristics, and security implications.
5. **Recommend one option** with rationale - make a decision, don't present a menu.
6. **Record the decision** - write a `DECISION-NNN` entry per 3.9 if the choice is non-obvious.

Keep it lightweight (a ~10-minute investigation). If it would take longer, add
`[NEEDS CLARIFICATION: requires spike - <what to investigate>]` and let the human decide.

### 3.7 Flag ambiguities

For every requirement that could be read two ways:

- `[NEEDS CLARIFICATION: <specific question>]` - ambiguous requirement, blocks task generation.
- `[ASSUMPTION: <what you assumed and why>]` - reasonable default; visible but non-blocking.

Rules: never guess when two interpretations lead to different implementations - flag it. Every
`[NEEDS CLARIFICATION]` must carry a specific question. Read `docs/STAKEHOLDERS.md` to frame each question for whoever
should answer it. Distinguish blocking questions from nice-to-haves.

### 3.8 Raise concerns

Proactively document, in the review, any concerns about **security** (authn/authz, input validation, data exposure,
injection), **performance** (N+1, large payloads, missing caching, scalability), **breaking changes** (API contracts,
backward compatibility), and **data integrity** (race conditions, partial updates, migration risk).

### 3.9 Record architectural decisions

If a non-obvious architectural decision was made during analysis, append a `DECISION-NNN` entry to `docs/DECISIONS.md`
(Date / Context / Decision / Rationale / Consequences). Skip if all decisions were obvious or already documented.

## Step 4: Draft the review document

Read `skills/ticket-review/templates/review-document.md` for the template and write (or, for an incremental update,
revise) the review document at the ticket reviews path. It captures acceptance criteria, proposed approach, scope
boundaries, open questions/assumptions, raised concerns, and any visual references. The `Last Reviewed` datetime (UTC)
is mandatory.

## Output

Return to `ticket-review` (do not print raw file contents):

```text
REQUIREMENT ANALYSIS COMPLETE

Review document: <path>
Classification signal: <any upgrade recommendation, e.g. STANDARD → EPIC, with reason | none>

Findings summary:
- <analysis point - file:line>

Open markers:
- [NEEDS CLARIFICATION: ...]   (blocking)
- [ASSUMPTION: ...]

Concerns: <security / performance / breaking / data-integrity, or none>

Incremental (if applicable):
- Diff summary: <what changed since Last Reviewed>
- up-to-date: <yes/no>
```

## Hard rules

- Never draft the review from stale or partial ticket data - fetch live data first, or stop and report the failure.
- Never ask the user - every question is a `[NEEDS CLARIFICATION]` marker.
- Write only the review document, the exploration log, `DECISION-NNN` entries, and the transient
  `.ritus/attachments/{TICKET_KEY}/` scratch (per Operating constraints). No source or task files.
- Cite `file:line` for every claim about existing code.

## Handoff

- **Report:** the analysis output above - review-document path, findings, open markers, concerns, and (incremental)
  the diff summary + up-to-date flag. `ticket-review` runs the human review gate on it and generates the task files.
