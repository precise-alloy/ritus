"""Write the iteration 15 scenarios (lv1-lv3 verify-task, lr1-lr4 pr-review) for the TL-40 EPIC. Re-runnable.

Run make_it15.py first: the executor reports cite line numbers read from its layers.
"""
import json
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURE = HERE.parent / "fixture"
LAYERS = FIXTURE / "layers"
SCEN = FIXTURE / "scenarios"
TASK_DIR = "docs/tasks/feature-TL-40-refunds"
CHECKS = "- [ ] [AC{n}] `npm run build` -> exit 0; `npm test` -> 0 failures; `npm run lint` -> `lint ok`"

PLAN = """# TL-40: Refunds and refund history

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
"""

TASKS = {
    "001-refund.md": """# Task 001: Add refund()

Level: EPIC - Depends on: none - Plan: docs/reviews/TL-40-review.md
Status: {status}

## Goal

Support staff can undo a mistaken transfer (TL-40): the transferred amount goes back to the sender, and when the
mistake was ours the sender also gets the transfer fee back. The limit, the receipt and the command are tasks 002-004.

## Acceptance

- [ ] [AC1] `refund(ledger, 'alice', 'bob', 2000)` moves 2000 cents from bob back to alice and leaves the fees account
  unchanged - a test in `test/refund.test.js`
- [ ] [AC2] With `{ refundFee: true }`, alice also gets back the fee `computeFee(amountCents, 'transfer')` charges, taken
  from the fees account; a 1050-cent refund returns an 11-cent fee (half-up, D-002) - a test
- [ ] [AC3] All or nothing: when bob's balance is below the amount, it throws `InsufficientFundsError` and no balance
  changes - a test
- [ ] [AC4] It refuses `fromId === toId`, and an amount that is not a positive whole number of cents, with `RangeError`,
  changing nothing - a test
- [ ] [AC5] It resolves to `{ id: 'R-<receipt number>', fromId, toId, amountCents, feeCents }`, where `feeCents` is the
  fee refunded (0 without `refundFee`) - a test
""" + CHECKS.format(n=6) + """

## Constraints

- All balance changes of a refund go through one `ledger.apply()` call, so a refund is all or nothing (D-003).
- Expected values in tests are literals, not the fee formula written out again (L-002).

## Interfaces

- Produces: `refund(ledger, fromId, toId, amountCents, { refundFee = false } = {}): Promise<{ id, fromId, toId,
  amountCents, feeCents }>` in `src/refund.js`

## Non-goals

- The $500 limit (002), the refund receipt (003), the `tl refund` command (004), recording the movement (005);
  partial refunds.

## Starting points

- `src/transfer.js:5-19` - the operation a refund reverses; mirror its shape
- `src/ledger.js:35-57` - `apply(entries)` is all or nothing; the fees account may go negative (`src/ledger.js:44`)
- `test/transfer.test.js`, `test/helpers.js` - `tempLedger()` for tests that touch balances
""",
    "002-refund-limit.md": """# Task 002: Refuse refunds above $500.00

Level: EPIC - Depends on: 001 - Plan: docs/reviews/TL-40-review.md
Status: {status}

## Goal

Refunds above $500.00 need a second approver, which TL-31 adds; until then `refund()` refuses them (TL-40).

## Acceptance

- [ ] [AC1] Refunds above $500.00 are refused with `RangeError` `Refunds above $500.00 need a second approver (TL-31)`
  until TL-31: exactly 50000 cents goes through, and 50001 cents is refused and changes nothing - a test
""" + CHECKS.format(n=2) + """

## Interfaces

- Produces: `REFUND_LIMIT_CENTS = 50000` in `src/refund.js`

## Starting points

- `src/refund.js` - `refund()`, from task 001; validate before any ledger call
""",
    "003-refund-receipt.md": """# Task 003: Render a refund receipt

Level: EPIC - Depends on: 001 - Plan: docs/reviews/TL-40-review.md
Status: {status}

## Goal

Support hands the customer a receipt for a refund, like the one for a transfer (TL-40).

## Acceptance

- [ ] [AC1] `renderRefundReceipt({ id: 'R-1002', fromId: 'alice', toId: 'bob', amountCents: 1050, feeCents: 11 })`
  returns the lines `Refund R-1002`, `Back to: alice`, `From: bob`, `Amount: $10.50`, `Fee returned: $0.11` - a test in
  `test/receipt.test.js`
- [ ] [AC2] Without a refunded fee (`feeCents: 0`) there is no `Fee returned` line - a test
- [ ] [AC3] An optional currency renders amounts like `renderReceipt` does (`EUR` -> `€10.50`) - a test
""" + CHECKS.format(n=4) + """

## Interfaces

- Produces: `renderRefundReceipt(refund, currency = 'USD'): string` in `src/receipt.js`

## Starting points

- `src/receipt.js:3-10` - `renderReceipt`, the transfer receipt to mirror
""",
    "004-refund-command.md": """# Task 004: Add `tl refund`

Level: EPIC - Depends on: 002, 003 - Plan: docs/reviews/TL-40-review.md
Status: {status}

## Goal

Support staff run `tl refund <from> <to> <amount> [--fee]` and get the refund receipt (TL-40).

## Acceptance

- [ ] [AC1] `tl refund alice bob 10.50 --fee` prints the refund receipt from `renderRefundReceipt`, exit 0 - a test in
  `test/cli.test.js`
- [ ] [AC2] Above the limit: `tl refund alice bob 600.00` prints
  `Error: Refunds above $500.00 need a second approver (TL-31)`, exit 1 - a test
- [ ] [AC3] USAGE lists `tl refund <from> <to> <amount> [--fee]` - diff: `src/cli.js`
""" + CHECKS.format(n=4) + """

## Interfaces

- Consumes: `refund()` (001, with the 002 limit) and `renderRefundReceipt()` (003)

## Starting points

- `src/cli.js:15-26` - `commands`; add `refund` next to `withdraw`
""",
    "005-movement-log.md": """# Task 005: Record every movement in the ledger

Level: EPIC - Depends on: 001 - Plan: docs/reviews/TL-40-review.md
Status: {status}

## Goal

Support needs an account's refund history (TL-40), and the ledger keeps only balances. From now on every applied
movement is recorded with its receipt id, kind, details and time; task 006 reads them.

## Acceptance

- [ ] [AC1] `ledger.apply(entries, { kind, memo })` records `{ id: 'R-<receipt number>', kind, at, memo }`, where `at`
  is the ledger clock's time as an ISO string; `ledger.movements()` resolves to every recorded movement, oldest first.
  Without options the kind is `adjustment` and the memo `{}` - a test in `test/ledger.test.js`
- [ ] [AC2] A refused `apply()` records nothing - a test
- [ ] [AC3] `transfer()`, `withdraw()` and `refund()` record their movement with kind `transfer`, `withdraw` and
  `refund`; the memo is `{ fromId, toId, amountCents, feeCents }` (withdraw: `{ accountId, amountCents, feeCents }`) -
  a test for each
- [ ] [AC4] A ledger file written before this change (no `movements`) still loads: `movements()` resolves to `[]` and
  the next `apply()` records normally - a test
- [ ] [AC5] `new Ledger(path, { now })` and `Ledger.create(path, balances, { now })` take the clock, a function
  returning a `Date`; the default is the system time - a test
""" + CHECKS.format(n=6) + """

## Constraints

- The movement is saved in the same write as the balances, inside `apply()`, so the two can't disagree (D-003).
- `tempLedger()` in `test/helpers.js` passes the options through; existing callers keep working.

## Interfaces

- Produces: `apply(entries, { kind = 'adjustment', memo = {} } = {})`, `movements(): Promise<Array<{ id, kind, at,
  memo }>>` and the `now` option, in `src/ledger.js`
- Consumes: `refund()` (001)

## Starting points

- `src/ledger.js:35-57` - `apply()`; the receipt number is taken just before the save
- `src/transfer.js`, `src/withdraw.js`, `src/refund.js` - the three callers of `apply()`
- `test/helpers.js` - `tempLedger()`
""",
    "006-list-refunds.md": """# Task 006: List an account's refunds

Level: EPIC - Depends on: 005 - Plan: docs/reviews/TL-40-review.md
Status: {status}

## Goal

Support looks up the refunds an account took part in (TL-40), whichever side of the refund it was on.

## Acceptance

- [ ] [AC1] `listRefunds(ledger, { accountId })` resolves to every refund the account took part in - as the account
  the money went back to (`fromId`) or the account it came from (`toId`) - newest first - a test in
  `test/refunds.test.js`
- [ ] [AC2] Each item is `{ id, at, fromId, toId, amountCents, feeCents }`, taken from the refund's movement - a test
- [ ] [AC3] Transfers and withdrawals are not listed; an account without refunds gets `[]` - a test
- [ ] [AC4] An unknown account is refused with `AccountNotFoundError` - a test
""" + CHECKS.format(n=5) + """

## Interfaces

- Produces: `listRefunds(ledger, { accountId }): Promise<Array<{ id, at, fromId, toId, amountCents, feeCents }>>` in
  `src/refunds.js`
- Consumes: `ledger.movements()` (005)

## Starting points

- `src/ledger.js` - `movements()`, and `getBalance()`, which throws `AccountNotFoundError`
""",
    "007-refunds-report.md": """# Task 007: Add `tl refunds`

Level: EPIC - Depends on: 004, 006 - Plan: docs/reviews/TL-40-review.md
Status: {status}

## Goal

Support staff run `tl refunds <account>` to see an account's refunds with totals (TL-40).

## Acceptance

- [ ] [AC1] `renderRefundReport(accountId, refunds)` returns `Refunds for <account>`, then one line per refund in the
  order given: `<id>  <date>  <back to> <- <from>  <amount>`, plus `  fee <fee>` when a fee was returned; `<date>` is
  the refund's UTC day (`YYYY-MM-DD`) - a test in `test/report.test.js`
- [ ] [AC2] The last line counts the refunds and totals their amounts and returned fees:
  `2 refunds, $25.00 back, $0.20 fees`; one refund reads `1 refund, ...` - a test
- [ ] [AC3] An account without refunds gets `No refunds for <account>` - a test
- [ ] [AC4] `tl refunds <account>` prints that report for `listRefunds()`'s result, exit 0; USAGE lists
  `tl refunds <account>` - a test in `test/cli.test.js`
""" + CHECKS.format(n=5) + """

## Interfaces

- Produces: `renderRefundReport(accountId, refunds): string` in `src/report.js`
- Consumes: `listRefunds()` (006)

## Starting points

- `src/cli.js` - `commands`; add `refunds` next to `refund`
- `src/money.js` - `formatAmount()`
""",
    "008-refunds-csv.md": """# Task 008: Add `tl refunds --csv`

Level: EPIC - Depends on: 007 - Plan: docs/reviews/TL-40-review.md
Status: {status}

## Goal

Finance imports an account's refunds into a spreadsheet (TL-40).

## Acceptance

- [ ] [AC1] `renderRefundsCsv(refunds)` returns the header `id,date,back_to,from,amount,fee`, then one row per refund
  in the order given, amounts as plain decimals: `R-1004,2026-09-02,alice,bob,20.00,0.20`; no fee is `0.00` - a test
  in `test/report.test.js`
- [ ] [AC2] A field holding a comma or a double quote is wrapped in double quotes, with inner quotes doubled
  (RFC 4180): `acme, inc` -> `"acme, inc"` - a test
- [ ] [AC3] Without refunds it is the header line alone - a test
- [ ] [AC4] `tl refunds <account> --csv` prints that CSV, exit 0; USAGE shows `tl refunds <account> [--csv]` - a test
  in `test/cli.test.js`
""" + CHECKS.format(n=5) + """

## Interfaces

- Produces: `renderRefundsCsv(refunds): string` in `src/report.js`

## Starting points

- `src/report.js` - `renderRefundReport()`, from 007
- `src/cli.js` - the `refunds` command, from 007
""",
}

EXPLORATION = """# Exploration log - feature-TL-40-refunds

## {{ago:90}} - plan

- [DECISIONS] A refund is its own ledger movement, one apply() call; nothing already recorded is edited
- [DECISIONS] Every applied movement is recorded in the ledger file with its receipt id, kind, memo and time (005)
"""

REVIEW_HEAD = """Review mode: local pre-PR review of branch `feature/TL-40-refunds` - the whole worktree against `origin/main`.
The change is uncommitted: the user commits at the end of the run.
Requirement source: the plan `docs/reviews/TL-40-review.md` and the task files in `docs/tasks/feature-TL-40-refunds/`.
The tasks' Goals carry the ticket text, so don't fetch TL-40.
"""
UNVERIFIED = "No per-task verification ran: re-run each task's Acceptance commands and build, test, and lint yourself."
VERIFIED = "Per-task verification ran: verify-task passed tasks 001-008 on this tree, and nothing has changed since."


def span(rel: str, title: str) -> tuple[int, int]:
    lines = (LAYERS / rel).read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines, 1) if line.startswith(f"test('{title}'"))
    end = next(i for i, line in enumerate(lines, 1) if i > start and line == "});")
    return start, end


def s(rel: str, title: str) -> str:
    a, b = span(rel, title)
    return f"{a}-{b}"


def first(rel: str, title: str) -> int:
    return span(rel, title)[0]


def line_of(rel: str, title: str, needle: str) -> int:
    a, b = span(rel, title)
    lines = (LAYERS / rel).read_text(encoding="utf-8").splitlines()
    return next(i for i in range(a, b + 1) if needle in lines[i - 1])


def report(acceptance: list[str], files: list[str], added: list[str]) -> str:
    return "\n".join(["Status: DONE", "Acceptance:", *acceptance, "Files changed:", *files, "Tests added:", *added,
                      "Tests changed: none", "Deviations: none", "Also affects: none", "Docs updated: none",
                      "Follow-ups: none"])


def verify_inputs(task: str, text: str) -> str:
    return (f"Task file: `{TASK_DIR}/{task}` (paths are relative to the project repository)\n"
            "Read-only apart from build/test/lint and the spot check it undoes (`testing.md`); never fixes.\n\n"
            f"Executor's report:\n\n```text\n{text}\n```\n")


CHECKS_LINE = "npm run build -> build ok; npm test -> {{TESTS_PASS}} passed, 0 failed; npm run lint -> lint ok"

R1 = "l-b1-t1/test/refund.test.js"
LV1 = report(
    [f"- [AC1] amount goes back from bob to alice, fees unchanged - src/refund.js; test/refund.test.js:"
     f"{s(R1, 'refund moves the amount back to the sender and leaves the fees account alone')}",
     f"- [AC2] refundFee returns the transfer fee from the fees account; 1050 -> 11 cents - src/refund.js; "
     f"test/refund.test.js:{s(R1, 'refundFee gives the transfer fee back from the fees account')}",
     f"- [AC3] all or nothing on InsufficientFundsError - one ledger.apply(); test/refund.test.js:"
     f"{s(R1, 'refund changes nothing when the recipient cannot cover the amount')}",
     f"- [AC4] same account and bad amounts refused with RangeError - test/refund.test.js:"
     f"{s(R1, 'refund refuses the same account and amounts that are not positive whole cents')}",
     f"- [AC5] resolves to {{ id, fromId, toId, amountCents, feeCents }} - test/refund.test.js:"
     f"{line_of(R1, 'refund moves the amount back to the sender and leaves the fees account alone', 'deepEqual(receipt')}, "
     f"{line_of(R1, 'refundFee gives the transfer fee back from the fees account', 'deepEqual(receipt')}",
     f"- [AC6] {CHECKS_LINE}"],
    ["- src/refund.js - refund()", "- test/refund.test.js - refund tests"],
    [f"- test/refund.test.js:{first(R1, 'refund moves the amount back to the sender and leaves the fees account alone')}"
     " - fails if the amount doesn't go back or the fees account changes",
     f"- test/refund.test.js:{first(R1, 'refundFee gives the transfer fee back from the fees account')}"
     " - fails if refundFee doesn't return the fee from the fees account",
     f"- test/refund.test.js:{first(R1, 'refund changes nothing when the recipient cannot cover the amount')}"
     " - fails if a refused refund changes a balance",
     f"- test/refund.test.js:{first(R1, 'refund refuses the same account and amounts that are not positive whole cents')}"
     " - fails if the same account or a bad amount is accepted"])

R2 = "l-b2-t6/test/refunds.test.js"
LV2 = report(
    [f"- [AC1] every refund the account took part in, as fromId or toId, newest first - src/refunds.js; "
     f"test/refunds.test.js:{s(R2, 'lists the refunds an account took part in, newest first')}",
     f"- [AC2] items are {{ id, at, fromId, toId, amountCents, feeCents }} from the refund's movement - "
     f"test/refunds.test.js:{line_of(R2, 'lists the refunds an account took part in, newest first', 'deepEqual')}",
     f"- [AC3] transfers and withdrawals are not listed; [] without refunds - test/refunds.test.js:"
     f"{s(R2, 'transfers and withdrawals are not refunds')}",
     f"- [AC4] unknown account -> AccountNotFoundError - src/refunds.js; test/refunds.test.js:"
     f"{s(R2, 'an unknown account is refused')}",
     f"- [AC5] {CHECKS_LINE}"],
    ["- src/refunds.js - listRefunds()", "- test/refunds.test.js - listRefunds tests"],
    [f"- test/refunds.test.js:{first(R2, 'lists the refunds an account took part in, newest first')}"
     " - fails if a refund is missing, extra or out of order",
     f"- test/refunds.test.js:{first(R2, 'transfers and withdrawals are not refunds')} - fails if a transfer or "
     "withdrawal is listed",
     f"- test/refunds.test.js:{first(R2, 'an unknown account is refused')} - fails if an unknown account is accepted"])

RP, CL = "l-t7/test/report.test.js", "l-t7/test/cli.test.js"
LV3 = report(
    [f"- [AC1] one line per refund in the order given, the fee when one was returned, the UTC day - src/report.js; "
     f"test/report.test.js:{s(RP, 'the report lists each refund and totals them')}",
     f"- [AC2] totals line, singular for one refund - test/report.test.js:"
     f"{s(RP, 'the report lists each refund and totals them')}, {s(RP, 'one refund is counted in the singular')}",
     f"- [AC3] `No refunds for <account>` - test/report.test.js:{s(RP, 'an account without refunds says so')}; "
     f"test/cli.test.js:{s(CL, 'refunds for an account without any says so')}",
     f"- [AC4] `tl refunds <account>` prints the report, exit 0; USAGE lists it - src/cli.js; test/cli.test.js:"
     f"{s(CL, 'refunds prints the account report')}",
     f"- [AC5] {CHECKS_LINE}"],
    ["- src/report.js - renderRefundReport()", "- src/cli.js - the refunds command and its USAGE line",
     "- test/report.test.js - report tests", "- test/cli.test.js - refunds command tests"],
    [f"- test/report.test.js:{first(RP, 'the report lists each refund and totals them')} - fails if a line, the order "
     "or a total is wrong",
     f"- test/report.test.js:{first(RP, 'one refund is counted in the singular')} - fails if one refund reads plural",
     f"- test/report.test.js:{first(RP, 'an account without refunds says so')} - fails if an empty report prints lines",
     f"- test/cli.test.js:{first(CL, 'refunds prints the account report')} - fails if the command doesn't print "
     "listRefunds' refunds as the report",
     f"- test/cli.test.js:{first(CL, 'refunds for an account without any says so')} - fails if an account without "
     "refunds errors"])

A = lambda i, check, text: {"id": i, "check": check, "text": text}  # noqa: E731
RO = "Leaves the working tree exactly as it found it"
NOFALSE_V = "Every other defect it reports is real"
NOFALSE_R = "No blocking finding that isn't real"
FEE_V = ("The FAIL is tied to task 001's refunded fee: wrong for 1050 cents (10, not 11), not computeFee's half-up "
         "fee, or AC2's 1050 -> 11 case untested")
FEE_R = ("A blocking finding is tied to task 001's refunded fee: wrong for 1050 cents (10, not 11), not computeFee's "
         "half-up fee, or AC2's 1050 -> 11 case untested")
FEE_NAMED = ("States that a 1050-cent refund returns a 10-cent fee, or that the fee is floored instead of computeFee's "
             "half-up - observed by running it or read from src/refund.js")
SPREAD = ("The finding says the fix reaches past src/refund.js: tests of later tasks assert the wrong fee ($0.10, "
          "0.10 or feeCents 10) and have to change with it")
FILTER_V = ("The FAIL is tied to listRefunds leaving out refunds where the account is the one the money came from "
            "(toId), or to AC1's 'either side' case being untested")
FILTER_R = ("A blocking finding is tied to listRefunds leaving out refunds where the account is the one the money "
            "came from (toId), or to AC1's 'either side' case being untested")
FILTER_NAMED = ("States that refunds where the account is the toId side are left out - observed (bob's list is empty, "
                "say) or read from the filter on memo.fromId only")
RAN = "Ran build, test and lint itself"
NORERUN = ("Doesn't re-run build and test: verification passed on this tree and nothing changed since "
           "(pr-review step 2)")

SCENARIOS = {
    "lv1": dict(
        statuses=["implemented"] + ["todo"] * 7,
        inputs=verify_inputs("001-refund.md", LV1),
        prompt="verify-task, EPIC task 001 of 8 (refund()) whose refunded fee floors instead of rounding half-up "
               "(1050 -> 10, AC2 says 11); its test covers 2000 only; only task 001 is implemented.",
        expected="VERIFY: FAIL tied to the refunded fee.",
        assertions=[A("lv1.fail", "auto", "Returns VERIFY: FAIL"), A("lv1.read_only", "auto", RO),
                    A("lv1.catches_fee", "judge", FEE_V), A("lv1.named_fee", "judge", FEE_NAMED),
                    A("lv1.no_false_defects", "judge", NOFALSE_V)]),
    "lv2": dict(
        statuses=["verified"] * 5 + ["implemented"] + ["todo"] * 2,
        inputs=verify_inputs("006-list-refunds.md", LV2),
        prompt="verify-task, EPIC task 006 of 8 (listRefunds) that only matches refunds where the account is fromId; "
               "its test only lists alice's refunds as fromId; 001-005 verified.",
        expected="VERIFY: FAIL tied to the missing toId refunds.",
        assertions=[A("lv2.fail", "auto", "Returns VERIFY: FAIL"), A("lv2.read_only", "auto", RO),
                    A("lv2.catches_filter", "judge", FILTER_V), A("lv2.named_filter", "judge", FILTER_NAMED),
                    A("lv2.no_false_defects", "judge", NOFALSE_V)]),
    "lv3": dict(
        statuses=["verified"] * 6 + ["implemented", "todo"],
        inputs=verify_inputs("007-refunds-report.md", LV3),
        prompt="verify-task, EPIC task 007 of 8 (tl refunds report); 001-006 verified. The code is right, but AC4 "
               "asks for a test that USAGE lists the command and none exists (left in the fixture by accident; the "
               "runs found it, so the expected verdict was corrected from PASS to FAIL before grading).",
        expected="VERIFY: FAIL for the missing USAGE test only; no invented defects.",
        assertions=[A("lv3.fail", "auto", "Returns VERIFY: FAIL (007 AC4's USAGE test is missing)"),
                    A("lv3.read_only", "auto", RO),
                    A("lv3.names_usage_gap", "judge",
                      "The FAIL names the missing test for 007 AC4's USAGE line - a break no test catches, or no "
                      "assertion on the USAGE text"),
                    A("lv3.no_false_defects", "judge",
                      "No defect it reports is invented: apart from the USAGE test, the task meets every acceptance "
                      "line")]),
    "lr1": dict(
        statuses=["implemented"] * 8,
        inputs=REVIEW_HEAD + UNVERIFIED + "\nNever fix anything.\n",
        prompt="pr-review, EPIC (8 tasks, 37 acceptance lines), no per-task verification; task 001's refunded fee "
               "floors (1050 -> 10) and the tests of 004-008 were written against it.",
        expected="Request Changes tied to the refunded fee.",
        assertions=[A("lr1.request_changes", "auto", "Returns Request Changes"), A("lr1.read_only", "auto", RO),
                    A("lr1.ran_checks", "auto", RAN), A("lr1.catches_fee", "judge", FEE_R),
                    A("lr1.named_fee", "judge", FEE_NAMED),
                    A("lr1.names_spread", "judge", SPREAD), A("lr1.no_false_positive", "judge", NOFALSE_R)]),
    "lr2": dict(
        statuses=["implemented"] * 8,
        inputs=REVIEW_HEAD + UNVERIFIED + "\nNever fix anything.\n",
        prompt="pr-review, EPIC (8 tasks, 37 acceptance lines), no per-task verification; task 006's listRefunds "
               "misses refunds where the account is toId, and its test doesn't cover that side.",
        expected="Request Changes tied to listRefunds.",
        assertions=[A("lr2.request_changes", "auto", "Returns Request Changes"), A("lr2.read_only", "auto", RO),
                    A("lr2.ran_checks", "auto", RAN), A("lr2.catches_filter", "judge", FILTER_R),
                    A("lr2.named_filter", "judge", FILTER_NAMED),
                    A("lr2.no_false_positive", "judge", NOFALSE_R)]),
    "lr3": dict(
        statuses=["implemented"] * 8,
        inputs=REVIEW_HEAD + UNVERIFIED + "\nNever fix anything.\n",
        prompt="pr-review, EPIC (8 tasks, 37 acceptance lines), no planted bug, no per-task verification (007/008 "
               "AC4 lack their USAGE test, a Recommended-level gap left by accident).",
        expected="Approve; no invented findings.",
        assertions=[A("lr3.approve", "auto", "Returns Approve"), A("lr3.read_only", "auto", RO),
                    A("lr3.ran_checks", "auto", RAN),
                    A("lr3.no_false_positive", "judge", NOFALSE_R)]),
    "lr4": dict(
        statuses=["verified"] * 8,
        inputs=REVIEW_HEAD + VERIFIED + "\nNever fix anything.\n",
        prompt="pr-review, EPIC (8 tasks, 37 acceptance lines), no planted bug, after per-task verification "
               "passed all 8 (007/008 AC4 lack their USAGE test, a Recommended-level gap left by accident).",
        expected="Approve without re-running build and test; no invented findings.",
        assertions=[A("lr4.approve", "auto", "Returns Approve"), A("lr4.read_only", "auto", RO),
                    A("lr4.no_rerun", "auto", NORERUN),
                    A("lr4.no_false_positive", "judge", NOFALSE_R)]),
}


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    for key, spec in SCENARIOS.items():
        root = SCEN / key
        if root.exists():
            shutil.rmtree(root)
        repo = root / "common" / "repo"
        write(repo / "docs/reviews/TL-40-review.md", PLAN)
        for (name, text), status in zip(TASKS.items(), spec["statuses"]):
            write(repo / TASK_DIR / name, text.replace("{status}", status))
        write(repo / TASK_DIR / "exploration.md", EXPLORATION)
        write(root / "inputs.md", spec["inputs"])
        write(root / "eval.json", json.dumps({"prompt": spec["prompt"], "expected_output": spec["expected"],
                                              "assertions": spec["assertions"]}, indent=2, ensure_ascii=False) + "\n")
        print(key, "->", root)
    total = sum(len(re.findall(r"^- \[ \] \[AC\d+\]", t, re.M)) for t in TASKS.values())
    print("acceptance lines:", total)


if __name__ == "__main__":
    main()
