# TL-14: Withdrawals with a 2% fee

> Last Reviewed: {{ts:1:16:20}} UTC
> Status: Ready for development
> Type: Feature

## 1. Questions, Assumptions & Decisions

### Open Questions (Needs Answer)

None.

### Assumptions

- The `withdraw` fee kind is already in the schedule (`src/fees.js:2-3`: 200 bps, 25-cent minimum), so the fee
  schedule does not change.

### Decisions

- `withdraw()` returns the account's new balance in cents, and `tl withdraw` prints it as
  `formatAmount(withdraw(ledger, accountId, amountCents))` (support lead: "show me what is left").
- The fee goes to `FEES_ACCOUNT`, like transfer fees.
- No receipt for withdrawals in this ticket.

## 2. Proposed Implementation

### Approach

Follow the `docs/ARCHITECTURE.md` pattern "Add a money-moving operation": `src/withdraw.js` computes the fee with
`computeFee(amountCents, 'withdraw')` and applies the debit and the fee in one `ledger.apply()` call, so a withdrawal
the account cannot cover changes nothing. Task 002 adds `tl withdraw <account> <amount>`, parsing the amount with
`parseAmount` (`src/money.js:24`).

## 3. Detailed Task List

### 3.2 Services & Business Logic

| # | File Path         | Action | Description                                       |
|---|-------------------|--------|---------------------------------------------------|
| 1 | `src/withdraw.js` | Create | `withdraw(ledger, accountId, amountCents)`        |

### 3.4 Controllers & Endpoints

| # | File Path    | Action | Description                        |
|---|--------------|--------|------------------------------------|
| 1 | `src/cli.js` | Modify | `withdraw` command and USAGE line  |

### 3.7 Unit Tests

| # | Test File Path          | Tests to Add                                             | Covers              |
|---|-------------------------|----------------------------------------------------------|---------------------|
| 1 | `test/withdraw.test.js` | new balance and fee; minimum fee; insufficient funds     | `withdraw()`        |
| 2 | `test/cli.test.js`      | `withdraw` prints the new balance                        | `tl withdraw`       |

## 4. QA Verification Notes

| # | Scenario   | Steps                          | Expected Result |
|---|------------|--------------------------------|-----------------|
| 1 | Withdrawal | `tl withdraw alice 50.00`      | `$49.00`        |

## 5. Risks & Concerns

### Security

- None identified (internal tool; typed amounts go through `parseAmount`).
