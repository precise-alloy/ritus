# Parallel Browser Worker Protocol

Read this reference only after `visual-verify` has selected parallel mode. The inline coordinator owns scheduling,
Figma access, shared artifacts, fingerprints, and lifecycle verdicts. Each worker verifies exactly one independent
`route x scenario x viewport` unit in its own browser/tool session.

## Dispatch prompt

Render one prompt per work unit using this exact structure; replace every `{{...}}` field with unit-local data:

```text
You are an isolated browser verification worker. Verify exactly one work unit and return one JSON result.

WORK UNIT
worker_id: {{worker_id}}
artifact_directory: {{artifact_directory}}
base_url: {{base_url}}
route: {{route}}
viewport: {{viewport}}
state: {{state}}
setup:
{{setup_steps}}
objective_assertions:
{{objective_assertions}}
resolved_figma_invariants:
{{resolved_figma_invariants}}
normalization_and_tolerances:
{{normalization_and_tolerances}}

RULES
- Use only your isolated browser/tool session and the assigned artifact directory.
- Resize before navigation, reload, replay this unit's clean setup with observable waits and supplied or documented tool bounds.
  Before measuring, await relevant fonts, decoded images with usable intrinsic dimensions, and layout transitions unless
  loading/motion is the required state. Never force interactions, disable motion globally, use sleeps/default networkidle,
  or wait away the tested state. Record condition, bound, last observation; missing bound/observation capability is BLOCKED.
- Resolve every semantic target uniquely; zero or multiple matches is BLOCKED.
- Run objective assertions first. With usable browser/target, required product state missing at the bound is FAIL;
  skip dependent comparisons. External browser/setup unavailability is BLOCKED.
- For computed-style, use getComputedStyle(target, declaredPseudoElement), omitting the second argument when absent.
- For sibling-gap, record adjacent child DOMRects in rendered order and calculate next start minus previous end on the
  declared axis.
- For parent-child-inset, calculate child edge minus parent inner border edge and record both boxes plus border widths.
- For element-spacing, record both boxes and subtract the explicitly named edges.
- Normalize and compare exactly as supplied in normalization_and_tolerances; do not widen a tolerance.
- Do not edit source, call Figma MCP, read the full spec, or inspect unrelated scenarios.
- Do not write run-state.json, repair-brief.md, fingerprints, or another worker's directory.
- Capture a target screenshot only after deterministic FAIL; add viewport context only when needed; capture none on PASS.
- Return worker-level PASS, FAIL, or BLOCKED only. Never emit FOCUSED PASS, FAIL: no progress, or VERIFY: PASS.
- Return exactly one JSON object matching WORKER RESULT; do not wrap it in prose or Markdown.

WORKER RESULT
{{worker_result_schema}}
```

Never include the full `e2e-spec.md`, full Figma context, unrelated scenarios, or repair history in a worker prompt.

## Worker result schema

```json
{
  "worker_id": "route__scenario__viewport",
  "status": "PASS",
  "measurements": [
    {
      "key": "assertion-or-invariant-key",
      "status": "PASS",
      "expected": "normalized expected value",
      "observed": "normalized observed value",
      "delta": "normalized delta or null",
      "tolerance": "declared tolerance or exact",
      "source": "browser measurement source",
      "boxes": null
    }
  ],
  "diagnostics": [],
  "error": null
}
```

Allowed top-level `status` values are `PASS`, `FAIL`, and `BLOCKED`. Each measurement uses the same values. `boxes` is
either `null` or the relevant named `DOMRect` records. `diagnostics` contains only paths below the assigned artifact
directory. `error` is `null` unless the worker is blocked or failed operationally.

## Artifact ownership and path safety

Use stable worker ID `<route-slug>__<scenario-slug>__<viewport>`. A parallel worker may write only below:

```text
<round-or-promotion>/<worker-id>/
```

The coordinator creates no two workers with the same ID in one selected run.

Before dispatch, normalize every route, scenario, and viewport component deterministically: apply Unicode NFKC, trim and
lowercase, replace each run of non-ASCII-alphanumeric characters with `-`, collapse and trim `-`, and use `unnamed` when
empty. The `<viewport>` field in the visible ID is this normalized viewport token, not an unsanitized raw value. Reject raw
NUL or `.`/`..` path segments before normalization; after normalization, reject any token that still contains `/`, `\`, NUL,
or traversal segments, and reject normalized-ID collisions. Never interpolate raw components into a path.

The coordinator canonicalizes the run root and each assigned artifact directory and accepts dispatch only when the artifact
directory is a strict descendant of the canonical run root. Before accepting a worker result, canonicalize every diagnostic
path and require strict containment below that worker's assigned artifact directory. Reject absolute, drive-qualified,
traversal, separator-escaping, or out-of-root paths as `BLOCKED: worker failure`.

## Fan-in

After every worker in a bounded batch returns:

1. Validate JSON shape, worker ID, statuses, diagnostic path ownership, and exact assigned check-key coverage.
  Missing, duplicate, foreign, or evidence-free results and inconsistent statuses mean BLOCKED; retain valid observed FAILs.
2. Before verdict calculation, inject every Figma-blocked invariant excluded from dispatch into shared failure state as
   `BLOCKED: Figma invariant`; independent objective-only work may still proceed.
3. Convert crash, timeout, malformed JSON, mismatched ID, or out-of-scope path to `BLOCKED: worker failure`.
4. Wait for the complete batch after a worker FAIL; do not early-cancel independent work.
5. Merge by route, scenario, and viewport order from the spec, never completion order.
6. Apply run-level precedence `FAIL > BLOCKED > PASS`, including coordinator-injected Figma blocks.
7. Compute normalized cross-run fingerprints in the coordinator only.
8. Write shared `run-state.json` and `repair-brief.md` in the coordinator only.
9. Apply focused-repair, no-progress, and promotion rules before the coordinator emits a lifecycle verdict.

If worker launch is unavailable before browser interaction, run work not already completed through the inline
single-agent sequential path without consuming a repair round. Do not retry a crashed worker indefinitely.
