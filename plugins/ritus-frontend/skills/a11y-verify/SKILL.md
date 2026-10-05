---
name: a11y-verify
description: "Use when a UI change needs accessibility verification against a local running app: assert an e2e-spec's a11y requirements, run axe, and report scoped coverage with A11Y: PASS / FAIL / BLOCKED."
argument-hint: The e2e spec (its `a11y:` blocks + routes) and the base URL to verify against.
user-invocable: true
---

# a11y-verify

Verify nonempty route-level `a11y:` blocks in a fresh context; `assertions:` belongs to `visual-verify`.
Ask for a missing spec/base URL, then BLOCKED if unavailable; never guess the port. List absent/empty blocks as
not audited, never passed. Zero executable coverage or missing explicitly required coverage means A11Y: BLOCKED.

Targets are **local-only**. Use `browser_evaluate` / `browser_run_code_unsafe` for the accessibility tree, ARIA
attributes, computed colours, and `axe.run()` via an injected script; use isolated localhost origins only.

Create this TODO and mark progress:

```markdown
- [ ] Require spec, base URL, and executable a11y coverage; otherwise BLOCKED.
- [ ] Collect covered routes and their scenario viewports; identify unaudited or missing required coverage.
- [ ] At every included route/viewport, run axe and assert the a11y entries using shared flow.
- [ ] Report verdict, coverage, and evidence.
```

## Procedure

For each included route, use distinct width/height pairs from its scenarios' `viewport(s)` (height 800px unless pinned).
Missing viewports or conflicting/unresolved shared-flow states mean BLOCKED; never choose a scenario arbitrarily.

1. Resize before navigating to base URL + route; establish clean preconditions. Unavailable setup is BLOCKED.
2. On ready state, run axe, check declared WCAG contrast ratios from computed colours, and confirm required roles/names.
3. For dynamic entries, replay shared `flow:` and compare ARIA/focus outcomes. Use observable waits with confirmed
   project/spec or documented tool timeouts, never sleeps or default networkidle. Record condition, bound, last observation.
4. With a usable browser/target, a required product state missing at the bound is FAIL. Missing observation capability,
   bound, access, or unique target is BLOCKED. Do not wait away an intentionally tested loading/motion state.
5. Save evidence: `browser_take_screenshot` to `.ritus/screenshot/<ticket>/<name>-a11y-<breakpoint>.png` (`mkdir -p` the
   dir first; `<ticket>` = the spec filename's `{ticket-id}` prefix, else its parent folder).

## Verdicts

- **PASS** - nonzero coverage; every required entry checked and satisfied, axe executed at every included pair without violations.
- **FAIL** - observed entry violation, product-state timeout, or axe violation.
- **BLOCKED** - required inputs, coverage, setup, or evidence unavailable. No axe execution is not a clean audit.

## Handoff

Report `A11Y: PASS / FAIL / BLOCKED` using `FAIL > BLOCKED > PASS`, with affected routes/viewports/checks, executed/required
assertion counts, axe runs/violations, and unaudited routes. PASS covers only the stated scope, not whole-site compliance.
