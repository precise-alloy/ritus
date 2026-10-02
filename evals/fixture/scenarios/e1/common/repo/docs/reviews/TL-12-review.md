# TL-12: Show fee and total on receipts

> Last Reviewed: {{ts:16:14:05}} UTC
> Status: Ready for development
> Type: Feature

## 1. Questions, Assumptions & Decisions

### Open Questions (Needs Answer)

None.

### Assumptions

- The fee on the receipt is the `feeCents` that `transfer()` already returns (`src/transfer.js:18`); nothing is
  recomputed for display.
- Total means what the sender paid: amount + fee.

### Decisions

- Fee and Total go after the Amount line, in that order (support lead, ticket comment).
- A zero fee is shown as `Fee: $0.00` rather than omitted, so every receipt has the same shape (ticket comment).

## 2. Proposed Implementation

### Approach

`renderReceipt` (`src/receipt.js:3-10`) gains two lines, formatted with `formatCents` like the Amount line. The CLI
already prints whatever `renderReceipt` returns (`src/cli.js:19`), so no command changes.

## 3. Detailed Task List

### 3.2 Services & Business Logic

| # | File Path        | Action | Description                          |
|---|------------------|--------|--------------------------------------|
| 1 | `src/receipt.js` | Modify | Add `Fee:` and `Total:` after Amount |

### 3.7 Unit Tests

| # | Test File Path         | Tests to Add                                  | Covers                       |
|---|------------------------|-----------------------------------------------|------------------------------|
| 1 | `test/receipt.test.js` | receipt lists amount, fee, and total; zero fee | New lines, zero-fee receipts |

## 4. QA Verification Notes

| # | Scenario         | Steps                              | Expected Result                         |
|---|------------------|------------------------------------|-----------------------------------------|
| 1 | Transfer receipt | `tl transfer alice bob 1250`       | `Fee: $0.13` and `Total: $12.63` lines  |

## 5. Risks & Concerns

None identified.
