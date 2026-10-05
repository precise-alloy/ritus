# E2E / Deterministic UI Spec - format and examples

`e2e-plan` writes this Markdown file. `visual-verify` runs scenario `assertions:` and `figma-css`; `a11y-verify` runs
nonempty route-level `a11y:` at distinct scenario viewport pairs; absent/empty blocks are unaudited, zero coverage BLOCKED.

Routes are app-relative; viewports are runtime widths (height defaults to 800px). Each scenario owns clean setup and one
confirmed state. Only explicitly requested Figma parity gets `figma-css`; name comparisons, not resolved values.

## /accounts

- name: accounts-list
- preconditions: authenticated user with at least three accounts
- flow: # retained for route-level a11y only
    1. navigate /accounts
    2. wait for populated role=list name="Accounts" within the confirmed project/tool timeout
- a11y:
    - axe: no violations
    - tab-order: interactive controls follow DOM order

### scenario: account-list-spacing

- viewport(s): 1200px
- state: populated
- setup:
    1. reload route
    2. within the confirmed project/tool timeout, wait for populated role=list name="Accounts" and its font/layout readiness
- figma-css:
    - url: https://www.figma.com/design/example/Accounts?node-id=120-45
    - target: role=list name="Accounts"
    - compare:
        - computed-style: background-color
        - computed-style: border-radius
        - sibling-gap: children=role=listitem axis=block
        - parent-child-inset: child=role=listitem first edges=inline
- assertions:
    - visible: role=list name="Accounts"
    - count: role=listitem >= 3

### scenario: account-sort-order

- viewport(s): 1200px
- state: sorted-by-name
- setup:
    1. reload route
    2. within the confirmed project/tool timeout, wait for populated role=list name="Accounts", then click role=button name="Sort by Name"
- assertions:
    - attribute: role=button name="Sort by Name" aria-pressed="true"
    - functional: account rows are ordered by Name ascending

<!-- Vocabulary:
     setup: clean-state steps owned by one scenario.
     assertions: focused / visible / hidden / text / value / attribute / style / console / geometry / functional.
     figma-css: structured design values compared with rendered browser evidence.
     a11y: route-level ARIA state / contrast / axe / tab-order checks retained for a11y-verify. -->
