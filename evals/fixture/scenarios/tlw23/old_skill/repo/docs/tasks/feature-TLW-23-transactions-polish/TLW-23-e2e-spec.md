# E2E / Deterministic UI Spec - TLW-23

## /accounts/checking

- name: account-checking
- preconditions: TinyLedger Web seed data is loaded; the Checking account has three transactions.
- flow:
    1. navigate /accounts/checking
    2. wait for heading name="Checking" and table name="Checking transactions"
- a11y:
    - axe: no violations
    - tab-order: interactive controls follow DOM order

### scenario: checking-transactions

- viewport(s): 375px, 768px, 1280px
- state: populated
- setup:
    1. reload route
    2. wait for table name="Checking transactions"
- assertions:
    - visible: table name="Checking transactions"
    - count: body rows of table name="Checking transactions" = 3
    - functional: row dates are in descending order (newest first)
    - text: incoming amounts start with "+" and outgoing amounts start with "-"
    - style: incoming amounts use the success color token; outgoing amounts use the text color token

## /accounts/travel

- name: account-travel
- preconditions: TinyLedger Web seed data is loaded; the Travel fund account has no transactions.
- flow:
    1. navigate /accounts/travel
    2. wait for heading name="Travel fund"
- a11y:
    - axe: no violations
    - tab-order: interactive controls follow DOM order

### scenario: travel-empty

- viewport(s): 375px, 768px, 1280px
- state: no transactions
- setup:
    1. reload route
    2. wait for heading name="Travel fund"
- assertions:
    - visible: text="No transactions yet"
    - visible: link name="Make a transfer"
    - attribute: link name="Make a transfer" href="/transfer"
    - hidden: table inside main
