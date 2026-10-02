# TL-16: Friendlier transfers - typed amounts and full receipts

> Last Reviewed: {{ts:2:15:30}} UTC
> Status: Ready for development
> Type: Feature

## 1. Questions, Assumptions & Decisions

### Open Questions (Needs Answer)

None.

### Assumptions

- Support staff type US-style amounts ("12.50", "1,234.00"); other locales are out of scope.
- The receipt fee is the `feeCents` that `transfer()` already returns (`src/transfer.js:18`).

### Decisions

- `tl transfer alice bob 12.50` replaces counting cents (`1250`). The typed amount must be greater than zero: "0" and
  "0.00" are refused, like any text that is not an amount (support lead, ticket comment - a zero transfer still
  creates a receipt number and confuses reconciliation).
- Anything refused throws `InvalidAmountError` (`src/errors.js:26-31`), so the CLI prints `Error: Invalid amount ...`
  and exits 1.
- Receipts gain `Fee:` and `Total:` (amount + fee) after the Amount line, in the receipt's currency; a zero fee is
  shown as `Fee: $0.00`.

## 2. Proposed Implementation

### Approach

1. `renderReceipt` (`src/receipt.js:3-10`) adds the two lines with `formatAmount(..., currency)`.
2. `parseAmount(input)` in `src/money.js` next to `formatAmount`: trim, match a strict pattern, convert to integer
   cents without float arithmetic (D-001), refuse zero and anything too large to count in cents.
3. `tl transfer` parses its amount argument with `parseAmount` (`src/cli.js:17-20`).

## 3. Detailed Task List

### 3.2 Services & Business Logic

| # | File Path        | Action | Description                                  |
|---|------------------|--------|----------------------------------------------|
| 1 | `src/receipt.js` | Modify | `Fee:` and `Total:` lines                    |
| 2 | `src/money.js`   | Modify | `parseAmount(input: string): number`         |

### 3.4 Controllers & Endpoints

| # | File Path    | Action | Description                                  |
|---|--------------|--------|----------------------------------------------|
| 1 | `src/cli.js` | Modify | `transfer` parses `<amount>` with parseAmount |

### 3.7 Unit Tests

| # | Test File Path         | Tests to Add                                     | Covers        |
|---|------------------------|--------------------------------------------------|---------------|
| 1 | `test/receipt.test.js` | fee and total lines; zero fee; currency          | task 001      |
| 2 | `test/money.test.js`   | valid forms; every refusal, including zero       | task 002      |
| 3 | `test/cli.test.js`     | typed amount; invalid amount prints an error     | task 003      |

## 4. QA Verification Notes

| # | Scenario       | Steps                            | Expected Result                              |
|---|----------------|----------------------------------|----------------------------------------------|
| 1 | Typed amount   | `tl transfer alice bob 12.50`    | receipt with `Fee: $0.13`, `Total: $12.63`   |
| 2 | Zero refused   | `tl transfer alice bob 0.00`     | `Error: Invalid amount "0.00": ...`, exit 1  |

## 5. Risks & Concerns

### Security

- Typed amounts are outside input: strict pattern, no float arithmetic, a size limit.
