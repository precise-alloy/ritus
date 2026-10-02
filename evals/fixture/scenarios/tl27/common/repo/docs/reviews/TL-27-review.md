# TL-27: Refund a mistaken transfer

Level: STANDARD - money movement (payments risk area) - Last reviewed: {{ts:1:10:05}} UTC
Sources: Jira TL-27 (In Progress), brainstorm decision brief from {{date:2}}

## Summary

Support staff undo a mistaken transfer as its own ledger movement: the amount goes back from the recipient to the
sender, and when the mistake was ours the transfer fee comes back from the fees account. Nothing already recorded is
edited, so finance can reconcile refunds (Linh Nguyen).

## Decisions (approved)

| # | Decision | Why |
|---|---|---|
| 1 | Support types the original parties and amount; no transfer history lookup | The ledger keeps only balances |
| 2 | One `ledger.apply()` call per refund | All or nothing (D-003) |
| 3 | The fee comes back only with `refundFee`, as `computeFee(amount, 'transfer')` | Support decides case by case |

## Acceptance criteria

See task 001; the CLI command is task 002.

## Task breakdown

| # | Task | Depends | Produces |
|---|---|---|---|
| 001 | `refund()` | - | `refund(ledger, fromId, toId, amountCents, { refundFee })` |
| 002 | `tl refund` | 001 | The CLI command |
