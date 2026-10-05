# E2E / Deterministic UI Spec - TLW-22

## /transfer

- name: transfer
- preconditions: TinyLedger Web seed data is loaded; supported widths are 375px to 1440px, with breakpoints at 640px and 1024px.
- flow:
    1. navigate /transfer
    2. wait for heading name="Transfer" and complementary name="Fee preview"
- a11y:
    - axe: no violations
    - name: textbox name="Note (optional)" takes its name from its visible label
    - tab-order: interactive controls follow DOM order

### scenario: transfer-layout-narrow

- viewport(s): 375px, 768px
- state: empty form
- setup:
    1. reload route
    2. wait for heading name="Transfer" and complementary name="Fee preview"
- assertions:
    - visible: textbox name="Note (optional)"
    - attribute: textbox name="Note (optional)" maxlength="140"
    - visible: complementary name="Fee preview"
    - geometry: the top of complementary name="Fee preview" is at or below the bottom of the transfer form
    - geometry: document scroll width is at most the viewport width

### scenario: transfer-layout-wide

- viewport(s): 1280px
- state: empty form
- setup:
    1. reload route
    2. wait for heading name="Transfer" and complementary name="Fee preview"
- assertions:
    - visible: textbox name="Note (optional)"
    - visible: complementary name="Fee preview"
    - geometry: complementary name="Fee preview" starts at or right of the transfer form's right edge, and their vertical ranges overlap
    - geometry: document scroll width is at most the viewport width

### scenario: transfer-fee-half-up

- viewport(s): 1280px
- state: amount 25.50 entered
- setup:
    1. reload route
    2. wait for textbox name="Amount"
    3. type "25.50" into textbox name="Amount"
- assertions:
    - text: complementary name="Fee preview" contains "$0.26"
    - text: complementary name="Fee preview" contains "$25.76"

### scenario: transfer-fee-below-half

- viewport(s): 1280px
- state: amount 25.49 entered
- setup:
    1. reload route
    2. wait for textbox name="Amount"
    3. type "25.49" into textbox name="Amount"
- assertions:
    - text: complementary name="Fee preview" contains "$0.25"
    - text: complementary name="Fee preview" contains "$25.74"

### scenario: transfer-fee-minimum

- viewport(s): 1280px
- state: amount 10.00 entered
- setup:
    1. reload route
    2. wait for textbox name="Amount"
    3. type "10.00" into textbox name="Amount"
- assertions:
    - text: complementary name="Fee preview" contains "$0.25"
    - text: complementary name="Fee preview" contains "$10.25"
