# E2E / Deterministic UI Spec - TLW-23

## /accounts/checking

- name: accounts-checking
- preconditions: TinyLedger Web seed data is loaded; TinyLedger Web supports widths from 375px through 1440px with breakpoints at 640px and 1024px.
- flow:
    1. navigate /accounts/checking
    2. wait for route content
- a11y:
    - axe: no violations
    - tab-order: interactive controls follow DOM order

### scenario: accounts-checking-375

- viewport(s): 375px
- state: ticket acceptance
- setup:
    1. navigate /accounts/checking
    2. wait for the route heading and layout readiness

- assertions:
    - functional: transactions are ordered newest first
    - text: amounts include signed values
    - visible: text="No transactions yet" when the account has no transactions
    - visible: link name="Make a transfer" when the account has no transactions
    - hidden: table when the account has no transactions

### scenario: accounts-checking-768

- viewport(s): 768px
- state: ticket acceptance
- setup:
    1. navigate /accounts/checking
    2. wait for the route heading and layout readiness

- assertions:
    - functional: transactions are ordered newest first
    - text: amounts include signed values
    - visible: text="No transactions yet" when the account has no transactions
    - visible: link name="Make a transfer" when the account has no transactions
    - hidden: table when the account has no transactions

### scenario: accounts-checking-1280

- viewport(s): 1280px
- state: ticket acceptance
- setup:
    1. navigate /accounts/checking
    2. wait for the route heading and layout readiness

- assertions:
    - functional: transactions are ordered newest first
    - text: amounts include signed values
    - visible: text="No transactions yet" when the account has no transactions
    - visible: link name="Make a transfer" when the account has no transactions
    - hidden: table when the account has no transactions

## /accounts/travel

- name: accounts-travel
- preconditions: TinyLedger Web seed data is loaded; TinyLedger Web supports widths from 375px through 1440px with breakpoints at 640px and 1024px.
- flow:
    1. navigate /accounts/travel
    2. wait for route content
- a11y:
    - axe: no violations
    - tab-order: interactive controls follow DOM order

### scenario: accounts-travel-375

- viewport(s): 375px
- state: ticket acceptance
- setup:
    1. navigate /accounts/travel
    2. wait for the route heading and layout readiness

- assertions:
    - functional: transactions are ordered newest first
    - text: amounts include signed values
    - visible: text="No transactions yet" when the account has no transactions
    - visible: link name="Make a transfer" when the account has no transactions
    - hidden: table when the account has no transactions

### scenario: accounts-travel-768

- viewport(s): 768px
- state: ticket acceptance
- setup:
    1. navigate /accounts/travel
    2. wait for the route heading and layout readiness

- assertions:
    - functional: transactions are ordered newest first
    - text: amounts include signed values
    - visible: text="No transactions yet" when the account has no transactions
    - visible: link name="Make a transfer" when the account has no transactions
    - hidden: table when the account has no transactions

### scenario: accounts-travel-1280

- viewport(s): 1280px
- state: ticket acceptance
- setup:
    1. navigate /accounts/travel
    2. wait for the route heading and layout readiness

- assertions:
    - functional: transactions are ordered newest first
    - text: amounts include signed values
    - visible: text="No transactions yet" when the account has no transactions
    - visible: link name="Make a transfer" when the account has no transactions
    - hidden: table when the account has no transactions
