---
name: e2e-plan
description: Use when frontend outcomes need an objective, independently replayable e2e-spec.md with routes, runtime viewports, browser assertions, and optional Figma design-value checks.
argument-hint: The routes, required outcomes, runtime viewport widths, optional node-scoped Figma URLs, and output path.
user-invocable: true
---

# e2e-plan

Write one task-scoped `e2e-spec.md` from stated requirements. Never invent requirements, breakpoints, selectors, or
expected Figma values. Missing required input is `BLOCKED`; success is `DONE` with the spec path. Read
`templates/e2e-spec.md` for the canonical shape.

## Workflow

```markdown
- [ ] Require every route, required outcome, and runtime viewport; otherwise report BLOCKED.
- [ ] Split outcomes into independent named scenarios with stable route-unique slugs.
- [ ] Give each scenario one confirmed state, observable clean-state setup, and browser-readable `assertions:`.
- [ ] When Figma parity is required, add a node-scoped URL, semantic DOM target, and explicit rendered invariants under `figma-css`.
- [ ] Record confirmed a11y coverage and unambiguous shared flow; audit viewports come from route scenarios.
- [ ] Write one Markdown spec without a sidecar manifest and report DONE with the spec path, or BLOCKED.
```

## Scenario contract

Each route-unique `### scenario: <stable-slug>` declares runtime `viewport(s)`, one `state`, independent clean-state
`setup` with observable readiness, objective `assertions`, and optional `figma-css`. Use confirmed project/spec or
documented tool timeouts; preserve intentional loading/motion states. Never derive viewports from Figma or share mutable
state. Keep one outcome per assertion without `OR`; no `figma-css` means no Figma parity claim.

## `figma-css` contract

Use this shape:

```yaml
figma-css:
  - url: <node-scoped Figma URL>
  - target: <semantic DOM target>
  - compare:
      - computed-style: <property> pseudo=<optional ::before|::after>
      - sibling-gap: children=<semantic child target> axis=<block|inline>
      - parent-child-inset: child=<semantic child target> edges=<block|inline|named edges>
      - element-spacing: from=<semantic target> to=<semantic target> edges=<named edges>
```

Include only requested comparisons. `visual-verify` resolves values from Figma at run time. Use `computed-style` for
colors, opacity, typography, border, radius, or explicitly required padding/gap; name a pseudo-element only when the
rendered property belongs to it. Use relational checks for distances:

- `sibling-gap` passes when adjacent child boxes have the required distance, including a margin-based implementation.
- `parent-child-inset` passes when parent and child geometry has the required inset, regardless of padding/margin use.
- `element-spacing` measures the named edges of two explicitly identified elements.

Exclude absolute position, frame size, viewport-relative position, wrapping, line count, and column count from Figma
parity. Verify one only as an objective assertion that pins viewport, state, targets, outcome, and tolerance.

## Planning rules

- Use one `## <route>` per app-relative route; supply the base URL at run time.
- Keep `flow:`/`a11y:` route-level; repeat required interactions in scenario `setup`. Empty a11y is unaudited, not passed.
- Cover every element when an invariant applies to a set. Use one representative only for a deeper interaction flow.
- Ask about relevant loading, empty, error, disabled, long-text, keyboard, and reduced-motion outcomes, not mandatory scenarios.
  Write only confirmed behavior; unresolved required outcomes block planning.
- Keep the spec compact: name the invariant and semantic target, not a full Figma context dump.

## Handoff

Report the spec path and covered routes, or `BLOCKED` with the missing input named. Hand scenario `assertions:` and
`figma-css` to `visual-verify`; hand route-level `a11y:` to `a11y-verify`.
