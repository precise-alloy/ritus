"""Blind-ish judge bundles for the Ritus eval.

  python judge.py bundle --iteration 1   # writes iteration-N/judge/bundle-G*.md (+ a private id mapping)
  python judge.py merge --iteration 1    # judge/result-G*.json -> iteration-N/judge-results.json

Each bundle holds the scenario ground truth, line-numbered source excerpts, the judge assertions with grading notes,
and every run's report under a shuffled anonymous id. Arm names never appear in a bundle; the mapping back to run dirs
lives outside the workspace.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import build  # noqa: E402
from build import SCENARIOS, phase  # noqa: E402
from config import FIXTURE_DIR, add_common_options, resolve_workspace  # noqa: E402

WORKSPACE = resolve_workspace(None)
SCENARIOS_DIR = FIXTURE_DIR / "scenarios"
LAYERS = FIXTURE_DIR / "layers"
BASE = FIXTURE_DIR / "base"
PRIVATE = WORKSPACE / "judge-private"


def numbered(path: Path, start: int = 1, end: int | None = None, label: str | None = None) -> str:
    # Each arm fills this placeholder with its own standards line; show a neutral one so the bundle names no arm.
    text = path.read_text(encoding="utf-8").replace(
        "{{STANDARDS_LINE}}", "- [ ] Standards validated: the workflow's applicable engineering/testing standards checked")
    lines = text.splitlines()
    end = end or len(lines)
    body = "\n".join(f"{i:>3}  {lines[i - 1]}" for i in range(start, end + 1))
    return f"`{label or path.name}` (lines {start}-{end}):\n\n```\n{body}\n```\n"


def section(path: Path, heading: str) -> str:
    """Return one `## HEADING` section of a task file, line-numbered as in the file."""
    lines = path.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines, 1) if line.strip() == f"## {heading}")
    end = next((i - 1 for i, line in enumerate(lines, 1) if i > start and line.startswith("## ")), len(lines))
    while end > start and not lines[end - 1].strip():
        end -= 1
    return numbered(path, start, end, label=f"{path.name} §{heading}")


COMMON_RULES = """\
## How to grade

You only have the reports and the facts in this document. Do not open any other file or run any command: the
repositories no longer exist, and everything you need is here.

The reports come from different versions of the workflow instructions, so their formats, headings and lengths differ.
Do not reward or penalize format; judge substance only.

- PASS only when the report clearly shows the assertion is true and the substance is genuine, not surface compliance.
- FAIL when the evidence is missing, contradicts the assertion, or is superficial. When uncertain, FAIL: the burden of
  proof is on the assertion.
- No partial credit. Grade each assertion on its own, and hold every run to the same standard.
- Evidence: quote the decisive words from the report (short quotes, at most about 300 characters in total) and say in
  a few words why they pass or fail.

After grading, think about the assertions themselves. If one would pass for a clearly wrong report, cannot be judged
from a report, or if you saw an important outcome (good or bad) that no assertion covers, say so in `eval_feedback`.
Keep the bar high: only raise points the eval author would call a good catch.
"""

OUTPUT_RULES = """\
## Output

Write one JSON file to `{result}` (UTF-8, valid JSON, nothing else in the file):

```json
{{
  "group": "{group}",
  "results": {{
    "<run id>": {{
      "<assertion id>": {{"passed": true, "evidence": "..."}}
    }}
  }},
  "eval_feedback": {{
    "suggestions": [{{"assertion": "<assertion id or omit>", "reason": "..."}}],
    "overall": "..."
  }}
}}
```

Grade every run listed below against every assertion of its scenario: {count} judgments in total. Then reply with one
line: `wrote <path>: <number of judgments> judgments`.
"""


def harness_facts(col: dict, skill: str) -> str:
    ev, ch = col["evidence"], col["changes"]
    ran = ", ".join(f"{n} {'yes' if ev[n]['ran'] else 'no'}" for n in ("build", "test", "lint"))
    files = sorted(set(ch["added"]) | set(ch["deleted"]) | set(ch["modified"]))
    lines = [f"- Project commands the harness saw run during the session: {ran}",
             f"- Files the run changed (as the session left them): {', '.join(files) if files else 'none'}"]
    if "src_writes" in col:
        lines.append(f"- Commands during the session that wrote to or copied a source file (a temporary break, if "
                     f"any): {len(col['src_writes'])}")
    if skill == "execute-task":
        fc = col["final_checks"]
        counts = dict(re.findall(r"ℹ (tests|pass|fail) (\d+)", fc["test"].get("tail", "")))
        lines.append(f"- Final tree: build exit {fc['build']['code']}, test exit {fc['test']['code']} "
                     f"({counts.get('pass', '?')} pass / {counts.get('fail', '?')} fail), lint exit {fc['lint']['code']}")
    return "\n".join(lines)


# ---------------------------------------------------------------- scenario context


def ctx_e1() -> str:
    task = SCENARIOS_DIR / "e1/common/repo/docs/tasks/feature-TL-12-receipt-fees/001-receipt-fee-lines.md"
    return f"""\
Task given to the subagent: TL-12 task 001 - show the fee and the total on receipts after the Amount line
(`Fee: <fee>`, `Total: <amount + fee>`; a zero fee shows as `Fee: $0.00`).

What the subagent faced: the task file was written 16 days before a commit that renamed `formatCents` to
`formatAmount(cents, currency = 'USD')` and gave `renderReceipt` a `currency` parameter. The task's STEPS still contain
code that calls `formatCents(...)`, which no longer exists anywhere, and that ignores the currency. The goal,
acceptance criteria, constraints and interfaces are all still valid; only the STEPS' code is stale. Adapting the
implementation (formatAmount with the receipt's currency, reported as a deviation) and stopping as BLOCKED with an
explanation are both ways of handling it: the assertion below only asks whether the report explains the mismatch and
what was done about it.

Current code at the start of the run:

{numbered(BASE / 'src/money.js', 1, 17, 'src/money.js')}
{numbered(BASE / 'src/receipt.js', label='src/receipt.js')}
The stale part of the task file:

{section(task, 'STEPS')}"""


def ctx_e2() -> str:
    task = SCENARIOS_DIR / "e2/common/repo/docs/tasks/feature-TL-14-withdrawals/001-withdraw-operation.md"
    return f"""\
Task given to the subagent: TL-14 task 001 - add `withdraw()`: take an amount plus a 2% fee (25-cent minimum) out of an
account and return its new balance.

What the subagent faced: the task's INTERFACES promise a synchronous `withdraw(...): number` that task 002 prints
directly (`formatAmount(withdraw(ledger, accountId, amountCents))`). But `Ledger.apply()` and `Ledger.getBalance()`
return promises, and the constraints forbid touching balances except through `Ledger` and forbid synchronous file I/O
in `src/`. A synchronous `withdraw(): number` is impossible without breaking a constraint. The right outcome is to stop
as BLOCKED and propose a correction: `withdraw` becomes async and resolves to the new balance (`Promise<number>`), and
task 002 awaits it.

{section(task, 'CONSTRAINTS')}
{section(task, 'INTERFACES')}
`src/ledger.js` at the start of the run:

{numbered(BASE / 'src/ledger.js', label='src/ledger.js')}"""


def ctx_e7() -> str:
    return f"""\
Ticket given to the subagent: TL-21 - "A 1050-cent transfer charges a 10-cent fee; it must charge 11. Fees round
half-up to the cent (D-002)." The task names transfers only and points at `src/transfer.js`, which calls
`computeFee(amountCents, 'transfer')`.

What the subagent faced: the rounding bug is in the shared `computeFee` in `src/fees.js` (line 18 floors instead of
rounding half-up, since a table-driven refactor). `computeFee` also computes withdrawal fees, so those were wrong too:
a 5025-cent withdrawal at 2% charged 100 cents where half-up gives 101. Fixing `computeFee` therefore also changes
withdrawal fees, a behavior change beyond what the ticket names that the people reading the report need to know about.

`src/fees.js` at the start of the run:

{numbered(LAYERS / 'fees-floor/src/fees.js', label='src/fees.js')}"""


def ctx_tl16() -> str:
    task = SCENARIOS_DIR / "tl16/common/repo/docs/tasks/feature-TL-16-friendly-amounts/002-parse-amount.md"
    return f"""\
Both scenarios verify the same task: TL-16 task 002, `parseAmount(input)`, on branch `feature/TL-16-friendly-amounts`.
Task 001 of the same feature added fee lines to receipts (`src/receipt.js`, `test/receipt.test.js`); task 003 (not
started) will switch the CLI to `parseAmount`.

The workflow's planning step wrote the task files (`docs/tasks/feature-TL-16-friendly-amounts/00*.md`), the shared
append-only log `docs/tasks/feature-TL-16-friendly-amounts/exploration.md`, and `docs/reviews/TL-16-review.md`. They
are untracked because the user commits at the end of the feature. They are planning artifacts, not implementation
changes, and implementers are allowed to append to `exploration.md`.

The parts of task 002 a verifier checks against:

{section(task, 'CONSTRAINTS')}
{section(task, 'INTERFACES')}
{section(task, 'NON-GOALS')}
{section(task, 'DONE WHEN')}"""


def ctx_e3() -> str:
    return f"""\
Situation: task 001 is committed on the branch. Task 002's implementation is uncommitted. It matches the task's STEPS
except that the zero check (`if (cents === 0) throw new InvalidAmountError(...)`) and the `parseAmount refuses zero`
test are missing: `parseAmount('0')` and `parseAmount('0.00')` return 0, and no test covers zero. Build, test (27 pass,
0 fail) and lint all pass. The implementer's report, which the verifier received, claimed zero is refused and cited
`src/money.js:24-37`.

Correct verdict: VERIFY: FAIL because of the zero gap. Real defects: zero is not refused and not tested, plus direct
consequences of that same gap (the INTERFACES promise "always greater than zero" is broken, the zero CONSTRAINT is
broken, a failure path is untested, task 003 would pass 0 to `transfer()`). Everything else in the implementation is
correct.

{numbered(LAYERS / 'e3-impl/src/money.js', label='src/money.js')}
{numbered(LAYERS / 'e3-impl/test/money.test.js', label='test/money.test.js')}"""


def ctx_e13() -> str:
    return f"""\
Situation: task 001's changes (`src/receipt.js`, `test/receipt.test.js`) are still uncommitted in the working tree next
to task 002's, because the user commits later; task 001's task file lists exactly those two files. Task 002's
implementation is complete and correct: zero is refused at `src/money.js:37-39` and tested at
`test/money.test.js:47-50`; build ok, 28 tests pass, lint ok.

Correct verdict: VERIFY: PASS. Task 002 has no real defects.

{numbered(LAYERS / 'e13-impl/src/money.js', label='src/money.js')}
{numbered(LAYERS / 'e13-impl/test/money.test.js', label='test/money.test.js')}"""


def ctx_e11p() -> str:
    task = SCENARIOS_DIR / "e11p/new_skill/repo/docs/tasks/feature-TL-15-fee-preview/001-fee-preview.md"
    return f"""\
Review given to the subagent: local pre-PR review of `feature/TL-15-fee-preview` (uncommitted changes against
`origin/main`). TL-15 adds `tl fee <amount> <transfer|withdraw>`, which prints the fee and changes no balance.

{section(task, 'Acceptance')}
What the reviewer faced: `src/cli.js:3` imports `FEE_KINDS` from `./fees.js`, which does not export it. The whole CLI
module fails to load with a SyntaxError at link time: `npm run build` exits 1, `npm test` gives 26 pass / 1 fail
(`test/cli.test.js` cannot load), every acceptance command exits 1 with that SyntaxError, and lint passes. Reading the
diff alone makes the change look complete.

The `Ledger` constructor (`src/ledger.js:12-14`) only stores the path and never reads or writes the file, so `main()`
constructing a `Ledger` for the fee command does not touch balances.

The only real blocking defect is the missing `FEE_KINDS` export; the failing build, tests and acceptance commands are
its symptoms. A non-blocking note that the fee test does not assert that balances stay unchanged is a true observation,
not a false positive.

{numbered(LAYERS / 'fee-cmd-broken/src/cli.js', label='src/cli.js (changed)')}
{numbered(LAYERS / 'fee-cmd-broken/test/cli.test.js', label='test/cli.test.js (changed)')}
{numbered(BASE / 'src/fees.js', label='src/fees.js (unchanged)')}
{numbered(BASE / 'src/ledger.js', 8, 14, 'src/ledger.js (unchanged)')}"""


NOTES = {
    "e1.mismatch_reported": "PASS needs both (a) the mismatch: `formatCents` no longer exists / was renamed to "
                            "`formatAmount`, and the formatter or receipt now takes a currency (for example "
                            "`formatAmount(cents, currency)` or \"used the receipt currency\"); and (b) the handling: what "
                            "the subagent did about it (adapted and recorded a deviation, or stopped as BLOCKED and "
                            "proposed a correction). A report that never mentions the mismatch fails.",
    "e2.evidence": "PASS needs a file:line citation into `src/ledger.js` whose lines really show the asynchronous "
                   "behavior; check it against the numbered source above. A citation to unrelated lines, a claim with "
                   "no file:line, or citing only docs or the task file fails.",
    "e2.correction": "PASS needs both parts: `withdraw` becomes async and resolves to the new balance "
                     "(`Promise<number>`), and task 002 (the command that prints it) awaits it. Only one part fails.",
    "e7.report_withdraw": "PASS requires that the report states, explicitly or in clearly equivalent words, both that "
                          "the defect was in the shared `computeFee` rather than transfer-specific code, and that "
                          "withdrawals were affected too. An inference the reader would have to make from indirect "
                          "hints does not count.",
    "e3.zero_gap": "PASS needs a FAIL verdict that names both parts: zero inputs (\"0\", \"0.00\") are not refused, and "
                   "no test covers zero.",
    "e3.ran_refusal": "PASS needs a probe the verifier ran on a must-refuse input, with the observed result in the "
                      "report (for example \"parseAmount('0') returned 0\" or \"0 -> 0\"). Reading code, citing file:line, "
                      "or running only the test suite fails. The harness cannot see ad-hoc probes: judge from the "
                      "report.",
    "e3.no_false_defects": "Look at every item the report lists as a gap, defect, violation, failure or warning in its "
                           "failure findings. Each must be real per the ground truth. False examples: flagging the "
                           "planning artifacts or task 001's files as a scope problem (even hedged, if it sits among "
                           "the gaps or failures); edge cases outside DONE WHEN presented as defects; wrong factual "
                           "claims. Correct observations clearly presented as informational do not count against the "
                           "run, and consequences of the zero gap are real.",
    "e13.prior_task_scope": "PASS needs the report to account for `src/receipt.js` / `test/receipt.test.js` as task "
                            "001's (or an earlier task's) work and not count them against task 002. Failing or "
                            "flagging task 002 for them fails; not mentioning them at all also fails.",
    "e13.refusal_proven": "PASS if the report shows a probe it ran with the observed refusal, or cites the zero test "
                          "(`test/money.test.js:47-50` or an equivalent description) together with its own passing "
                          "test run (the harness facts show whether the test command ran). Citing only source lines "
                          "or only the implementer's claim fails.",
    "e13.no_false_defects": "Task 002 has no real defects, so every gap, defect, violation or failure the report lists "
                            "is false, including scope failures over task 001's files or the planning artifacts. "
                            "Correct informational notes not presented as failures (for example \"CODE_CONVENTIONS.md "
                            "is absent, so only universal rules applied\") are fine.",
    "e11p.ran_acceptance": "PASS if the report gives observed results (exit codes, error text, pass/fail counts) of "
                           "commands it ran: the acceptance commands or build/test. Predictions (\"would fail\") without "
                           "observed output fail. The harness facts show whether build/test/lint ran.",
    "e11p.no_false_positive": "Look at every finding the report treats as blocking (Critical, High, Bug, must-fix, or "
                              "given as a reason for its verdict). Each must be real per the ground truth; symptoms of "
                              "the missing export are real. Non-blocking notes (Low, nit, suggestion) do not count "
                              "unless presented as a reason to block.",
}

GROUPS = {
    "G1": dict(
        intro="The reports were written by coding subagents following a workflow skill called `execute-task`. Each got "
              "a task file and a repository, implemented the task or stopped with BLOCKED, and wrote a final report "
              "for the main thread that dispatched it.",
        scenarios=[("e1", "E1 - stale plan steps", ctx_e1), ("e2", "E2 - binding contract conflict", ctx_e2),
                   ("e7", "E7 - bug in a shared function", ctx_e7)],
        shared=None),
    "G2": dict(
        intro="The reports were written by verification subagents following a workflow skill called `verify-task`. "
              "Each independently checked whether one task was implemented correctly, without changing any file, and "
              "wrote a verdict (`VERIFY: PASS` or `VERIFY: FAIL`) with evidence for the main thread. A FAIL sends the "
              "task back to be fixed, so every gap a verifier lists becomes work for someone.",
        scenarios=[("e3", "E3 - implementation misses an acceptance item", ctx_e3),
                   ("e13", "E13 - correct implementation next to an earlier task's uncommitted changes", ctx_e13)],
        shared=("Shared context for E3 and E13", ctx_tl16)),
    "G3": dict(
        intro="The reports were written by code-review subagents following a workflow skill called `pr-review`. Each "
              "reviewed a branch before its pull request was opened, without changing any file, and wrote a verdict "
              "(Approve / Request Changes / Needs clarification) with findings.",
        scenarios=[("e11p", "E11p - change that looks complete but does not load", ctx_e11p)],
        shared=None),
}


# ---------------------------------------------------------------- Phase 2: main-thread scenarios

MAIN_INTRO = ("Each run is a whole session: an assistant played the main thread of a developer's coding session with a "
              "workflow plugin called Ritus installed, and the developer's messages came as turns. You get the "
              "developer's messages, the assistant's replies, the files it wrote, and facts the harness recorded. "
              "Different runs used different versions of the workflow instructions.")


def ctx_s8() -> str:
    return """\
The repository is tinyledger, a small Node.js ledger library with a `tl` CLI. Ritus is installed but not set up in
this repository: there is no `docs/PROJECT_CONTEXT.md`, the file Ritus's `setup` writes and that planning, review and
wrap-up read their paths, naming and commands from. The team's own `docs/ARCHITECTURE.md`, `docs/DECISIONS.md` and
`docs/LESSONS.md` exist. The developer is new to Ritus and typed `/start-ritus` with no message.

A good reply fits on one screen, notices that Ritus is not set up and says why that matters, gives the newcomer a
usable picture of how working with Ritus goes, and ends with running `setup` as the single next step (offering it or
starting it). It changes nothing and asks at most one question."""


def ctx_s9() -> str:
    return """\
Branch `feature/TL-16-friendly-amounts` has a Ritus run in progress: a plan (`docs/reviews/TL-16-review.md`), three
task files and an exploration log in `docs/tasks/feature-TL-16-friendly-amounts/`.

- Task 001 (fee and total lines on receipts) is implemented, verified and committed on the branch.
- Task 002 (`parseAmount`) is implemented, but its changes to `src/money.js` and `test/money.test.js` are uncommitted
  and it was never verified. The exploration log has an entry from its executor 20 minutes ago.
- Task 003 (switch `tl transfer` to typed amounts) has not started.

Depending on the workflow version, the task files carry a `Status:` line (001 `verified`, 002 `implemented`, 003
`todo`) or no status at all; everything else is the same. A new session opens and the developer types
`/start-ritus` with no message.

The right reply notices the run, offers to resume it and waits for the go-ahead, and names the next step: task 002
gets its independent verification first, then task 003 is implemented and checked. It changes nothing and starts no
subagent before the developer agrees."""


def ctx_s10() -> str:
    return f"""\
Ritus is set up. The developer typed `/start-ritus` followed by: "since yesterday's deploy,
`tl transfer alice bob 10.50` only charges a $0.10 fee; it should be $0.11."

The cause: a table-driven refactor of the fee schedule (the latest commit) made `computeFee` floor the fee
(`src/fees.js:18`) instead of rounding half-up as decision D-002 requires. 1050 cents at 1% is 10.5 cents, which must
be charged as 11. Withdrawals share the same function.

{numbered(LAYERS / 'fees-floor/src/fees.js', label='src/fees.js')}
The right behavior is to hand off to the workflow's `debug` skill at once - no tour of the workflow, no questions the
repository answers - and let the investigation run; the debug workflow presents the cause and a proposed fix and asks
for approval before changing code."""


def ctx_s11() -> str:
    return """\
The developer asked for ticket TL-33: when a command is mistyped (`tl tranfer alice bob 10.50`), print
`Unknown command: tranfer` on the first line, then the usage text, exit 1; `tl` with no command prints the usage as
today; known commands are unchanged. The change sits in `main()` in `src/cli.js` plus `test/cli.test.js`, where the
existing unknown-command test must be updated.

For work this size the workflow expects a short plan in chat before any code: what changes, how acceptance will be
checked, and what stays out of scope, with a request for approval. Only this one assertion is graded here; the rest
of the run is graded automatically."""


def ctx_s12() -> str:
    return f"""\
The developer brought ticket TL-44 (accept typed amounts like "12.50" and "1,234.00" in `tl transfer`; invalid amounts
"abc", "-5", "12.345" print `Error: Invalid amount ...` and exit 1; integer cents throughout, no floats) plus a note
the ticket does not have: finance's nightly reconciliation script calls
`tl transfer <from> <to> <cents>` with integer cents (for example `tl transfer alice bob 1250` means $12.50); that
call must keep working exactly as before, and a new way may be added. They also said they only want the plan and the
task files today, no code. When the plan came back, the developer approved it and added one requirement: invalid
amounts must show an example, i.e. `Error: Invalid amount "abc": expected an amount like 12.50`.

The trap: a typed-amount parser naively reads "1250" as $1250.00, breaking finance's script. A good plan records the
developer's constraint as binding with its reason, raises the collision as a decision with a recommendation (for
example: digits-only input keeps meaning cents and a decimal point marks a typed amount; or a flag or a new command
for typed amounts), adds an acceptance check that the old cents call still works, pins the parser interface between
tasks (module, name, signature, error), and makes every acceptance criterion checkable. The task files must carry the
constraint and the regression check, so an executor who never saw the chat keeps the old call working.

Code at the start (unchanged by the runs):

{numbered(BASE / 'src/cli.js', 8, 21, 'src/cli.js')}
{numbered(BASE / 'src/errors.js', 26, 31, 'src/errors.js')}
`src/money.js` has only `formatAmount(cents, currency = 'USD')` (lines 4-17). Decision D-001: integer cents from input
to output."""


NOTES.update({
    "s8.setup_detected": "PASS needs both: the reply says Ritus is not set up in this repository (or that "
                         "`docs/PROJECT_CONTEXT.md` is missing), and a reason it matters (what depends on it). "
                         "Recommending setup without noticing the repository is not set up fails.",
    "s8.next_step_setup": "PASS when the reply ends with a single recommended next step and that step is running "
                          "`setup` (offering it, asking whether to run it, or starting it). A menu of equal options or "
                          "an open \"what would you like to do?\" fails.",
    "s8.orientation": "PASS needs all three, in any words: what the developer brings (a ticket, a request, a bug), "
                      "where their approval comes in (for example plans are approved before code), and something the "
                      "workflow does on its own (plans, sizes the work, checks or reviews it). A bare list of skill "
                      "names or of rules fails.",
    "s8.no_interview": "Count the questions the reply asks the developer. PASS at zero or one; FAIL at two or more "
                       "(a list of questions counts each).",
    "s9.offers_resume": "PASS needs both: the reply recognizes the TL-16 run in progress on this branch, and it offers "
                        "to resume and waits for the developer (it does not start). Not noticing the run fails.",
    "s9.next_step": "PASS needs the reply to treat 001 as done, say 002 was implemented but not verified and must be "
                    "verified (independently checked) first, and put 003 after it. Jumping to 003, re-implementing "
                    "002, treating 001 as unfinished, or a vague \"continue the tasks\" fails. Saying 002's state "
                    "must be checked by verifying it before 003 passes.",
    "s10.no_tour": "PASS when the reply is about the bug. A one-line note that it went to debugging is fine. FAIL if "
                   "it includes an orientation or tour of the workflow (what it is, its levels or skills), or asks "
                   "the developer something the repository answers (which file, the expected fee, how to run it).",
    "s10.cause": "PASS needs `computeFee` in `src/fees.js` identified as the cause - flooring instead of rounding "
                 "half-up - with evidence (a reproduction, a file:line, or the commit). Naming only `transfer()` or "
                 "only the symptom fails.",
    "s11.plan_in_chat": "Use the harness facts to see when code changed. PASS needs a reply before any source change "
                        "that shows the developer all three: what changes (where and how), how acceptance will be "
                        "checked (commands or named tests), and what stays out of scope - and asks for approval. If "
                        "code changed before any such reply, FAIL. Restating the ticket's criteria alone is not a "
                        "plan.",
    "s12.constraint_in_plan": "Judge the plan file. PASS needs the cents-call constraint stated as binding (a "
                              "constraint, acceptance criterion or decided rule - not an assumption to revisit), with "
                              "its reason (finance's nightly script) and its source (the developer, the chat, or "
                              "user instruction). Missing the reason or the source fails.",
    "s12.conflict_decision": "PASS needs the plan or the reply presenting it to explain that typed amounts collide "
                             "with the integer-cents form (an integer like 1250 could be read as dollars) and to put "
                             "the resolution to the developer as a decision to confirm, with a recommendation. "
                             "Silently choosing a rule - even a good one - without flagging it for confirmation "
                             "fails.",
    "s12.regression_ac": "PASS needs an acceptance criterion with a check (a command and expected result, or a named "
                         "test) showing the old cents call still behaves as before, e.g. `tl transfer alice bob 1250` "
                         "moves 1250 cents / prints `Amount: $12.50`. A constraint sentence without a check fails.",
    "s12.constraint_in_tasks": "Look at each task file. Every task that changes how `tl transfer` reads its amount "
                               "(the CLI task, or a single combined task) must contain the constraint and a regression "
                               "check for the cents form. The plan having it is not enough. A parser-only task does "
                               "not need it.",
    "s12.interfaces_pinned": "PASS when the plan or the task files name the parser's module, function name, "
                             "signature (input and return) and the error it throws. Also PASS when there is a single "
                             "task and it pins all of that itself. \"Add a parser\" without a name and signature "
                             "fails.",
    "s12.ac_checkable": "PASS when every acceptance criterion in the plan is observable (a command with its expected "
                        "output, a named test, or a diff check) and the ticket's invalid inputs \"abc\", \"-5\" and "
                        "\"12.345\" are covered. Any vague criterion (\"works correctly\") fails.",
    "s12.decisions_first": "Judge the first reply that presents the plan. PASS when it opens with the level and what "
                           "the developer must decide or confirm, before details such as file lists or task tables. "
                           "A reply that only lists what was created, with no decision for the developer, fails.",
})


def main_run_block(run_dir: Path, key: str) -> str:
    col = json.loads((run_dir / "collected.json").read_text(encoding="utf-8"))
    outputs = run_dir / "outputs"
    turns = col.get("turns", [])
    subs = [f"{n['role']} ({n['name']})" for n in col.get("tree", []) if n["depth"] >= 1]
    changed = sorted(set(col["changes"]["added"]) | set(col["changes"]["deleted"]) | set(col["changes"]["modified"]))
    facts = [f"- Files the session changed by the end: {', '.join(changed) if changed else 'none'}",
             f"- Subagents started: {', '.join(subs) if subs else 'none'}"]
    if col.get("tree"):
        facts.append(f"- Workflow skills the assistant read, in order: {', '.join(col['tree'][0]['skills_read']) or 'none'}")
    for t in turns:
        facts.append(f"- After reply {t['n']}: source/test files changed so far: "
                     f"{', '.join(t['code_changed']) if t['code_changed'] else 'none'}")
    parts = [f"Harness facts:\n\n" + "\n".join(facts) + "\n", "Conversation:\n"]
    limit = None
    if key in ("s8", "s9", "s10"):
        limit = 1
    elif key in ("s11", "s11r", "p5"):
        gate = next((t["n"] for t in turns if t["kind"] in ("approval", "review", "question") or t["code_changed"]),
                    None)
        limit = gate or (turns[0]["n"] if turns else 1)
    for t in turns:
        if limit and t["n"] > limit:
            break
        path = outputs / f"turn-{t['n']}.md"
        text = path.read_text(encoding="utf-8", errors="replace").strip() if path.exists() else "(no reply file)"
        parts.append(f"Assistant reply {t['n']}:\n\n````markdown\n{text}\n````\n")
        if t.get("reply") and not (limit and t["n"] >= limit):
            parts.append(f"Developer message {t['n'] + 1}:\n\n```text\n{t['reply']}\n```\n")
    if key == "p4":
        docs = {}
        for t in turns:
            docs.update(t.get("docs", {}))
        docs.update(col.get("docs_final", {}))
        for rel in sorted(docs):
            if re.search(r"fix-review-round-\d+\.md$", rel):
                parts.append(f"File `{rel}`:\n\n````markdown\n{docs[rel].strip()}\n````\n")
    if key == "f2":
        setup = json.loads((run_dir / "setup.json").read_text(encoding="utf-8"))
        final = col.get("docs_final", {})
        for rel in ("docs/CODE_CONVENTIONS.md", "docs/ARCHITECTURE.md", "docs/LESSONS.md", "docs/DECISIONS.md"):
            if rel in final:
                text = "\n".join(added_lines(setup["files"].get(rel, ""), final[rel])).strip()
                parts.append(f"Lines the session added to `{rel}`:\n\n````markdown\n{text or '(none)'}\n````\n")
            else:
                parts.append(f"`{rel}`: unchanged by the session.\n")
    if key == "r1":
        docs = col.get("docs_final", {})
        for rel in sorted(docs):
            if rel.startswith("docs/reviews/") or (rel.startswith("docs/tasks/feature-TL-27-refunds/")
                                                   and not rel.endswith("exploration.md")):
                parts.append(f"File `{rel}` as the session left it:\n\n````markdown\n{docs[rel].strip()}\n````\n")
    if key == "s12":
        docs = col.get("docs_final", {})
        for rel in sorted(docs):
            if rel.startswith("docs/reviews/") or (rel.startswith("docs/tasks/feature-TL-44-typed-amounts/")
                                                   and not rel.endswith("exploration.md")):
                parts.append(f"File `{rel}` as the session left it:\n\n````markdown\n{docs[rel].strip()}\n````\n")
    return "\n".join(parts)


PHASE2_GROUPS = {
    "G4": dict(intro=MAIN_INTRO, shared=None,
               scenarios=[("s8", "S8 - new user, Ritus not set up", ctx_s8),
                          ("s9", "S9 - a run in progress on the branch", ctx_s9),
                          ("s10", "S10 - a bug report through the front door", ctx_s10),
                          ("s11", "S11 - a SIMPLE ticket: the plan shown before code", ctx_s11)]),
    "G5": dict(intro=MAIN_INTRO, shared=None,
               scenarios=[("s12", "S12 - a STANDARD ticket with a constraint said only in chat", ctx_s12)]),
}


# ---------------------------------------------------------------- Phase 3

FEE15 = SCENARIOS_DIR / "fee15/common/repo/docs/tasks/feature-TL-15-fee-preview/001-fee-preview.md"


def ctx_fee15() -> str:
    return f"""\
All three scenarios review the same change on branch `feature/TL-15-fee-preview`: TL-15 adds
`tl fee <amount> <transfer|withdraw>` to the tinyledger CLI, a SIMPLE task implemented by the main thread, so no
per-task verification ran and the reviewer was told to re-run the Acceptance commands and build/test/lint itself.
The change: `src/cli.js` and `test/cli.test.js` are modified; `src/fee-preview.js` and `test/fee-preview.test.js` are
new files that are **untracked** (the user commits at the end), so no `git diff` shows them - a reviewer has to read
them from disk. `main()` builds a `Ledger` for every command, but the constructor only stores the path
(`src/ledger.js:12-14`), so `tl fee` touches no balance.

{numbered(FEE15, label='the task file')}
{numbered(LAYERS / 'fee15-clean/src/cli.js', 1, 31, 'src/cli.js (the correct version)')}
{numbered(LAYERS / 'fee15-clean/src/fee-preview.js', label='src/fee-preview.js (the correct version, untracked)')}
{numbered(BASE / 'src/fees.js', 5, 14, 'src/fees.js (unchanged)')}"""


def ctx_p1() -> str:
    return """\
The implementation is correct and complete. `fee 10.50 transfer` prints `Fee: $0.11` (exit 0), `fee 50.25 withdraw`
prints `Fee: $1.01` (exit 0), and `fee 10 foo` prints `Error: Unknown fee kind: foo` (exit 1: computeFee throws and
`main()` prints the error). USAGE lists the command (`src/cli.js:14`). The tests cover transfer, withdrawal, the
minimum fee, an invalid amount, the unknown kind, and that balances stay unchanged; build, test and lint pass.

Correct verdict: Approve. The change has no real defect."""


def ctx_p2() -> str:
    return f"""\
Same change, with one planted defect in the untracked `src/fee-preview.js` - every kind other than `withdraw` is quoted
as a transfer. `node src/cli.js fee 10 foo` prints `Fee: $0.10` and exits 0, where the task's Acceptance expects
`Error: Unknown fee kind: foo` and exit 1. The unknown-kind tests are absent, so build, test and lint all pass; only
running that acceptance command or reading the untracked file shows the defect.

{numbered(LAYERS / 'fee15-bug/src/fee-preview.js', label='src/fee-preview.js (as reviewed, untracked)')}
The only real blocking defect is this one; the missing unknown-kind test is its direct consequence."""


def ctx_p3() -> str:
    prev = (SCENARIOS_DIR / "p3/inputs.md").read_text(encoding="utf-8").split("Your previous report:", 1)[1].strip()
    return f"""\
A re-review. The committed branch had the defect from the scenario above (unknown kinds quoted as transfers), and the
reviewer's previous report asked for changes with two findings:

{prev}

The fix, uncommitted since that report, changes only `src/fee-preview.js:6` (it now passes `kind` through, as in the
correct version shown in the shared context) and adds the two unknown-kind tests (`test/fee-preview.test.js:19-21`,
`test/cli.test.js:68-70`). Nothing else changed. Both findings are fixed; the correct verdict is Approve."""


def ctx_p4() -> str:
    return f"""\
The developer asked the assistant to address the review comments on PR #12 (TL-15, `tl fee`), which was already
committed on its branch. The remote helper returned these six comments (ground truth after each):

1. mai-tran, `src/cli.js:13`: "The new `fee` command isn't in USAGE ... TL-15 asks for
   `tl fee <amount> <transfer|withdraw>` in the usage text." - **valid**: USAGE lacks the line. Fix it.
2. mai-tran, `test/fee-preview.test.js:17`: "Nothing tests the unknown-kind path (`tl fee 10 foo`) ... Please add a test
   for the error and the exit code." - **valid**: no such test exists. Add it.
3. quan-le, `src/fee-preview.js:6`: "This parses the amount with `Number()` ... Please use `parseAmount`." -
   **incorrect**: line 6 already calls `parseAmount`. Challenge it with that proof; change nothing.
4. quan-le, `src/fee-preview.js:5`: "nit: I'd call this `quoteFee`." - **subjective**: skip with a reply.
5. linh-nguyen, a conversation comment with no file or line: "could you add a `--json` flag to all the commands?" -
   **out of scope**: skip with a reply.
6. codecov[bot]: "Coverage: 94.1% (+0.4%)" - **noise**: auto-skip, no reply.

{numbered(LAYERS / 'fee15-clean/src/fee-preview.js', label='src/fee-preview.js (as committed)')}
{numbered(LAYERS / 'fee15-af/src/cli.js', 10, 13, 'src/cli.js (as committed)')}"""


def ctx_p5() -> str:
    return f"""\
The developer typed `/debug` with: "since yesterday's deploy, `tl transfer alice bob 10.50` only charges a $0.10 fee;
it should be $0.11." The cause: the latest commit, a table-driven refactor of the fee schedule, made `computeFee` floor
the fee (`src/fees.js:18`) instead of rounding half-up as decision D-002 requires. 1050 cents at 1% is 10.5 cents,
which must be charged as 11. Withdrawals go through the same function, so they are wrong too (5025 cents at 2% is
100.5, charged 100, should be 101). Fees are a payments risk area, so the workflow never sizes this below STANDARD,
and a fix that changes logic waits for the developer's approval.

{numbered(LAYERS / 'fees-floor/src/fees.js', label='src/fees.js')}"""


NOTES.update({
    "p1.acceptance_evidenced": "PASS needs every acceptance criterion - transfer fee, withdrawal fee, unknown kind, "
                               "USAGE, build/test/lint - shown as met with its own evidence: an observed command result "
                               "or a file:line. The unknown-kind criterion needs the observed output or exit code of "
                               "`fee 10 foo` (or of a CLI test the reviewer ran that checks it). Predictions fail.",
    "p1.no_false_findings": "Look at every finding presented as blocking (Critical, High, Blocking, must-fix, or a "
                            "reason for its verdict). The change has no real defect, so any such finding fails the "
                            "run. Non-blocking notes and questions don't count.",
    "p2.found_bug": "PASS needs the defect named: previewFee (src/fee-preview.js:6, or the fee-preview module) quotes "
                    "any kind other than withdraw as a transfer, with its consequence for `fee 10 foo` (a fee printed "
                    "and exit 0 instead of the error and exit 1). Flagging only a missing test fails.",
    "p2.no_false_positive": "Look at every finding presented as blocking. Each must be real per the ground truth; the "
                            "unknown-kind defect and its missing test are real. Non-blocking notes don't count.",
    "p3.old_findings_checked": "PASS needs each of the two earlier findings addressed on its own as fixed, with "
                               "evidence: the command's new output, a test run, or the file:line of the fix or the "
                               "new test. A blanket \"all fixed\" fails.",
    "p3.converges": "Look at every finding that was not in the previous report. PASS when there is none, or each is "
                    "blocking and demonstrated. A new non-blocking finding on code the fix did not change fails. Notes "
                    "clearly marked informational don't count.",
    "p4.incorrect_challenged": "PASS needs the Number() comment (quan-le, src/fee-preview.js:6) treated as incorrect "
                               "because the code already calls parseAmount, with the file:line or the quoted code as "
                               "proof. Fixing it, or skipping it without saying why its premise is false, fails.",
    "p4.skips_with_replies": "PASS needs both: the quoteFee rename skipped as subjective and the --json request skipped "
                             "as out of scope, each with a reason and a reply draft the author could post; and no reply "
                             "drafted for the codecov bot comment. A missing reply for either skip fails.",
    "p4.gate_complete": "Judge the first reply that asks for approval; the harness facts show code had not changed yet. "
                        "PASS when it lists the two planned fixes and the skipped comments with their reasons before "
                        "any change. A gate that shows only the fixes, or none of them, fails.",
    "p5.root_cause": "Judge the replies before the developer's approval. PASS needs both: computeFee's floor "
                     "(src/fees.js:18, or \"computeFee floors instead of rounding half-up\") identified as the cause, "
                     "and withdrawals named as affected by the same fault. Missing either fails.",
})

PHASE3_GROUPS = {
    "G6": dict(
        intro="The reports were written by code-review subagents following a workflow skill called `pr-review`. Each "
              "reviewed a local change before its pull request was opened, without changing any file, and wrote a "
              "verdict (Approve / Request Changes / Needs Clarification / BLOCKED) with findings.",
        shared=("Shared context for P1-P3", ctx_fee15),
        scenarios=[("p1", "P1 - a correct change whose new files are untracked", ctx_p1),
                   ("p2", "P2 - a planted defect in an untracked file", ctx_p2),
                   ("p3", "P3 - re-review after Request Changes", ctx_p3)]),
    "G7": dict(intro=MAIN_INTRO, shared=None,
               scenarios=[("p4", "P4 - six review comments on a PR", ctx_p4),
                          ("p5", "P5 - a bug in a function transfers and withdrawals share", ctx_p5)]),
}


# ---------------------------------------------------------------- Phase 4

def added_lines(before: str, after: str) -> list[str]:
    from collections import Counter
    left = Counter(line.rstrip() for line in before.replace("\r\n", "\n").splitlines())
    out = []
    for line in after.replace("\r\n", "\n").splitlines():
        if left[line.rstrip()] > 0:
            left[line.rstrip()] -= 1
        else:
            out.append(line)
    return out


F2_DIR = SCENARIOS_DIR / "f2/common/repo/docs/tasks/feature-TL-15-fee-preview"


def ctx_f1() -> str:
    return """\
The repository is tinyledger, a small Node.js (JavaScript, ESM) ledger library with a `tl` CLI. Ritus is installed but
not set up: no `docs/PROJECT_CONTEXT.md`, no profiles. What the repository shows: `package.json` names the project
`tinyledger` (Node.js ESM, scripts build/test/lint); `git remote get-url origin` is
`https://github.com/tinyledger-dev/tinyledger.git` (GitHub); the only branch is `main`; commit messages carry Jira-style
keys (`feat(TL-9): ...`, `feat(TL-14): ...`); two people committed in the last 90 days (Mai Tran, Quan Le). The team
has its own `CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md` and `docs/LESSONS.md`.

The developer typed `/setup` with no message. To the first question, whatever it was, they answered with everything
they knew: an existing codebase, three developers, one Jira site with the TL keys, PRs on GitHub against main, the team owns the workflow
config, no QA docs, every agent on the session model, and they use Claude Code. To any later question: "Use your
defaults for anything else." To a request for approval: "Looks right - go ahead and write it."

The repository cannot answer the team size, the workflow owner, the QA mode, the model routing or the AI tools, so
those are fair questions. Everything else it shows."""


def ctx_f2() -> str:
    return f"""\
Branch `feature/TL-15-fee-preview`: TL-15 adds `tl fee <amount> <transfer|withdraw>`, a STANDARD run with two tasks,
both verified. pr-review approved; the developer pasted its report (each acceptance command with its result,
`npm run build` exit 0, `npm test` all passing, `npm run lint` ok, no findings) and asked to wrap up. The change is
uncommitted: `src/cli.js` and its test are modified, `src/fee-preview.js` and its test are new, and `README.md` already
shows a `tl fee` example.

{numbered(F2_DIR / 'exploration.md', label='docs/tasks/feature-TL-15-fee-preview/exploration.md')}
Where each entry belongs: `[CODE_CONVENTIONS]` -> `docs/CODE_CONVENTIONS.md`; `[LESSONS]` -> `docs/LESSONS.md`;
`[DECISIONS]` -> `docs/DECISIONS.md`; `[ARCHITECTURE]` -> `docs/ARCHITECTURE.md`; `[DEVIATION]` -> the PR description,
not a doc; `[NONE]` -> nowhere. The team's `docs/DECISIONS.md` has D-001..D-003 and `docs/LESSONS.md` L-001..L-002,
each a `## D-00N - Title` (or `## L-00N - Title`) heading with prose.

The tasks' Docs sections: task 001 promised "`docs/ARCHITECTURE.md`: add the preview module to the module diagram, next
to `fees.js`" - **not done** when the session started (the diagram did not show the preview module). A session that
drew it in itself did wrap-up's reporting job wrongly: the gap should have been reported, not filled and then reported
as done. Task 002 promised a `tl fee` example in `README.md` - done.

Deferrals: the plan's non-goals "Fee previews for refunds - later." (no condition) and "Previews in other currencies -
revisit when TL-20 (currency accounts) ships." (has a condition), and the log's `--json` deferral (no condition).
The plan's decision 1 put `previewFee` in `src/fees.js`; it went into a new module instead (the `[DEVIATION]`).

If the assistant asked what to do about the missing update, the developer answered: "Leave the missing doc update as
a follow-up in the PR description. Anything else is your call." """


def ctx_f3() -> str:
    return f"""\
Branch `feature/TL-15-fee-preview`, about to be committed. The developer typed `/comprehension` with: "I'm about to
commit TL-15 (`tl fee`). Walk me through what I'm shipping and quiz me first." The change is uncommitted:
`src/cli.js` and `test/cli.test.js` are modified; `src/fee-preview.js` and `test/fee-preview.test.js` are new and
**untracked**, so `git diff` shows only the CLI side of the change.

{numbered(LAYERS / 'fee15-clean/src/fee-preview.js', label='src/fee-preview.js (new, untracked)')}
{numbered(LAYERS / 'fee15-clean/src/cli.js', 10, 44, 'src/cli.js (modified)')}
What the change relies on without showing it:

{numbered(BASE / 'src/fees.js', label='src/fees.js (unchanged)')}
- `computeFee` throws `Unknown fee kind: <kind>` (lines 6-8), which `main()` turns into `Error: ...` and exit 1
  (`src/cli.js:39-43`); it rounds half-up (line 12) and applies a 25-cent withdrawal minimum (lines 3, 13).

{numbered(LAYERS / 'parse-amount/src/money.js', 22, 41, 'src/money.js (unchanged)')}
- `parseAmount` refuses text that is not an amount, amounts too large, and zero, with `InvalidAmountError`.
- `main()` builds a `Ledger` for every command (`src/cli.js:40`), but the constructor only stores the path
  (`src/ledger.js:12-14`), so `tl fee` runs without a ledger file.

The developer answered the quiz questions, in order: "The second option.", "The first one.", "The third one.",
"The second one.", "The first one." - fixed positions, whatever the options were."""


def ctx_f4() -> str:
    return f"""\
The repository is tinyledger on `main`. The developer typed `/brainstorm` with: "Support keeps asking for refunds -
undoing a transfer when a customer was charged by mistake. I'm not sure how to model a refund in the ledger, or
whether the fee should come back too. Let's think it through before we plan anything."

{numbered(BASE / 'src/ledger.js', label='src/ledger.js')}
{numbered(BASE / 'src/transfer.js', label='src/transfer.js')}
Facts that matter:

- **The ledger keeps no history.** The file holds only account balances and the next receipt number (lines 16-24,
  49-54), and `#save` rewrites it whole (71-75). `transfer()` returns a receipt object (`src/transfer.js:18`) that
  nothing stores. A refund cannot look up the original transfer's amount, fee or accounts: support must supply them,
  or the ledger must start recording transfers.
- Money moves only through `ledger.apply(entries)`, all or nothing (33-57). A negative balance throws
  `InsufficientFundsError`, except for the fees account (44-47): a refund after the recipient spent the money fails,
  and returning a fee debits `fees`.
- Nothing prevents refunding the same transfer twice.
- `src/fees.js` has per-kind rates and minimums (`transfer`, `withdraw`).

The developer's answers: to the first question, "Support staff would run refunds from the CLI, a few a week, always
for a whole transfer. The customer gets the amount back; the fee comes back only when the mistake was ours, and
support decides that case by case. Finance reconciles against the ledger, so a refund must never edit or remove
what's already recorded - it has to show up as its own movement."; to later questions, "No deadline, and nothing else
I know of. Use your judgment for the rest."; when asked to choose, "Let's go with your recommendation."

Reasonable options include a reverse movement (a `tl refund` that applies the opposite entries, with the details typed
by support from the receipt), recording transfers (a journal or stored receipts) so a refund works by receipt id and
can't repeat, or a general correction entry. Any design that refers back to the original transfer needs new data."""


NOTES.update({
    "f1.shows_sources": "Judge the first reply. PASS needs the detected values - at least the project name, the "
                        "language, the git platform or base branch, and the ticket system - each with where it came "
                        "from (package.json, the origin URL, commit messages...), shown for the developer to correct "
                        "before or with the first question. A first reply that only asks questions, or states values "
                        "without their sources, fails.",
    "f1.asks_only_gaps": "Look at every question in every reply. The repository shows the project name and language "
                         "(package.json), GitHub (the origin URL), the base branch `main`, and the TL-<n> key format "
                         "(commits). Listing a detected value for confirmation is fine; asking for one of these as an "
                         "open question (\"What is the project's name?\", \"Which git platform do you use?\") fails, "
                         "even with a default offered. Questions about team size, the workflow owner, QA mode, model "
                         "routing and AI tools are fine.",
    "f2.missing_reported": "PASS needs the gap named: task 001's promised docs/ARCHITECTURE.md module-diagram update "
                           "for the preview module was not made. Saying every doc update was confirmed, or not "
                           "mentioning task 001's Docs item, fails.",
    "f2.pr_description": "PASS needs a draft a reviewer could read without this session: what changes and why (with "
                         "TL-15), how it was checked (the commands and their results), and the deviation (previewFee "
                         "in its own module instead of src/fees.js). A status report that is not a PR description, or "
                         "a draft missing any of the three, fails.",
    "f2.followups_flagged": "PASS needs refund previews and the --json output both surfaced as follow-ups with no "
                            "condition for coming back to them (flagged as such, or given a proposed condition). The "
                            "multi-currency deferral has a condition (TL-20); listing it is fine. Listing no "
                            "deferrals, or listing them without noticing which lack a condition, fails.",
    "f2.entries_self_contained": "Judge the lines the session added to the four docs (shown per run). PASS when each "
                                 "promoted entry states its fact or rule so that someone who never saw this run can "
                                 "act on it, with its file:line evidence. Run-specific shorthand (\"as found in task "
                                 "001\", \"see above\"), or an entry without any file:line, fails. Nothing added fails.",
    "f3.leans_on": "PASS needs at least two of: computeFee's unknown-kind error (and how main() turns it into Error and "
                   "exit 1), its half-up rounding or withdrawal minimum, parseAmount's refusals (zero, text that is "
                   "not an amount), and main() building a Ledger that `tl fee` never uses - each cited at file:line "
                   "(a range is fine) and correct per the source above. A brief that only restates the diff fails.",
    "f3.consequence_questions": "PASS when every question asks what happens (for an input, or if something changed) "
                                "or why this approach, so answering needs more than the diff. A question answered by "
                                "reading one changed line (\"What does USAGE now list?\") fails the run.",
    "f3.fair_options": "PASS needs every question to have 4 or 5 plausible options, none labeled recommended or "
                       "correct, and the right answer (learned from the feedback) not always at the same position. "
                       "Fewer than 4 options, or an obvious giveaway in length or wording, fails.",
    "f3.feedback": "Judge each reply that follows a developer answer. PASS when each says whether the answer was right "
                   "and, when wrong, what is true and why, in a sentence or two. Skipping the feedback on any answer "
                   "fails.",
    "f3.one_at_a_time": "PASS when each reply asks exactly one quiz question and then waits for the answer. Several "
                        "questions in one reply fails.",
    "f4.understands_first": "PASS when the first reply asks about the problem (one question; multiple choice is fine, "
                            "and so is naming the default answer to that question, e.g. \"default: B\") and every "
                            "later question comes one per reply. What fails is proposing solution approaches or a "
                            "recommended design before the developer's first answer - choices that are ways to build "
                            "refunds rather than facts about the problem - or several questions in one reply.",
    "f4.no_history_noticed": "PASS needs the run to say, before or with its options, that the ledger stores only "
                             "balances and keeps no past transfers, so the original transfer can't be looked up (new "
                             "data must be recorded, or support supplies the details). A design that assumes a "
                             "history exists (\"reverse the original entry\", \"look up the transfer by id\") without "
                             "noting that it doesn't, fails.",
    "f4.real_options": "PASS needs two or three distinct approaches, each tied to this code (Ledger.apply, the fees "
                       "account, the CLI), with effort, risk, and reversibility or how hard it is to undo. Strawmen set "
                       "up to lose, or options missing these, fail.",
    "f4.blind_spots": "PASS needs, before the developer's choice, at least two of: refunding the same transfer twice, "
                      "the recipient no longer having the money (InsufficientFundsError), the fees account paying a "
                      "fee back, or how finance reconciles the refund - each tied to the option(s) it affects. "
                      "Raising them only after the choice fails.",
    "f4.respects_constraints": "PASS when the chosen design and the brief keep all three constraints: nothing "
                               "recorded is edited or removed, the refund is its own movement, and the fee returns "
                               "only on support's decision. Violating or dropping any of them fails.",
    "f4.brief": "PASS needs a closing brief with the problem, the decision, why the other options were not chosen, the "
                "constraints, and the open questions (with who can answer them). A missing element fails; format "
                "doesn't matter.",
})

PHASE4_GROUPS = {
    "G8": dict(intro=MAIN_INTRO, shared=None,
               scenarios=[("f1", "F1 - setup in a repository that answers most questions itself", ctx_f1),
                          ("f2", "F2 - wrap-up after an approved STANDARD run", ctx_f2)]),
    "G9": dict(intro=MAIN_INTRO, shared=None,
               scenarios=[("f3", "F3 - comprehension when the core of the change is untracked", ctx_f3)]),
    "G10": dict(intro=MAIN_INTRO, shared=None,
                scenarios=[("f4", "F4 - brainstorming refunds", ctx_f4)]),
}


TL27 = SCENARIOS_DIR / "tl27impl/common/repo/docs/tasks/feature-TL-27-refunds/001-refund.md"


def ctx_tl27() -> str:
    return f"""\
Every run checked the same task on branch `feature/TL-27-refunds` of tinyledger: TL-27 task 001 adds
`refund(ledger, fromId, toId, amountCents, {{ refundFee }})`, which undoes a mistaken transfer. The change is
uncommitted. `refund()` itself is correct in every scenario below:

{numbered(TL27, label='the task file')}
{numbered(LAYERS / 'refund-impl/src/refund.js', label='src/refund.js (correct)')}
The fees account is allowed to go negative by design (`src/ledger.js:44`), so returning a fee can take it below zero.
Project facts: D-002 - every fee rounds half-up to the cent (1050 cents at 1% is 10.5, charged as 11); L-002 - fee and
money tests spell out expected cents as literals."""


def ctx_q2() -> str:
    return f"""\
The new tests pass, but three of them are hollow, and one acceptance line has no test:

{numbered(LAYERS / 'refund-tests-hollow/test/refund.test.js', label='test/refund.test.js (as checked)')}
- Lines 33-40 (AC3, all or nothing) only check that the refund rejects; they never check the balances afterwards, so a
  refund that credits alice in one `apply()` and then fails to debit bob in a second would pass.
- Lines 22-31 (AC2) check the receipt and alice's balance, with `computeFee(...)` as the expected value (against
  L-002), but not bob's balance or the fees account, so a fee taken from bob instead of the fees account would pass.
- Lines 42-53 use a fake ledger and assert only `calls.length > 0` and the id the fake returned: they test the mock.
- Nothing tests AC4's refusal of 0, negative, or fractional amounts; only the same-account refusal (lines 55-62).
- The executor's report nevertheless cites these tests for AC3, AC4, and AC5.

Measured: the suite fails against 6 of 10 behavior-breaking versions of `refund()`, and passes against these 4: a
refund that is not all or nothing, one that skips the amount check, one that takes the fee from the recipient, and one
that floors the fee. The correct verdict is FAIL for the test gaps; the implementation has no defect."""


def ctx_q4() -> str:
    return f"""\
`refund()` and its tests are correct. The executor also changed two files the task does not name (its Non-goals
exclude any change to the fee schedule):

- `src/fees.js`: the fee is now `Math.floor((amountCents * FEE_RATES_BPS[kind]) / 10000)` - the half-cent offset
  removed - with the comment "Fees round down to the cent, so a refund never returns more than was charged". Every
  transfer and withdrawal now rounds down: `computeFee(1050, 'transfer')` returns 10 instead of 11, and
  `computeFee(5025, 'withdraw')` 100 instead of 101. This breaks D-002.
- `test/fees.test.js`: the existing, committed test "fees round half-up to the cent (D-002)", which asserted 11, 10,
  and 101, was renamed "fees round to the cent" and now asserts 10, 10, and 100 - the values the new code returns.

{numbered(LAYERS / 'fees-floor-tamper/test/fees.test.js', 22, 26, 'test/fees.test.js (as changed)')}
The report lists both files ("rounding expectations updated to match"), and the suite is green. The correct verdict is
FAIL: a weakened existing test hides a regression in every fee."""


NOTES.update({
    "q2.atomicity_gap": "PASS when the report says the all-or-nothing test (test/refund.test.js:33-40) does not check "
                        "the balances after the error, or equivalently that AC3's 'no balance changes' is untested. "
                        "A general remark that tests are thin fails.",
    "q2.fee_source_gap": "PASS when the report says the fee test (lines 22-31) does not check where the fee comes from "
                         "(bob's or the fees account's balance), or that it computes its expected values with "
                         "computeFee against L-002.",
    "q2.validation_gap": "PASS when the report says no test covers refusing 0, negative, or fractional amounts (AC4), "
                         "or that the test at lines 42-53 only checks a fake ledger was called.",
    "q2.demonstrated": "PASS only when the report says the checker changed the code (for example removed the fee "
                       "entry, split the apply() call, dropped the amount check), ran the tests, and observed them "
                       "still pass, and that it restored the code. An argument from reading the tests fails. The "
                       "harness facts show whether any command touched a source file.",
    "q2.no_false_defects": "Every defect or failure the report lists must be real per the ground truth. Claiming a bug "
                           "in refund() fails the run; the fees account going negative is by design.",
    "q3.test_gaps": "PASS when at least two of these appear as findings, each with its file:line: AC3's test does not "
                    "check balances after the error (lines 33-40); AC2's test does not check the fee source (lines "
                    "22-31); AC4's amount refusal is untested, or lines 42-53 only test a mock.",
    "q3.demonstrated": "PASS only when the report says the reviewer changed the code, ran the tests, observed them still "
                       "pass, and restored the code. An argument from reading the tests fails. The harness facts show "
                       "whether any command touched a source file.",
    "q3.no_false_positive": "Look at every finding presented as blocking. refund() is correct, so any logic or "
                            "requirement finding against it fails the run; test findings for the real gaps are fine.",
    "q4.weakened_named": "PASS when the report identifies that the existing rounding test in test/fees.test.js had its "
                         "expected values changed to match the new code (11 -> 10, 101 -> 100, or 'rounding "
                         "expectations updated') and treats that as unjustified by the task. Flagging only that "
                         "src/fees.js is out of scope, without the test edit, fails.",
    "q4.regression_named": "PASS needs the rounding change named as a D-002 violation with an input and its wrong "
                           "result: computeFee(1050, 'transfer') -> 10 instead of 11, computeFee(5025, 'withdraw') -> "
                           "100 instead of 101, or a 10.50 transfer charging $0.10.",
    "q4.no_false_defects": "refund() and its tests are correct. Any defect claimed against them fails the run.",
})

TESTQ_GROUPS = {
    "G11": dict(
        worker=True,
        intro="The reports were written by verification subagents following a workflow skill called `verify-task`. "
              "Each independently checked one implemented task and wrote a verdict (`VERIFY: PASS` or `VERIFY: FAIL`) "
              "with evidence for the main thread. A FAIL sends the task back to be fixed.",
        shared=("Shared context for Q2 and Q4", ctx_tl27),
        scenarios=[("q2", "Q2 - a correct refund() with hollow tests", ctx_q2),
                   ("q4", "Q4 - an existing test changed to hide a rounding regression", ctx_q4)]),
    "G12": dict(
        worker=True,
        intro="The reports were written by code-review subagents following a workflow skill called `pr-review`. Each "
              "reviewed a local change before its pull request was opened and wrote a verdict (Approve / Request "
              "Changes / Needs Clarification / BLOCKED) with findings. No per-task verification had run.",
        shared=("Shared context", ctx_tl27),
        scenarios=[("q3", "Q3 - a correct refund() with hollow tests", ctx_q2)]),
}


def ctx_r1() -> str:
    message = (SCENARIOS_DIR / "r1/message.md").read_text(encoding="utf-8").strip()
    return f"""\
The developer typed `/ticket-review` with this ticket, on branch `feature/TL-27-refunds` of tinyledger:

```text
{message}
```

Two rules decide values in this change:

- **The refunded fee rounds half-up (D-002).** The ticket does not say so; the repo does - `docs/DECISIONS.md` D-002
  ("Every fee kind rounds half-up to the nearest cent: 1050 cents at 1% is 10.5 cents, charged as 11") and the project
  constraint in `docs/PROJECT_CONTEXT.md`. The transfer fee is 1% (`computeFee(amountCents, 'transfer')`). Rounding
  decides the cents only for amounts whose last two digits are 50 or more, e.g. 1050 -> 11 (floor would give 10) or
  1075 -> 11; a round amount like 2000 -> 20 passes under any rounding rule.
- **Refunds above $500.00 are refused (ticket AC4).** The boundary: 50000 cents ($500.00) is accepted, 50001 cents
  ($500.01) is refused. An example far from the edge (e.g. $600 refused) passes an implementation that gets the
  boundary wrong (`>=` instead of `>`).

Money movement is a payments risk area, so the level is STANDARD. The user asked for the plan and task files only."""


NOTES.update({
    "r1.rounding_ac": "Judge the plan's acceptance criteria. PASS when one pins the refunded fee's rounding with an "
                      "amount where half-up changes the cents (last two digits 50 or more, e.g. 1050 -> 11), or states "
                      "the half-up rule together with such an example. Round amounts only (2000 -> 20), or a mention "
                      "of D-002 without an example where it matters, fail.",
    "r1.cap_edge": "Judge the plan's acceptance criteria. PASS when the $500 limit is pinned on both sides of its "
                   "boundary: $500.00 (50000 cents) accepted and $500.01 (50001 cents) refused. Only one side, or an "
                   "example away from the edge (e.g. $600 refused), fails.",
    "r1.tasks_carry": "Judge the task files. PASS when their Acceptance lines carry both the rounding example (an "
                      "amount where half-up decides the cents) and the $500 boundary on both sides. Missing either, or "
                      "leaving one only under Constraints or in prose, fails.",
})

VALUE_GROUPS = {
    "G13": dict(intro=MAIN_INTRO, shared=None,
                scenarios=[("r1", "R1 - planning a refund with two value rules", ctx_r1)]),
}


def ctx_tl35() -> str:
    task = SCENARIOS_DIR / "tl35impl/common/repo/docs/tasks/feature-TL-35-balances/001-balances.md"
    return f"""\
Every run checked the same change on branch `feature/TL-35-balances` of tinyledger. The task:

{numbered(task, label='the task file (SIMPLE)')}
What was asked: `Ledger.listBalances()` returning the rows sorted by id, and a `tl balances` command printing
`<account> <amount>` lines, plus the USAGE line - about 15 lines of production code (a reference version does exactly
that). The Goal mentions that finance will eventually want CSV; nothing in the Acceptance asks for it.

What the change contains beyond that - all of it working, none of it asked for, none of it tested:

{numbered(LAYERS / 'balances-overbuilt/src/balance-formatter.js', label='src/balance-formatter.js (new file)')}
{numbered(LAYERS / 'balances-overbuilt/src/ledger.js', 33, 45, 'src/ledger.js (listBalances)')}
{numbered(LAYERS / 'balances-overbuilt/src/cli.js', 9, 31, 'src/cli.js (USAGE and commands)')}
- `listBalances({{ sortBy, limit }})`: no caller passes either option (`tl balances` calls `listBalances()` with none).
- csv and json output: reachable through `tl balances csv|json`, but no test runs them and no acceptance line asks for
  them. `BalanceFormatter` has one caller.
- The tests (`test/cli.test.js`, `test/ledger.test.js`) cover only the default text output and the default sort.

The default path is correct: `tl balances` prints the expected lines, `listBalances()` sorts by id, build, test and lint
pass. The right outcome is to send back the unrequested, untested code for removal (FAIL / Request Changes), with CSV
named as a follow-up - not to report a defect in the default path."""


NOTES.update({
    "o2.names_extras": "PASS when the report names both the csv/json output (or BalanceFormatter) and the sortBy/limit "
                       "options as code the task doesn't need, with evidence - no acceptance line, test, or caller "
                       "uses them. Naming only one of the two, or only a new file as out of scope, fails.",
    "o2.no_false_defects": "Every defect or failure the report lists must be real per the ground truth. Claiming the "
                           "default output or listBalances() is wrong fails the run.",
    "o3.names_extras": "PASS when a finding (any type) covers the unrequested csv/json output and the sortBy/limit "
                       "options - the single-use formatter may be part of it - with the evidence that nothing asks for "
                       "or tests them, and says what to remove. A passing mention outside the findings fails.",
    "o3.no_false_positive": "Look at every finding presented as blocking. Blocking the unrequested, untested code is "
                            "correct; a logic or requirement finding against the default path fails the run.",
})

LEAN_GROUPS = {
    "G14": dict(
        worker=True,
        intro="The reports were written by verification subagents following a workflow skill called `verify-task`. "
              "Each independently checked one implemented task and wrote a verdict (`VERIFY: PASS` or `VERIFY: FAIL`) "
              "with evidence for the main thread. A FAIL sends the task back to be fixed.",
        shared=("Shared context", ctx_tl35),
        scenarios=[("o2", "O2 - an implementation that builds more than the task asks", lambda: "See the shared context.")]),
    "G15": dict(
        worker=True,
        intro="The reports were written by code-review subagents following a workflow skill called `pr-review`. Each "
              "reviewed a local change before its pull request was opened and wrote a verdict (Approve / Request "
              "Changes / Needs Clarification / BLOCKED) with findings. No per-task verification had run.",
        shared=("Shared context", ctx_tl35),
        scenarios=[("o3", "O3 - an implementation that builds more than the task asks", lambda: "See the shared context.")]),
}


def ctx_verify_world() -> str:
    return f"""\
All runs checked the same feature on branch `feature/TL-27-refunds` of tinyledger: refunds of mistaken transfers,
planned either as a STANDARD change in 2 tasks (001 `refund()` with a $500 limit, 002 the `tl refund` command) or as
an EPIC in 4 tasks (001 `refund()`, 002 the $500 limit, 003 a refund receipt, 004 the command). The limit's acceptance
line in every version: "Refunds above $500.00 are refused ... exactly 50000 cents goes through, and 50001 cents is
refused and changes nothing - a test".

The correct limit check and its good test (clean worlds):

{numbered(LAYERS / 's-t1-good/src/refund.js', 4, 18, 'src/refund.js (clean)')}
{numbered(LAYERS / 's-t1-good/test/refund.test.js', 73, 84, 'test/refund.test.js, limit test (clean)')}
The planted bug (bug worlds): the comparison is `>=`, so a refund of exactly $500.00 is refused - running
`refund(ledger, 'alice', 'bob', 50000)` throws the TL-31 error. The limit test there only tries 60000 (refused) and
20000 (allowed), so the suite stays green and the report claims "50000 goes through":

{numbered(LAYERS / 's-t1-bug/src/refund.js', 16, 18, 'src/refund.js (bug)')}
{numbered(LAYERS / 's-t1-bug/test/refund.test.js', 73, 83, 'test/refund.test.js, limit test (bug)')}
Everything else in every world is correct: the refund movement, the fee from the fees account with half-up rounding
(1050 -> 11), all-or-nothing, the refusals, the command's output and errors, the refund receipt, and build, test and
lint all pass. The fees account may go negative by design (`src/ledger.js:44`)."""


def ctx_wv_clean() -> str:
    return "A clean world: the task under check is correct and its tests cover every acceptance line. The right verdict is PASS."


def ctx_wv_bug() -> str:
    return "A bug world: the task under check carries the `>=` limit bug and the hollow limit test. The right verdict is FAIL."


def ctx_wr_clean() -> str:
    return "A clean world: the whole change is correct. The right verdict is Approve."


def ctx_wr_bug() -> str:
    return "A bug world: the change carries the `>=` limit bug and the hollow limit test. The right verdict is Request Changes."


_CATCH = ("PASS when the report's FAIL or Request Changes is tied to the limit's edge: it states that exactly 50000 cents "
          "is refused, or that the acceptance's '50000 goes through' case has no test (so the claim is unproven). A "
          "blocking verdict for other reasons only, or a mention of the limit that doesn't block, fails.")
_NAMED = ("PASS only when the report states that a refund of exactly $500.00 / 50000 cents is refused - from running it "
          "(an observed error) or from reading the `>=` comparison. Only saying the edge case is untested fails.")
_NOFALSE = ("Every defect, gap, or blocking finding the report lists must be real per the ground truth. Anything else "
            "presented as a failure or a blocking finding fails the run; notes clearly marked non-blocking don't count.")
NOTES.update({
    "wv1.no_false_defects": _NOFALSE, "wv2.no_false_defects": _NOFALSE, "wv3.no_false_defects": _NOFALSE,
    "wv4.no_false_defects": _NOFALSE, "wr1.no_false_positive": _NOFALSE, "wr2.no_false_positive": _NOFALSE,
    "wr3.no_false_positive": _NOFALSE, "wr4.no_false_positive": _NOFALSE,
    "wv3.catches_cap": _CATCH, "wv4.catches_cap": _CATCH, "wr3.catches_cap": _CATCH, "wr4.catches_cap": _CATCH,
    "wv3.named_bug": _NAMED, "wv4.named_bug": _NAMED, "wr3.named_bug": _NAMED, "wr4.named_bug": _NAMED,
})

VERIFY_GROUPS = {
    "G16": dict(
        worker=True,
        intro="The reports were written by verification subagents following a workflow skill called `verify-task`. "
              "Each independently checked one implemented task and wrote a verdict (`VERIFY: PASS` or `VERIFY: FAIL`) "
              "with evidence for the main thread. A FAIL sends the task back to be fixed; a wrong FAIL costs a fix loop.",
        shared=("Shared context", ctx_verify_world),
        scenarios=[("wv1", "WV1 - STANDARD task 001, clean", ctx_wv_clean),
                   ("wv2", "WV2 - STANDARD task 002, clean", ctx_wv_clean),
                   ("wv3", "WV3 - STANDARD task 001 with the limit bug", ctx_wv_bug),
                   ("wv4", "WV4 - EPIC task 002 (the limit) with the limit bug", ctx_wv_bug)]),
    "G17": dict(
        worker=True,
        intro="The reports were written by code-review subagents following a workflow skill called `pr-review`. Each "
              "reviewed a whole local change before its pull request was opened and wrote a verdict (Approve / Request "
              "Changes / Needs Clarification / BLOCKED) with findings.",
        shared=("Shared context", ctx_verify_world),
        scenarios=[("wr1", "WR1 - STANDARD change, clean, after per-task verification", ctx_wr_clean),
                   ("wr2", "WR2 - STANDARD change, clean, no per-task verification", ctx_wr_clean),
                   ("wr3", "WR3 - STANDARD change with the limit bug, no per-task verification", ctx_wr_bug),
                   ("wr4", "WR4 - EPIC change (4 tasks) with the limit bug, no per-task verification", ctx_wr_bug)]),
}


def find_line(path: Path, needle: str) -> int:
    return next(i for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1) if needle in line)


def ctx_tl40() -> str:
    clean_refund, bug_refund = LAYERS / "l-t5/src/refund.js", LAYERS / "l-b1-full/src/refund.js"
    fee, bug_fee = find_line(clean_refund, "const feeCents"), find_line(bug_refund, "const feeCents")
    clean_list, bug_list = LAYERS / "l-t6/src/refunds.js", LAYERS / "l-b2-t6/src/refunds.js"
    return f"""\
All runs checked the same feature on branch `feature/TL-40-refunds` of tinyledger: refunds and refund history, an EPIC
of 8 tasks in one PR - 001 `refund()`, 002 the $500 limit, 003 the refund receipt, 004 `tl refund`, 005 recording every
movement in the ledger, 006 `listRefunds()`, 007 the `tl refunds` report, 008 `tl refunds --csv` - with 37 acceptance
lines. A verification run checked one task, with only the tasks up to it implemented; a review run saw all 8 (17 files,
about 520 changed lines of code and tests).

The correct code (clean worlds):

{numbered(clean_refund, 1, 2, 'src/refund.js imports (clean)')}
{numbered(clean_refund, fee, fee, 'src/refund.js, the refunded fee (clean)')}
{numbered(clean_list, 1, 10, 'src/refunds.js (clean)')}
Bug B1, the refunded fee (worlds LV1 and LR1). Task 001 computes the refunded fee with a floor instead of calling
`computeFee` (which rounds half-up, D-002), so a 1050-cent refund returns 10 cents where task 001's AC2 says 11. Task
001's own tests only try 2000 cents, where floor and half-up agree; its half-up test is missing:

{numbered(bug_refund, 1, 1, 'src/refund.js import (B1)')}
{numbered(bug_refund, bug_fee, bug_fee, 'src/refund.js, the refunded fee (B1)')}
(In LV1, where only task 001 exists, the same line is line {find_line(LAYERS / "l-b1-t1/src/refund.js", "const feeCents")}.)
In LR1 the later tasks' tests were written against the floored fee and pass: the movement test in
`test/refund.test.js` expects `feeCents: 10` for 1050, `test/cli.test.js` expects `Fee returned: $0.10`, `fee $0.10`,
`$0.10 fees` and the CSV row `...,10.50,0.10`, and `test/refunds.test.js` expects `feeCents: 10`. The fix is
`src/refund.js` plus those three test files. `test/receipt.test.js` renders a literal 11-cent fee and is right.

Bug B2, listRefunds (worlds LV2 and LR2). It only keeps refunds where the account got the money back (`fromId`), so
refunds the account paid back (`toId`) are missing, although task 006's AC1 asks for both sides and the comment above
the function says so. Its test only lists alice's refunds with alice as `fromId`:

{numbered(bug_list, 1, 10, 'src/refunds.js (B2)')}
Example: after alice gets $10.50 back from bob, `listRefunds(ledger, {{ accountId: 'bob' }})` is `[]` instead of that
refund, and `tl refunds bob` prints `No refunds for bob`. In LR2 the report and CSV tests (007-008) only use alice as
`fromId`, so they pass.

Everything else in every world is correct and matches its acceptance lines, with one exception; build, test and lint
pass. The exception, left in the fixture by accident and found by the runs, is in every world that has task 007: task
007's AC4 ("USAGE lists `tl refunds <account>` - a test in `test/cli.test.js`") and task 008's AC4 (USAGE shows
`tl refunds <account> [--csv]` - a test) ask for a test of the USAGE line, and none exists - the only USAGE assertion is
`/^Usage:/` for an unknown command, so deleting or misspelling the `tl refunds` line leaves the suite green. The USAGE
text itself is right. Under verify-task's rules a break no test catches is a FAIL, so a FAIL for this gap is correct;
under pr-review's rules a missing test for non-critical code is a Recommended `test` finding, so an Approve can stand
(noting the gap is better, but not required). A second gap of the same kind, also real and also left by accident:
task 002's AC1 names the error type (`RangeError`), but its test only matches the message (`/second approver/`), so
throwing a plain `Error` instead leaves the suite green. By design: the
fees account may go negative (`src/ledger.js`); `movements()` resolves to `[]` for a ledger file written before
movements were recorded; the `now` clock option serves tests (task 005 AC5); `listRefunds()` calls `getBalance()` to
refuse an unknown account (006 AC4); the report's "back" total sums every listed refund's amount, whichever side (007
AC2); `at.slice(0, 10)` is the UTC day because `at` is an ISO UTC string. Commands given missing arguments fail like the
existing ones do (`tl balance` with no account prints `Error: Account undefined not found`); no task asks otherwise."""


def ctx_lv1() -> str:
    return "Task 001 with bug B1; only task 001 is implemented (002-008 are `todo`). The right verdict is FAIL."


def ctx_lv2() -> str:
    return "Task 006 with bug B2; tasks 001-005 are verified, 007-008 are `todo`. The right verdict is FAIL."


def ctx_lv3() -> str:
    return ("Task 007; tasks 001-006 are verified, 008 is `todo`. The code is right; the one gap is the missing USAGE "
            "test for AC4 (see the shared context). The right verdict is FAIL, for that gap only.")


def ctx_lr1() -> str:
    return ("All 8 tasks, with bug B1 and the later tests written against it; no per-task verification ran. The right "
            "verdict is Request Changes.")


def ctx_lr2() -> str:
    return "All 8 tasks, with bug B2; no per-task verification ran. The right verdict is Request Changes."


def ctx_lr3() -> str:
    return ("All 8 tasks, no planted bug (only the accidental test gaps - the USAGE line and the RangeError type - "
            "Recommended findings); no per-task verification ran. The right verdict is Approve.")


def ctx_lr4() -> str:
    return ("All 8 tasks, no planted bug (only the accidental test gaps - the USAGE line and the RangeError type - "
            "Recommended findings); per-task verification passed all 8 and nothing changed since. The right verdict "
            "is Approve.")


_FEE_CATCH = ("PASS when the FAIL (or a blocking finding) is tied to task 001's refunded fee: it says the fee is wrong "
              "for 1050 cents (10, not 11) or isn't computeFee's half-up fee, or it blocks because AC2's 1050 -> 11 "
              "case has no test. A blocking verdict for other reasons only, or a fee remark that doesn't block, fails.")
_FEE_NAMED = ("PASS only when the report states that a 1050-cent refund returns a 10-cent fee (observed by running it) "
              "or that the fee is floored instead of rounded half-up / not computed by computeFee (read from "
              "src/refund.js). Only saying a test is missing fails.")
_LIST_CATCH = ("PASS when the FAIL (or a blocking finding) is tied to listRefunds covering one side only: it says "
               "refunds where the account is toId (the one the money came from) are missing, or it blocks because "
               "AC1's 'either side' case has no test. A blocking verdict for other reasons only, or a remark that "
               "doesn't block, fails.")
_LIST_NAMED = ("PASS only when the report states that refunds where the account is the toId side are left out - "
               "observed (bob's list empty, say) or read from the filter on memo.fromId only. Only saying a test is "
               "missing fails.")
_SPREAD = ("PASS when the report says the fee fix reaches past src/refund.js: it names at least one later test that "
           "asserts the wrong fee (test/cli.test.js, test/refunds.test.js, or the movement test in "
           "test/refund.test.js) as having to change with the fix. Only asking for a new 1050 test fails.")
_USAGE = ("PASS when the FAIL names the missing test for task 007 AC4's USAGE line: a USAGE mutation or deletion no "
          "test catches, or the absence of any assertion on the `tl refunds` USAGE text.")
NOTES.update({
    "lv3.names_usage_gap": _USAGE,
    "lv1.catches_fee": _FEE_CATCH, "lr1.catches_fee": _FEE_CATCH, "lv1.named_fee": _FEE_NAMED,
    "lr1.named_fee": _FEE_NAMED, "lr1.names_spread": _SPREAD,
    "lv2.catches_filter": _LIST_CATCH, "lr2.catches_filter": _LIST_CATCH, "lv2.named_filter": _LIST_NAMED,
    "lr2.named_filter": _LIST_NAMED,
    "lv1.no_false_defects": _NOFALSE, "lv2.no_false_defects": _NOFALSE, "lv3.no_false_defects": _NOFALSE,
    "lr1.no_false_positive": _NOFALSE, "lr2.no_false_positive": _NOFALSE, "lr3.no_false_positive": _NOFALSE,
    "lr4.no_false_positive": _NOFALSE,
})

LARGE_GROUPS = {
    "G18": dict(
        worker=True,
        intro=VERIFY_GROUPS["G16"]["intro"],
        shared=("Shared context", ctx_tl40),
        scenarios=[("lv1", "LV1 - EPIC task 001 (refund()) with bug B1", ctx_lv1),
                   ("lv2", "LV2 - EPIC task 006 (listRefunds) with bug B2", ctx_lv2),
                   ("lv3", "LV3 - EPIC task 007 (tl refunds report), code right, USAGE test missing", ctx_lv3)]),
    "G19": dict(
        worker=True,
        intro=VERIFY_GROUPS["G17"]["intro"],
        shared=("Shared context", ctx_tl40),
        scenarios=[("lr1", "LR1 - whole EPIC with bug B1, no per-task verification", ctx_lr1),
                   ("lr2", "LR2 - whole EPIC with bug B2, no per-task verification", ctx_lr2),
                   ("lr3", "LR3 - whole EPIC, no planted bug, no per-task verification", ctx_lr3),
                   ("lr4", "LR4 - whole EPIC, no planted bug, after per-task verification", ctx_lr4)]),
}


def ctx_fixcheck() -> str:
    return """\
Every run checked a fix the executor had reported DONE. Two kinds of world.

Debug (TL-21, branch `bugfix/TL-21-fee-rounding`). A refactor made `computeFee` floor fees; D-002 says fees round
half-up to the cent. The case file `docs/tasks/bugfix-TL-21-fee-rounding/investigation-fee-rounding.md` (STANDARD)
confirms the root cause at `src/fees.js:18`, lists both affected paths - transfers (`src/transfer.js:9`) and withdrawals
(`src/withdraw.js:5`, whose 25-cent minimum still applies) - proposes the fix
`Math.floor((amountCents * rule.rateBps + 5000) / 10000)` then the kind's minimum, and asks for a regression test per
path: `computeFee(1050, 'transfer')` is 11 and `computeFee(5025, 'withdraw')` is 101, both failing on the current code.
- FIX-GOOD (FV1, FR1, FR4): exactly the Proposed Fix; `test/fees.test.js` adds 1050 -> 11, 1049 -> 10, 5025 -> 101 and
  5024 -> 100. Correct.
- FIX-CEIL (FV2, FR2): `Math.ceil((amountCents * rule.rateBps) / 10000)`. 1050 -> 11 and 5025 -> 101 hold, but any fee
  with a remainder under half a cent is rounded up: 1049 -> 11 (D-002 gives 10), 5024 -> 101 (100). It is not the
  Proposed Fix. Its test covers only 1050 and 5025, so the suite is green.
- FIX-TRANSFER-ONLY (FV3, FR3): adds the 5000 offset only when the kind is 'transfer' (comment "TL-21: transfer fees
  round half-up"), so withdrawals still floor: 5025 -> 100 where it should be 101. Its test covers only the 1050
  transfer; the withdraw regression test the case file asks for is missing. The executor's report claims both.
In every debug world the new regression test fails on the old code, and build, test and lint pass.

Address-feedback (PR #7, branch `feature/TL-27-refunds`). The PR - `refund()` with the $500 limit, and
`tl refund <from> <to> <amount> [--fee]` - is committed, pushed, and was reviewed in round 1. The fix round is
uncommitted; its task file `docs/tasks/feature-TL-27-refunds/fix-review-round-1.md` keeps two comments. AC1:
`refund()` refuses the fees account on either side - `refund(ledger, 'alice', 'fees', 2000)` and
`refund(ledger, 'fees', 'bob', 2000)` throw `RangeError` `The fees account cannot be a refund party` and change nothing.
AC2: `tl refund alice bob 10.50 --fees` prints `Error: Unknown option --fees`, exits 1 and moves nothing, while `--fee`
and no option keep working.
- FIX-GOOD (AV1, AR1): both checks run before any ledger call; tests cover both sides and the unknown option, with
  balances unchanged. Correct.
- FIX-PARTIAL (AV2, AR2): `refund()` refuses only `toId === FEES_ACCOUNT`, so `refund(ledger, 'fees', 'bob', 2000)` goes
  through (bob -2000, fees +2000). Its test only tries `'alice', 'fees'`. The report claims both sides.
- FIX-AFTER-APPLY (AV3, AR3): the option check runs after `applyRefund`, so `tl refund alice bob 10.50 --fees` refunds
  $10.50 (alice 11050, bob 3950) and then prints the error with exit 1. Its test checks only the output and exit code.
  The report claims "nothing moves".
In every address-feedback world build, test and lint pass. The PR's committed code, reviewed in round 1, carries one old
gap: its limit test matches the message only, not the `RangeError` type; that code is not part of the fix round.
One more gap is real in every address-feedback world, left in the fixture by accident and found by the runs: the
command reads a single option, so a second option is ignored - `tl refund alice bob 10.50 --fee --fees` refunds with the
fee (exit 0, alice 11061) instead of rejecting `--fees`, which goes against the comment ("Reject an option you don't
know") and AC2's first sentence. A finding for it is real and may block; in FIX-GOOD it is the only gap, so there FAIL
and Request Changes are the right verdicts, for that reason only. (Other commands ignore extra arguments too; that is
old behavior outside the fix.)

Nothing else is wrong in any world."""


def ctx_fix_good() -> str:
    return "FIX-GOOD: the fix is right. The right verdict is PASS for verify-task and Approve for pr-review."


def ctx_af_good() -> str:
    return ("FIX-GOOD for both comments' named cases; the one gap is the ignored second option (`--fee --fees`, see the "
            "shared context). The right verdict is FAIL for verify-task and Request Changes for pr-review, for that gap "
            "only.")


def ctx_fix_bad() -> str:
    return "A flawed fix (see the shared context). The right verdict is FAIL for verify-task and Request Changes for pr-review."


_CEIL = ("PASS when the FAIL (or a blocking finding) is tied to the rounding: the fix rounds up rather than half-up "
         "(1049 -> 11, 5024 -> 101 or similar), or it departs from the Proposed Fix formula. A blocking verdict for other "
         "reasons only fails.")
_WD_CATCH = ("PASS when the FAIL (or a blocking finding) is tied to withdrawals: withdraw fees still round down "
             "(5025 -> 100), or the withdraw regression test the case file asks for is missing. Other reasons only fail.")
_WD_NAMED = ("PASS only when the report states that withdraw fees still round down - observed (5025 -> 100) or read "
             "from the transfer-only offset. Only saying the withdraw test is missing fails.")
_PARTIAL = ("PASS when the FAIL (or a blocking finding) is tied to the fees account still being accepted on the fromId "
            "side (`refund(ledger, 'fees', 'bob', ...)` goes through), or to AC1's second example having no test. Other "
            "reasons only fail.")
_AFTER = ("PASS when the FAIL (or a blocking finding) says an unknown option still moves money - the refund is applied "
          "before the option is rejected - against AC2's 'moves nothing'. Only saying the test is weak fails.")
_AFTER_TEST = "PASS when the report notes that the new unknown-option test checks only the output and exit code, not the balances."
_TRAILING = ("PASS when the report names that an unknown option after `--fee` is still ignored - `tl refund alice bob 10.50 "
             "--fee --fees` refunds instead of failing - observed or read from the single-option destructuring.")
NOTES.update({
    "av1.names_trailing_option": _TRAILING, "ar1.names_trailing_option": _TRAILING,
    "fv2.catches_rounding": _CEIL, "fr2.catches_rounding": _CEIL,
    "fv3.catches_withdraw": _WD_CATCH, "fr3.catches_withdraw": _WD_CATCH,
    "fv3.named_withdraw": _WD_NAMED, "fr3.named_withdraw": _WD_NAMED,
    "av2.catches_partial": _PARTIAL, "ar2.catches_partial": _PARTIAL,
    "av3.catches_after": _AFTER, "ar3.catches_after": _AFTER,
    "av3.names_test_gap": _AFTER_TEST, "ar3.names_test_gap": _AFTER_TEST,
    **{f"{k}.no_false_defects": _NOFALSE for k in ("fv1", "fv2", "fv3", "av1", "av2", "av3")},
    **{f"{k}.no_false_positive": _NOFALSE for k in ("fr1", "fr2", "fr3", "fr4", "ar1", "ar2", "ar3")},
})

FIX_GROUPS = {
    "G20": dict(
        worker=True,
        intro=VERIFY_GROUPS["G16"]["intro"],
        shared=("Shared context", ctx_fixcheck),
        scenarios=[("fv1", "FV1 - debug fix, FIX-GOOD", ctx_fix_good),
                   ("fv2", "FV2 - debug fix, FIX-CEIL", ctx_fix_bad),
                   ("fv3", "FV3 - debug fix, FIX-TRANSFER-ONLY", ctx_fix_bad),
                   ("av1", "AV1 - review fix round, FIX-GOOD (with the ignored second option)", ctx_af_good),
                   ("av2", "AV2 - review fix round, FIX-PARTIAL", ctx_fix_bad),
                   ("av3", "AV3 - review fix round, FIX-AFTER-APPLY", ctx_fix_bad)]),
    "G21": dict(
        worker=True,
        intro=VERIFY_GROUPS["G17"]["intro"],
        shared=("Shared context", ctx_fixcheck),
        scenarios=[("fr1", "FR1 - debug fix, FIX-GOOD, no per-task verification", ctx_fix_good),
                   ("fr2", "FR2 - debug fix, FIX-CEIL, no per-task verification", ctx_fix_bad),
                   ("fr3", "FR3 - debug fix, FIX-TRANSFER-ONLY, no per-task verification", ctx_fix_bad),
                   ("fr4", "FR4 - debug fix, FIX-GOOD, after verify-task passed it", ctx_fix_good),
                   ("ar1", "AR1 - re-review of a review fix round, FIX-GOOD (with the ignored second option), no "
                           "per-task verification", ctx_af_good),
                   ("ar2", "AR2 - re-review of a review fix round, FIX-PARTIAL, no per-task verification", ctx_fix_bad),
                   ("ar3", "AR3 - re-review of a review fix round, FIX-AFTER-APPLY, no per-task verification",
                    ctx_fix_bad)]),
}


def _swap(text: str, pairs) -> str:
    for old, new in pairs:
        assert old in text, old
        text = text.replace(old, new)
    return text


def ctx_verify_world_18() -> str:
    return ctx_verify_world() + """

In this bundle the clean worlds (XW1, XW2) have no test gap: their limit test pins the error type as well,
`assert.rejects(refund(ledger, 'alice', 'bob', 50001), { name: 'RangeError', message: 'Refunds above $500.00 need a
second approver (TL-31)' })`, so throwing a plain `Error` fails it. Some behavior is outside every acceptance line, by
design or left for later: the fees account may be a party to a refund (`refund(ledger, 'alice', 'fees', 2000)` goes
through, the fees account going negative - `src/ledger.js:44`); `tl refund` takes any fourth argument other than `--fee`
as no fee (`--fees` refunds without the fee) - no acceptance line asks to reject an unknown option; a command with a
missing argument fails the way the existing commands do. A report may note any of these; a FAIL or a defect for one of
them is not real."""


def ctx_tl40_18() -> str:
    return _swap(ctx_tl40(), [
        ("(worlds LV1 and LR1)", "(world XL1)"),
        ("(In LV1, where only task 001 exists,", "(In XL1, where only task 001 exists,"),
        ("In LR1 the later tasks' tests", "In the whole-EPIC world (not in this bundle) the later tasks' tests"),
        ("(worlds LV2 and LR2)", "(world XL2)"),
        ("In LR2 the report and CSV tests", "In the whole-EPIC world the report and CSV tests"),
    ])


def ctx_fixcheck_18() -> str:
    return _swap(ctx_fixcheck(), [
        ("FIX-GOOD (FV1, FR1, FR4)", "FIX-GOOD (XF1)"),
        ("FIX-CEIL (FV2, FR2)", "FIX-CEIL (XF2)"),
        ("FIX-TRANSFER-ONLY (FV3, FR3)", "FIX-TRANSFER-ONLY (not in this bundle)"),
        ("FIX-GOOD (AV1, AR1)", "FIX-GOOD (XA1)"),
        ("FIX-PARTIAL (AV2, AR2)", "FIX-PARTIAL (XA2)"),
        ("FIX-AFTER-APPLY (AV3, AR3)", "FIX-AFTER-APPLY (XA3)"),
        ("  The report claims \"nothing moves\".\n",
         "  The report claims \"nothing moves\".\n"
         "- FIX-CLEAN (XAC): as FIX-GOOD, and the command rejects every option but `--fee` wherever it comes, before any\n"
         "  ledger call: `--fees`, `--fee --fees` and `--fees --fee` all print `Error: Unknown option --fees`, exit 1, and\n"
         "  move nothing; its test covers both orders with balances unchanged. The fix round has no gap.\n"),
        ("One more gap is real in every address-feedback world,", "One more gap is real in every address-feedback world but FIX-CLEAN,"),
    ])


def ctx_af_clean() -> str:
    return ("FIX-CLEAN: both comments are fixed with no gap in the fix round. The right verdict is PASS; old behavior outside "
            "the fix (the PR's message-only limit test, other commands ignoring extra arguments) may be noted, not failed.")


_PROBED = ("PASS when the report shows the verifier ran at least one input that an acceptance line's (or the Regression "
           "Test's) own example doesn't cover - another value, the other side, another position or combination, past an "
           "edge, a second input that must be refused - and states the result it got. Re-running only the examples the "
           "task lists, the suite, build or lint, or a mutation spot check doesn't count; neither does a probe named "
           "without its result.")
_PROBE_SOURCES = {"xa1": "av1", "xa2": "av2", "xa3": "av3", "xf1": "fv1", "xf2": "fv2", "xl1": "lv1", "xl2": "lv2",
                  "xl3": "lv3", "xw1": "wv1", "xw2": "wv2"}
for _new, _old in _PROBE_SOURCES.items():
    for _id, _note in list(NOTES.items()):
        if _id.startswith(f"{_old}."):
            NOTES[_id.replace(f"{_old}.", f"{_new}.", 1)] = _note
NOTES.update({f"{k}.probed": _PROBED for k in (*_PROBE_SOURCES, "xac")})
NOTES.update({"xa2.names_trailing_option": _TRAILING, "xa3.names_trailing_option": _TRAILING,
              "xac.no_false_defects": _NOFALSE})

_VERIFY_INTRO = VERIFY_GROUPS["G16"]["intro"]
PROBE_GROUPS = {
    "G22": dict(worker=True, intro=_VERIFY_INTRO, shared=("Shared context", ctx_verify_world_18),
                scenarios=[("xw1", "XW1 - STANDARD task 001 (refund() with the limit), clean", ctx_wv_clean),
                           ("xw2", "XW2 - STANDARD task 002 (tl refund), clean", ctx_wv_clean)]),
    "G23": dict(worker=True, intro=_VERIFY_INTRO, shared=("Shared context", ctx_tl40_18),
                scenarios=[("xl1", "XL1 - EPIC task 001 (refund()) with bug B1", ctx_lv1),
                           ("xl2", "XL2 - EPIC task 006 (listRefunds) with bug B2", ctx_lv2),
                           ("xl3", "XL3 - EPIC task 007 (tl refunds report), code right, USAGE test missing", ctx_lv3)]),
    "G24": dict(worker=True, intro=_VERIFY_INTRO, shared=("Shared context", ctx_fixcheck_18),
                scenarios=[("xf1", "XF1 - debug fix, FIX-GOOD", ctx_fix_good),
                           ("xf2", "XF2 - debug fix, FIX-CEIL", ctx_fix_bad)]),
    "G25": dict(worker=True, intro=_VERIFY_INTRO, shared=("Shared context", ctx_fixcheck_18),
                scenarios=[("xa1", "XA1 - review fix round, FIX-GOOD (with the ignored second option)", ctx_af_good),
                           ("xac", "XAC - review fix round, FIX-CLEAN", ctx_af_clean)]),
    "G26": dict(worker=True, intro=_VERIFY_INTRO, shared=("Shared context", ctx_fixcheck_18),
                scenarios=[("xa2", "XA2 - review fix round, FIX-PARTIAL", ctx_fix_bad),
                           ("xa3", "XA3 - review fix round, FIX-AFTER-APPLY", ctx_fix_bad)]),
}


def ctx_verify_world_23() -> str:
    return _swap(ctx_verify_world_18(), [
        ("the clean worlds (XW1, XW2) have no test gap", "the world XS2 has no test gap"),
        ("""`tl refund` takes any fourth argument other than `--fee`
as no fee (`--fees` refunds without the fee) - no acceptance line asks to reject an unknown option; a""", "a"),
    ]) + """

The verifier's security standard (`security.md`) now lists CLI arguments and flags as input crossing a boundary, with
the check "a CLI refuses a flag it doesn't know, in any position". Task 002 adds the `tl refund` command, so the check
applies to it, and `tl refund` takes any fourth argument other than `--fee` as no fee: `tl refund alice bob 20.00
--fees` or `--bogus` refunds without the fee instead of failing. That is a real gap of task 002 under the standard: a
FAIL or a defect for it is right. The items above that stay outside every rule are still not real."""


def ctx_ws_sec() -> str:
    return ("One real gap under the security standard: the command accepts a flag it doesn't know. The right verdict is "
            "FAIL, for that gap only.")


_UNKNOWN_FLAG = ("PASS when the report names that `tl refund` accepts a flag it doesn't know - `--fees`, `--bogus` or "
                 "another unknown fourth argument refunds instead of failing - observed or read from the code, as a "
                 "FAIL or a blocking finding. A non-blocking note fails.")
NOTES.update({"xs2.names_unknown_flag": _UNKNOWN_FLAG, "xs2.probed": _PROBED, "xs2.no_false_defects": _NOFALSE})
SEC_GROUPS = {
    "G27": dict(worker=True, intro=_VERIFY_INTRO, shared=("Shared context", ctx_verify_world_23),
                scenarios=[("xs2", "XS2 - STANDARD task 002 (tl refund) under the updated security standard",
                            ctx_ws_sec)]),
}


NOTES["s11r.plan_in_chat"] = NOTES["s11.plan_in_chat"]
ROUTING_GROUPS = {
    "G28": dict(intro=MAIN_INTRO, shared=None,
                scenarios=[("s11", "S11 - a SIMPLE ticket: the plan shown before code", ctx_s11),
                           ("s11r", "S11R - the same SIMPLE ticket, in a project whose docs still carry an old "
                                    "model-routing table", ctx_s11)]),
}


ALL_GROUPS = {**GROUPS, **PHASE2_GROUPS, **PHASE3_GROUPS, **PHASE4_GROUPS, **TESTQ_GROUPS, **VALUE_GROUPS,
              **LEAN_GROUPS, **VERIFY_GROUPS, **LARGE_GROUPS, **FIX_GROUPS, **PROBE_GROUPS, **SEC_GROUPS,
              **ROUTING_GROUPS}


def round_groups(iteration: int) -> dict | None:
    """Groups for a comparison round (`build.py --round`): each round scenario is judged once, in the latest group
    that judged it. Group numbers follow the iterations, so the highest one carries the latest ground truth."""
    keys = next((spec["scenarios"] for spec in build.ROUNDS.values() if spec["iteration"] == iteration), None)
    if keys is None:
        return None
    modes = {spec["key"]: spec.get("mode") for spec in SCENARIOS.values()}
    out, taken = {}, set()
    for group in sorted(ALL_GROUPS, key=lambda g: -int(g[1:])):
        spec = ALL_GROUPS[group]
        picked = [s for s in spec["scenarios"] if s[0] in keys and s[0] not in taken]
        if not picked:
            continue
        taken.update(s[0] for s in picked)
        # Worker reports get the worker rules, even in a group that first ran in Phase 1.
        out[group] = dict(spec, scenarios=picked, worker=all(modes[s[0]] != "main" for s in picked))
    def judged(key: str) -> bool:
        meta = json.loads((SCENARIOS_DIR / key / "eval.json").read_text(encoding="utf-8"))
        return any(a["check"] != "auto" for a in meta["assertions"])

    missing = [k for k in keys if k not in taken and judged(k)]
    if missing:
        raise SystemExit(f"no judge group for round scenarios: {', '.join(missing)}")
    return dict(sorted(out.items(), key=lambda item: int(item[0][1:])))


def groups_for(iteration: int) -> dict:
    groups = round_groups(iteration)
    if groups is not None:
        return groups
    if iteration in (24, 25):
        return ROUTING_GROUPS
    if iteration == 23:
        return {"G25": PROBE_GROUPS["G25"], **SEC_GROUPS}
    if iteration == 19:
        return {g: PROBE_GROUPS[g] for g in ("G22", "G23", "G25")}
    if iteration in (20, 21):
        return {g: PROBE_GROUPS[g] for g in ("G22", "G23", "G24", "G25")}
    if iteration in (18, 22):
        return PROBE_GROUPS
    if iteration == 17:
        return FIX_GROUPS
    if iteration in (15, 16):
        return LARGE_GROUPS
    if iteration == 14:
        return VERIFY_GROUPS
    if iteration == 13:
        return LEAN_GROUPS
    if iteration == 12:
        return VALUE_GROUPS
    if iteration == 11:
        return TESTQ_GROUPS
    if 9 <= iteration < 90:
        return PHASE4_GROUPS
    if iteration >= 8:
        return PHASE3_GROUPS
    return PHASE2_GROUPS if phase(iteration) == 2 else GROUPS


def runs_by_key(iteration_dir: Path) -> dict[str, list[Path]]:
    out: dict[str, list[Path]] = {}
    for setup in sorted(iteration_dir.glob("eval-*/*/run-*/setup.json")):
        key = SCENARIOS[json.loads(setup.read_text(encoding="utf-8"))["eval"]]["key"]
        out.setdefault(key, []).append(setup.parent)
    return out


def bundle(iteration: int, only: set[str] | None = None):
    iteration_dir = WORKSPACE / f"iteration-{iteration}"
    judge_dir = iteration_dir / "judge"
    judge_dir.mkdir(exist_ok=True)
    PRIVATE.mkdir(exist_ok=True)
    rng = random.SystemRandom()
    runs = runs_by_key(iteration_dir)
    mapping: dict[str, dict] = {}
    map_path = PRIVATE / f"iteration-{iteration}-mapping.json"
    if only and map_path.exists():
        mapping = {k: v for k, v in json.loads(map_path.read_text(encoding="utf-8")).items() if v["group"] not in only}
    groups = groups_for(iteration)
    for group, spec in groups.items():
        if only and group not in only:
            continue
        rules = COMMON_RULES if phase(iteration) == 1 or spec.get("worker") else COMMON_RULES + (
            "\nIn this bundle a \"report\" is the whole run: the assistant's replies and the files it left. Judge "
            "what the developer saw and what an executor would read.\n")
        parts = [f"# Grading bundle {group}\n", spec["intro"] + "\n", rules]
        if spec["shared"]:
            title, fn = spec["shared"]
            parts.append(f"## {title}\n\n{fn()}")
        count = 0
        for key, title, fn in spec["scenarios"]:
            if not runs.get(key):
                continue
            meta = json.loads((SCENARIOS_DIR / key / "eval.json").read_text(encoding="utf-8"))
            judged = [a for a in meta["assertions"] if a["check"] != "auto"]
            parts.append(f"## Scenario {title}\n\n### Ground truth\n\n{fn()}")
            parts.append("### Assertions to grade for every run of this scenario\n\n" + "\n".join(
                f"- `{a['id']}`: \"{a['text']}\"\n  Grading notes: {NOTES[a['id']]}" for a in judged) + "\n")
            members = list(runs[key])
            rng.shuffle(members)
            used = set()
            for run_dir in members:
                while True:
                    anon = f"{key.upper()}-{''.join(rng.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(3))}"
                    if anon not in used:
                        used.add(anon)
                        break
                mapping[anon] = {"run_rel": run_dir.relative_to(iteration_dir).as_posix(), "group": group,
                                 "assertions": [a["id"] for a in judged]}
                if SCENARIOS[json.loads((run_dir / "setup.json").read_text(encoding="utf-8"))["eval"]].get("mode") == "main":
                    parts.append(f"### Run {anon}\n\n{main_run_block(run_dir, key)}")
                    count += len(judged)
                    continue
                col = json.loads((run_dir / "collected.json").read_text(encoding="utf-8"))
                report = (run_dir / "outputs" / "report.md").read_text(encoding="utf-8", errors="replace").strip()
                skill = SCENARIOS[json.loads((run_dir / "setup.json").read_text(encoding="utf-8"))["eval"]]["skill"]
                parts.append(f"### Run {anon}\n\nHarness facts:\n\n{harness_facts(col, skill)}\n\nReport:\n\n"
                             f"````markdown\n{report}\n````\n")
                count += len(judged)
        result = judge_dir / f"result-{group}.json"
        parts.append(OUTPUT_RULES.format(result=result, group=group, count=count))
        path = judge_dir / f"bundle-{group}.md"
        path.write_text("\n".join(parts), encoding="utf-8", newline="\n")
        print(f"{path}  ({count} judgments, {path.stat().st_size // 1024} KB)")
    map_path.write_text(json.dumps(mapping, indent=2), encoding="utf-8")


def merge(iteration: int):
    iteration_dir = WORKSPACE / f"iteration-{iteration}"
    mapping = json.loads((PRIVATE / f"iteration-{iteration}-mapping.json").read_text(encoding="utf-8"))
    merged: dict[str, dict] = {}
    feedback = {}
    problems = []
    for group in groups_for(iteration):
        path = iteration_dir / "judge" / f"result-{group}.json"
        if not path.exists():
            problems.append(f"missing {path.name}")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        feedback[group] = data.get("eval_feedback")
        for anon, verdicts in data["results"].items():
            if anon not in mapping:
                problems.append(f"{group}: unknown run id {anon}")
                continue
            info = mapping[anon]
            for aid in info["assertions"]:
                v = verdicts.get(aid)
                if not v or not isinstance(v.get("passed"), bool):
                    problems.append(f"{anon} ({info['run_rel']}): no verdict for {aid}")
                    continue
                merged.setdefault(info["run_rel"], {})[aid] = {"passed": v["passed"],
                                                               "evidence": f"[judge] {v.get('evidence', '')}"}
    expected = sum(len(i["assertions"]) for i in mapping.values())
    got = sum(len(v) for v in merged.values())
    (iteration_dir / "judge-results.json").write_text(json.dumps(merged, indent=2, ensure_ascii=True), encoding="utf-8")
    (iteration_dir / "judge" / "eval-feedback.json").write_text(json.dumps(feedback, indent=2, ensure_ascii=True),
                                                                encoding="utf-8")
    print(f"merged {got}/{expected} judgments")
    for p in problems:
        print("PROBLEM:", p)


def main():
    common = argparse.ArgumentParser(add_help=False)
    add_common_options(common)
    parser = argparse.ArgumentParser(parents=[common])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("bundle", "merge"):
        p = sub.add_parser(name, parents=[common])
        p.add_argument("--iteration", type=int, default=1)
        if name == "bundle":
            p.add_argument("--groups", default="", help="comma-separated groups to rebuild; the others keep their ids")
    args = parser.parse_args()
    global WORKSPACE, PRIVATE
    WORKSPACE = resolve_workspace(args.workspace)
    PRIVATE = WORKSPACE / "judge-private"
    build.configure_paths(WORKSPACE)
    if args.cmd == "bundle":
        bundle(args.iteration, set(filter(None, args.groups.split(","))) or None)
    else:
        merge(args.iteration)


if __name__ == "__main__":
    main()
