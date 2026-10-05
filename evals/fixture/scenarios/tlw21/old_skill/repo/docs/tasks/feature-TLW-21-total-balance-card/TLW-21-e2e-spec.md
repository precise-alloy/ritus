# E2E / Deterministic UI Spec - TLW-21

## /accounts

- name: accounts
- preconditions: TinyLedger Web seed data is loaded; TinyLedger Web supports widths from 375px through 1440px with breakpoints at 640px and 1024px.
- flow:
    1. navigate /accounts
    2. wait for route content
- a11y:
    - axe: no violations
    - tab-order: interactive controls follow DOM order

### scenario: accounts-375

- viewport(s): 375px
- state: ticket acceptance
- setup:
    1. navigate /accounts
    2. wait for the route heading and layout readiness
- figma-css:
    - url: https://www.figma.com/design/TLWEB0001/TinyLedger-Web?node-id=12-34
    - target: region name="Total balance"
    - compare:
        - computed-style: background-color equals design fill token
        - computed-style: border-color equals design stroke token
        - computed-style: border-radius equals design radius
        - parent-child-inset: child=label edges=block-start inline-start
        - sibling-gap: children=label,value axis=block
- assertions:
    - visible: region name="Total balance"
    - text: region name="Total balance" contains "$12,345.67"
    - geometry: summary card fills the content column with no horizontal overflow

### scenario: accounts-768

- viewport(s): 768px
- state: ticket acceptance
- setup:
    1. navigate /accounts
    2. wait for the route heading and layout readiness
- figma-css:
    - url: https://www.figma.com/design/TLWEB0001/TinyLedger-Web?node-id=12-34
    - target: region name="Total balance"
    - compare:
        - computed-style: background-color equals design fill token
        - computed-style: border-color equals design stroke token
        - computed-style: border-radius equals design radius
        - parent-child-inset: child=label edges=block-start inline-start
        - sibling-gap: children=label,value axis=block
- assertions:
    - visible: region name="Total balance"
    - text: region name="Total balance" contains "$12,345.67"
    - geometry: summary card fills the content column with no horizontal overflow

### scenario: accounts-1280

- viewport(s): 1280px
- state: ticket acceptance
- setup:
    1. navigate /accounts
    2. wait for the route heading and layout readiness
- figma-css:
    - url: https://www.figma.com/design/TLWEB0001/TinyLedger-Web?node-id=12-34
    - target: region name="Total balance"
    - compare:
        - computed-style: background-color equals design fill token
        - computed-style: border-color equals design stroke token
        - computed-style: border-radius equals design radius
        - parent-child-inset: child=label edges=block-start inline-start
        - sibling-gap: children=label,value axis=block
- assertions:
    - visible: region name="Total balance"
    - text: region name="Total balance" contains "$12,345.67"
    - geometry: summary card fills the content column with no horizontal overflow
