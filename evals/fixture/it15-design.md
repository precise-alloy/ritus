# Iteration 15 design - per-task verify vs end review on a large EPIC with cross-task bugs

User asked (after iteration 14): measure cross-task bugs and a large EPIC diff before deciding the verify policy.

## Feature: TL-40 refunds and refund history (EPIC, one phase/PR, 8 tasks, 37 AC)

Branch `feature/TL-40-refunds`, docs in `docs/tasks/feature-TL-40-refunds/`, plan `docs/reviews/TL-40-review.md`.
Main = TL27_MAIN; worktree = TL27_LAYERS + layers below.

| # | Task | Depends | Code |
|---|---|---|---|
| 001 | `refund()` | - | src/refund.js, test/refund.test.js |
| 002 | $500 limit | 001 | refund.js + test |
| 003 | refund receipt | 001 | receipt.js + test |
| 004 | `tl refund` | 002, 003 | cli.js + test |
| 005 | movement log: `apply(entries, { kind, memo })`, `movements()`, clock option | 001 | ledger.js, transfer.js, withdraw.js, refund.js, helpers.js, tests |
| 006 | `listRefunds(ledger, { accountId })` (fromId or toId, newest first) | 005 | src/refunds.js + test |
| 007 | `tl refunds <account>` report (lines + totals) | 006 | src/report.js, cli.js + tests |
| 008 | `tl refunds <account> --csv` (RFC 4180 quoting) | 007 | report.js, cli.js + tests |

## Worlds and bugs

- B1 (cross-task, encoded): 001 computes the refunded fee as `Math.floor(amount * FEE_RATES_BPS.transfer / 10000)`
  instead of `computeFee` (half-up): 1050 -> 10, AC2 says 11. 001 test is hollow (2000 -> 20 only). Later tests encode
  the wrong fee: cli (004 `10.50 --fee` -> `$0.10`), refunds (006 feeCents 10), report (007 `fee $0.10`, totals),
  csv (008 `0.10`). Fix late = refund.js + 4-5 test files; fix early = refund.js + refund.test.js.
- B2 (large diff, no deciding example): 006 filters `memo.fromId === accountId` only, so refunds the account paid back
  (toId) are missing; test only checks alice (fromId). 007/008 tests use alice only.

| Eval | Key | Skill | World | Expected |
|---|---|---|---|---|
| 37 | lv1 | verify-task 001 | B1, only 001 implemented | FAIL (fee rounding) |
| 38 | lv2 | verify-task 006 | B2, 001-006 implemented | FAIL (toId refunds missing) |
| 39 | lv3 | verify-task 007 | clean, 001-007 | PASS |
| 40 | lr1 | pr-review unverified | B1 full (001-008) | Request Changes (fee) |
| 41 | lr2 | pr-review unverified | B2 full | Request Changes (listRefunds) |
| 42 | lr3 | pr-review unverified | clean full | Approve |
| 43 | lr4 | pr-review verified | clean full | Approve, no re-run |

Layers: l-t1..l-t8 clean cumulative; l-b1-t1 (001-stage bug + hollow test); l-b1-full (final refund.js with floor,
hollow refund test, encoded cli/refunds/report tests); l-b2-t6 (refunds.js bug + hollow test).
