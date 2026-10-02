# TL-40: Refunds and refund history

Level: EPIC - money movement (payments risk area) - Last reviewed: {{ts:1:10:05}} UTC
Sources: Jira TL-40 (In Progress)

## Summary

Support staff undo a mistaken transfer as its own ledger movement; the fee comes back from the fees account when the
mistake was ours; refunds above $500.00 are refused until TL-31 adds a second approver. Every movement is now recorded
in the ledger, so support can list an account's refunds with `tl refunds`, as a report or as CSV for finance.

## Acceptance criteria

The task files carry each criterion with its check.

## Task breakdown

One phase, one PR.

| # | Task | Depends |
|---|---|---|
| 001 | `refund()` | - |
| 002 | The $500 limit | 001 |
| 003 | Refund receipt | 001 |
| 004 | `tl refund` | 002, 003 |
| 005 | Record every movement in the ledger | 001 |
| 006 | `listRefunds()` | 005 |
| 007 | `tl refunds` report | 004, 006 |
| 008 | `tl refunds --csv` | 007 |
