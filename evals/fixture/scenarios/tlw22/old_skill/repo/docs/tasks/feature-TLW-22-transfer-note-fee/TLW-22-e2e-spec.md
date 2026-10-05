# E2E / Deterministic UI Spec - TLW-22

## /transfer

- name: transfer
- preconditions: TinyLedger Web seed data is loaded; TinyLedger Web supports widths from 375px through 1440px with breakpoints at 640px and 1024px.
- flow:
    1. navigate /transfer
    2. wait for route content
- a11y:
    - axe: no violations
    - tab-order: interactive controls follow DOM order

### scenario: transfer-375

- viewport(s): 375px
- state: ticket acceptance
- setup:
    1. navigate /transfer
    2. wait for the route heading and layout readiness

- assertions:
    - visible: textbox name="Note"
    - attribute: textbox name="Note" maxlength="140"
    - visible: region name="Transfer fee"
    - geometry: fee panel is beside the form at 1280px and below the form at 375px and 768px
    - functional: `transferFee(2550)` returns 26 and `transferFee(2549)` returns 25

### scenario: transfer-768

- viewport(s): 768px
- state: ticket acceptance
- setup:
    1. navigate /transfer
    2. wait for the route heading and layout readiness

- assertions:
    - visible: textbox name="Note"
    - attribute: textbox name="Note" maxlength="140"
    - visible: region name="Transfer fee"
    - geometry: fee panel is beside the form at 1280px and below the form at 375px and 768px
    - functional: `transferFee(2550)` returns 26 and `transferFee(2549)` returns 25

### scenario: transfer-1280

- viewport(s): 1280px
- state: ticket acceptance
- setup:
    1. navigate /transfer
    2. wait for the route heading and layout readiness

- assertions:
    - visible: textbox name="Note"
    - attribute: textbox name="Note" maxlength="140"
    - visible: region name="Transfer fee"
    - geometry: fee panel is beside the form at 1280px and below the form at 375px and 768px
    - functional: `transferFee(2550)` returns 26 and `transferFee(2549)` returns 25
