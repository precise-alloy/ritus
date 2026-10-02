# TL-27: Refund a mistaken transfer

Level: STANDARD - money movement (payments risk area) - Last reviewed: 2026-09-24 10:05 UTC
Sources: Jira TL-27 (In Progress)

## Summary

Support staff undo a mistaken transfer as its own ledger movement; the fee comes back from the fees account when the
mistake was ours; refunds above $500.00 are refused until TL-31 adds a second approver.

## Acceptance criteria

The task files carry each criterion with its check.

## Task breakdown

| # | Task | Depends |
|---|---|---|
| 001 | `refund()` with the $500 limit | - |
| 002 | `tl refund` | 001 |
