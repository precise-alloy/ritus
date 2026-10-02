"""Write the iteration 17 layers and scenarios: checking a fix - verify-task against pr-review - in the debug flow
(TL-21 fee rounding case file) and the address-feedback flow (review round 1 on the TL-27 refunds PR). Re-runnable.

Debug worlds (branch bugfix/TL-21-fee-rounding on FULL_HISTORY, where C5 made computeFee floor):
  d-fix-good           half-up restored in computeFee; regression test for both kinds and the x.49 edge
  d-fix-ceil           Math.ceil: 1050 -> 11 and 5025 -> 101 pass, but 1049 -> 11 over-charges (not the Proposed Fix)
  d-fix-transfer-only  half-up for transfer only; withdraw still floors (5025 -> 100); only a transfer test
Address-feedback worlds (PR #7 = TL-27 STANDARD refunds, committed and pushed; the fix round is uncommitted):
  a-fix-good           fees account refused on both sides; unknown option rejected before any ledger call
  a-fix-partial        fees account refused as toId only (fromId side untested)
  a-fix-after-apply    unknown option rejected after the refund was applied: money moves, exit 1; test checks output only
"""
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURE = HERE.parent / "fixture"
LAYERS = FIXTURE / "layers"
SCEN = FIXTURE / "scenarios"


def read(rel: str) -> str:
    return (FIXTURE / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


def sub(text: str, old: str, new: str) -> str:
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new)


LAYER_FILES: dict[str, dict[str, str]] = {}


def put(layer: str, rel: str, text: str) -> None:
    LAYER_FILES.setdefault(layer, {})[rel] = text


# ---------------------------------------------------------------- debug: TL-21 fee rounding
FEES_FLOOR = read("layers/fees-floor/src/fees.js")
FLOOR_LINE = "  return Math.max(Math.floor((amountCents * rule.rateBps) / 10000), rule.minCents);"
FEES_TEST = read("base/test/fees.test.js")

put("d-fix-good", "src/fees.js",
    sub(FEES_FLOOR, FLOOR_LINE, "  return Math.max(Math.floor((amountCents * rule.rateBps + 5000) / 10000), rule.minCents);"))
put("d-fix-good", "test/fees.test.js", FEES_TEST + r"""
test('fees round half-up to the cent (D-002, TL-21)', () => {
  assert.equal(computeFee(1050, 'transfer'), 11);
  assert.equal(computeFee(1049, 'transfer'), 10);
  assert.equal(computeFee(5025, 'withdraw'), 101);
  assert.equal(computeFee(5024, 'withdraw'), 100);
});
""")

put("d-fix-ceil", "src/fees.js",
    sub(FEES_FLOOR, FLOOR_LINE, "  return Math.max(Math.ceil((amountCents * rule.rateBps) / 10000), rule.minCents);"))
put("d-fix-ceil", "test/fees.test.js", FEES_TEST + r"""
test('a half-cent fee rounds up to the next cent (TL-21)', () => {
  assert.equal(computeFee(1050, 'transfer'), 11);
  assert.equal(computeFee(5025, 'withdraw'), 101);
});
""")

put("d-fix-transfer-only", "src/fees.js", sub(FEES_FLOOR, FLOOR_LINE, """\
  // TL-21: transfer fees round half-up (D-002).
  const offset = kind === 'transfer' ? 5000 : 0;
  return Math.max(Math.floor((amountCents * rule.rateBps + offset) / 10000), rule.minCents);"""))
put("d-fix-transfer-only", "test/fees.test.js", FEES_TEST + r"""
test('a 1050-cent transfer charges an 11-cent fee (TL-21)', () => {
  assert.equal(computeFee(1050, 'transfer'), 11);
});
""")

# ---------------------------------------------------------------- address-feedback: PR #7 docs, committed with the PR
for rel in ("docs/reviews/TL-27-review.md", "docs/tasks/feature-TL-27-refunds/001-refund.md",
            "docs/tasks/feature-TL-27-refunds/002-refund-command.md", "docs/tasks/feature-TL-27-refunds/exploration.md"):
    text = read(f"scenarios/wr1/common/repo/{rel}")
    text = text.replace("{{ts:1:10:05}}", "2026-09-24 10:05").replace("{{ago:90}}", "2026-09-24 09:40")
    put("a-pr-docs", rel, text)

REFUND = read("layers/s-t1-good/src/refund.js")
REFUND_TEST = read("layers/s-t1-good/test/refund.test.js")
CLI = read("layers/s-t2/src/cli.js")
CLI_TEST = read("layers/s-t2/test/cli.test.js")
SAME_ACCOUNT = """  if (fromId === toId) {
    throw new RangeError('Cannot refund to the same account');
  }
"""
PARTY = "The fees account cannot be a refund party"
REFUND_BOTH = sub(REFUND, SAME_ACCOUNT, SAME_ACCOUNT + f"""  if (fromId === FEES_ACCOUNT || toId === FEES_ACCOUNT) {{
    throw new RangeError('{PARTY}');
  }}
""")
REFUND_TO_ONLY = sub(REFUND, SAME_ACCOUNT, SAME_ACCOUNT + f"""  if (toId === FEES_ACCOUNT) {{
    throw new RangeError('{PARTY}');
  }}
""")
PARTY_TEST_BOTH = f"""
test('the fees account cannot be a refund party', async () => {{
  const {{ ledger, cleanup }} = await tempLedger();
  try {{
    const refused = {{ name: 'RangeError', message: '{PARTY}' }};
    await assert.rejects(refund(ledger, 'alice', FEES_ACCOUNT, 2000), refused);
    await assert.rejects(refund(ledger, FEES_ACCOUNT, 'bob', 2000), refused);
    assert.equal(await ledger.getBalance('alice'), 10000);
    assert.equal(await ledger.getBalance('bob'), 5000);
    assert.equal(await ledger.getBalance(FEES_ACCOUNT), 0);
  }} finally {{
    await cleanup();
  }}
}});
"""
PARTY_TEST_TO_ONLY = f"""
test('the fees account cannot be a refund party', async () => {{
  const {{ ledger, cleanup }} = await tempLedger();
  try {{
    const refused = {{ name: 'RangeError', message: '{PARTY}' }};
    await assert.rejects(refund(ledger, 'alice', FEES_ACCOUNT, 2000), refused);
    assert.equal(await ledger.getBalance('alice'), 10000);
    assert.equal(await ledger.getBalance(FEES_ACCOUNT), 0);
  }} finally {{
    await cleanup();
  }}
}});
"""
CLI_REFUND = """  async refund(ledger, [fromId, toId, amount, flag]) {
    const receipt = await applyRefund(ledger, fromId, toId, parseAmount(amount), { refundFee: flag === '--fee' });
"""
CLI_CHECK_FIRST = sub(CLI, CLI_REFUND, """  async refund(ledger, [fromId, toId, amount, option]) {
    if (option !== undefined && option !== '--fee') {
      throw new RangeError(`Unknown option ${option}`);
    }
    const receipt = await applyRefund(ledger, fromId, toId, parseAmount(amount), { refundFee: option === '--fee' });
""")
CLI_CHECK_AFTER = sub(CLI, CLI_REFUND, """  async refund(ledger, [fromId, toId, amount, option]) {
    const receipt = await applyRefund(ledger, fromId, toId, parseAmount(amount), { refundFee: option === '--fee' });
    if (option !== undefined && option !== '--fee') {
      throw new RangeError(`Unknown option ${option}`);
    }
""")
OPTION_TEST_FULL = """
test('refund rejects an option it does not know and moves nothing', async () => {
  const { ledger, path, cleanup } = await tempLedger();
  try {
    assert.deepEqual(await main(['refund', 'alice', 'bob', '10.50', '--fees'], { ledgerPath: path }), {
      code: 1,
      output: 'Error: Unknown option --fees',
    });
    assert.equal(await ledger.getBalance('alice'), 10000);
    assert.equal(await ledger.getBalance('bob'), 5000);
  } finally {
    await cleanup();
  }
});
"""
OPTION_TEST_OUTPUT_ONLY = """
test('refund rejects an option it does not know', async () => {
  const { path, cleanup } = await tempLedger();
  try {
    assert.deepEqual(await main(['refund', 'alice', 'bob', '10.50', '--fees'], { ledgerPath: path }), {
      code: 1,
      output: 'Error: Unknown option --fees',
    });
  } finally {
    await cleanup();
  }
});
"""
put("a-fix-good", "src/refund.js", REFUND_BOTH)
put("a-fix-good", "test/refund.test.js", REFUND_TEST + PARTY_TEST_BOTH)
put("a-fix-good", "src/cli.js", CLI_CHECK_FIRST)
put("a-fix-good", "test/cli.test.js", CLI_TEST + OPTION_TEST_FULL)
put("a-fix-partial", "src/refund.js", REFUND_TO_ONLY)
put("a-fix-partial", "test/refund.test.js", REFUND_TEST + PARTY_TEST_TO_ONLY)
put("a-fix-partial", "src/cli.js", CLI_CHECK_FIRST)
put("a-fix-partial", "test/cli.test.js", CLI_TEST + OPTION_TEST_FULL)
put("a-fix-after-apply", "src/refund.js", REFUND_BOTH)
put("a-fix-after-apply", "test/refund.test.js", REFUND_TEST + PARTY_TEST_BOTH)
put("a-fix-after-apply", "src/cli.js", CLI_CHECK_AFTER)
put("a-fix-after-apply", "test/cli.test.js", CLI_TEST + OPTION_TEST_OUTPUT_ONLY)


# ---------------------------------------------------------------- scenario docs
CASE_DIR = "docs/tasks/bugfix-TL-21-fee-rounding"
CASE_FILE = f"""# Investigation: fees round down instead of half-up

Level: STANDARD - Date: {{{{date:1}}}} - Ticket: TL-21
Status: implemented

## Symptom

`tl transfer alice bob 10.50` charges a $0.10 fee. D-002 says fees round half-up to the cent, so 10.5 cents is 11, and
finance reconciles against that rule at month end.

## Root cause

Grade: Confirmed

`computeFee` floors the fee (`src/fees.js:18`: `Math.floor((amountCents * rule.rateBps) / 10000)`). The table-driven
refactor ("refactor(fees): table-driven fee schedule") dropped the `+ 5000` that made it round half-up.

## Evidence

- `computeFee(1050, 'transfer')` -> 10 - Confirmed - `node -e "import('./src/fees.js').then((m) => console.log(m.computeFee(1050, 'transfer')))"`
- `computeFee(5025, 'withdraw')` -> 100, where D-002 gives 101 - Confirmed - the same command for withdraw
- The refactor's diff removes `+ 5000` from the fee formula - Confirmed - `git log -p -- src/fees.js`
- The existing fee tests use amounts whose fee is a whole number of cents, so they pass either way - Deduced

## Affected paths

- Transfers - `src/transfer.js:9` - the sender is charged the floored fee (the ticket's case)
- Withdrawals - `src/withdraw.js:5` - the floored 2% fee; the 25-cent minimum still applies on top

## Proposed Fix

Round half-up once, in `computeFee`, as before the refactor: `Math.floor((amountCents * rule.rateBps + 5000) / 10000)`,
then the kind's minimum. Both paths go through it, so neither caller changes.

## Regression Test

- `test/fees.test.js`: `computeFee(1050, 'transfer')` is 11 and `computeFee(5025, 'withdraw')` is 101 - one per affected
  path; both fail on the current code - `npm test -- test/fees.test.js`
"""
CASE_EXPLORATION = """# Exploration log - bugfix-TL-21-fee-rounding

## {{ago:40}} - debug

- [LESSONS] A refactor that moves a formula into a table can drop a rounding term; the fee tests used whole-cent fees
  and could not see it
"""
FIX_TASK_DIR = "docs/tasks/feature-TL-27-refunds"
FIX_TASK = f"""# Fix: review round 1 on PR #7

Level: STANDARD - Depends on: none - Plan: docs/reviews/TL-27-review.md
Status: implemented

## Goal

Address the two comments kept from round 1 of the review of PR #7 (TL-27 refunds):

- `src/refund.js:9` @mai.tran: "The fees account may go negative by design, so `refund(ledger, 'alice', 'fees', 2000)`
  pays alice money the fees account never had. A refund shouldn't have the fees account on either side."
- `src/cli.js:28` @quan.le: "`tl refund alice bob 10.50 --fees` quietly refunds without the fee. Reject an option you
  don't know instead of guessing."

## Acceptance

- [ ] [AC1] `refund()` refuses the fees account on either side: `refund(ledger, 'alice', 'fees', 2000)` and
  `refund(ledger, 'fees', 'bob', 2000)` both throw `RangeError` `{PARTY}` and change nothing - a test
  in `test/refund.test.js`
- [ ] [AC2] `tl refund` rejects an option it doesn't know: `tl refund alice bob 10.50 --fees` prints
  `Error: Unknown option --fees`, exits 1, and moves nothing; `--fee` and no option keep working - a test in
  `test/cli.test.js`
- [ ] [AC3] `npm run build` -> exit 0; `npm test` -> 0 failures; `npm run lint` -> `lint ok`

## Starting points

- `src/refund.js:9-18` - `refund()`'s checks, all before its one `ledger.apply()` call
- `src/cli.js:28-32` - the `refund` command
"""

CHECKS_LINE = "npm run build -> build ok; npm test -> {{TESTS_PASS}} passed, 0 failed; npm run lint -> lint ok"


def span(rel: str, title: str) -> str:
    lines = (LAYERS / rel).read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines, 1) if line.startswith(f"test('{title}'"))
    end = next(i for i, line in enumerate(lines, 1) if i > start and line == "});")
    return f"{start}-{end}"


def first(rel: str, title: str) -> int:
    return int(span(rel, title).split("-")[0])


def line_of(rel: str, needle: str) -> int:
    lines = (LAYERS / rel).read_text(encoding="utf-8").splitlines()
    return next(i for i, line in enumerate(lines, 1) if needle in line)


def report(acceptance, files, added, also="none") -> str:
    return "\n".join(["Status: DONE", "Acceptance:", *acceptance, "Files changed:", *files, "Tests added:", *added,
                      "Tests changed: none", "Deviations: none", f"Also affects: {also}", "Docs updated: none",
                      "Follow-ups: none"])


def verify_inputs(task_path: str, text: str) -> str:
    return (f"Task file: `{task_path}` (paths are relative to the project repository)\n"
            "Read-only apart from build/test/lint and the spot check it undoes (`testing.md`); never fixes.\n\n"
            f"Executor's report:\n\n```text\n{text}\n```\n")


def debug_report(layer: str, title: str, fix_line: str, what: str, test_note: str) -> str:
    t = f"{layer}/test/fees.test.js"
    fees_line = line_of(f"{layer}/src/fees.js", "return Math.max")
    return report(
        [f"- Regression Test: computeFee(1050, 'transfer') -> 11 and computeFee(5025, 'withdraw') -> 101 - "
         f"test/fees.test.js:{span(t, title)}; npm test -- test/fees.test.js failed on the old src/fees.js",
         f"- Proposed Fix: {fix_line} - src/fees.js:{fees_line}",
         f"- {CHECKS_LINE}"],
        [f"- src/fees.js - {what}", "- test/fees.test.js - the TL-21 regression test"],
        [f"- test/fees.test.js:{first(t, title)} - {test_note}"],
        also="transfer and withdraw fees (both affected paths)")


DEBUG_REVIEW = """Review mode: local pre-PR review of branch `bugfix/TL-21-fee-rounding` - the whole worktree against `origin/main`.
The change is uncommitted: the user commits at the end of the run.
Requirement source: the case file `docs/tasks/bugfix-TL-21-fee-rounding/investigation-fee-rounding.md` - its Regression
Test is the acceptance and its Proposed Fix the approved decision. Its Symptom carries the ticket, so don't fetch TL-21.
"""
AF_REVIEW = """Review mode: re-review of PR #7 (branch `feature/TL-27-refunds`, pushed to `origin`) after review round 1. The PR's
commits were reviewed in round 1; the fix round is the uncommitted worktree change, not pushed yet.
Requirement source: the fix task `docs/tasks/feature-TL-27-refunds/fix-review-round-1.md` - its Goal quotes the two
review comments kept - with the plan `docs/reviews/TL-27-review.md` and the task files next to it. Don't fetch the PR or
TL-27. There is no earlier pr-review report: the round-1 findings are those two comments.
"""
UNVERIFIED = "No per-task verification ran: re-run the Acceptance commands and build, test, and lint yourself.\n"
VERIFIED = "Per-task verification ran: verify-task passed the fix on this tree, and nothing has changed since.\n"
NEVER = "Never fix anything.\n"


def build_scenarios() -> dict:
    # Reads the layers for line numbers, so it runs after they are written.
    FV1 = debug_report("d-fix-good", "fees round half-up to the cent (D-002, TL-21)",
                       "computeFee rounds half-up once again (+ 5000 before the division)",
                       "computeFee rounds half-up again", "fails if a half-cent fee is floored, or a .49 fee rounded up")
    FV2 = debug_report("d-fix-ceil", "a half-cent fee rounds up to the next cent (TL-21)",
                       "computeFee rounds the half cent up instead of dropping it",
                       "computeFee rounds a fractional fee up", "fails if a half-cent fee is rounded down")
    FV3 = debug_report("d-fix-transfer-only", "a 1050-cent transfer charges an 11-cent fee (TL-21)",
                       "computeFee adds the half-up offset before the division",
                       "computeFee rounds half-up", "fails if the 1050-cent transfer fee is rounded down")


    def af_report(layer: str, party_title: str, option_title: str) -> str:
        rt, ct = f"{layer}/test/refund.test.js", f"{layer}/test/cli.test.js"
        party = line_of(f"{layer}/src/refund.js", "FEES_ACCOUNT) {")
        option = line_of(f"{layer}/src/cli.js", "option !== undefined")
        plain = first(ct, "refund prints what went back to the sender")
        return report(
            [f"- [AC1] fees account refused on either side with RangeError, nothing changes - src/refund.js:{party}; "
             f"test/refund.test.js:{span(rt, party_title)}",
             f"- [AC2] unknown option -> Error: Unknown option --fees, exit 1, nothing moves; --fee and no option still "
             f"work - src/cli.js:{option}; test/cli.test.js:{span(ct, option_title)}, :{plain}",
             f"- [AC3] {CHECKS_LINE}"],
            ["- src/refund.js - refuse the fees account as a refund party", "- src/cli.js - reject unknown refund options",
             "- test/refund.test.js - fees-party test", "- test/cli.test.js - unknown-option test"],
            [f"- test/refund.test.js:{first(rt, party_title)} - fails if the fees account may be a refund party",
             f"- test/cli.test.js:{first(ct, option_title)} - fails if an unknown option is accepted"])


    AV1 = af_report("a-fix-good", "the fees account cannot be a refund party",
                    "refund rejects an option it does not know and moves nothing")
    AV2 = af_report("a-fix-partial", "the fees account cannot be a refund party",
                    "refund rejects an option it does not know and moves nothing")
    AV3 = af_report("a-fix-after-apply", "the fees account cannot be a refund party", "refund rejects an option it does not know")


    A = lambda i, check, text: {"id": i, "check": check, "text": text}  # noqa: E731
    RO = "Leaves the working tree exactly as it found it"
    NOFALSE_V = "Every other defect it reports is real"
    NOFALSE_R = "No blocking finding that isn't real"
    RAN = "Ran build, test and lint itself"
    NORERUN = ("Doesn't re-run build and test: verification passed on this tree and nothing changed since "
               "(pr-review step 2)")
    ROUND = ("Blocks on the rounding: the fix rounds up (Math.ceil) instead of half-up - a fee with a remainder under half a "
             "cent is over-charged (1049 -> 11 where D-002 gives 10), or the fix departs from the Proposed Fix formula")
    WD_CATCH = ("Blocks because withdrawals still round down: computeFee(5025, 'withdraw') is 100 not 101, or the withdraw "
                "regression test the case file asks for is missing")
    WD_NAMED = "States that a withdraw fee still floors (5025 -> 100, observed or read from the transfer-only offset)"
    PARTIAL = ("Blocks because the fees account is still accepted as the other party: refund(ledger, 'fees', 'bob', 2000) "
               "goes through, or AC1's second case has no test")
    AFTER = ("Blocks because an unknown option still moves money: `tl refund alice bob 10.50 --fees` refunds before it "
             "errors (the check runs after the refund), against AC2's 'moves nothing'")
    AFTER_TEST = "Notes that the new option test checks only the output, not that nothing moved"
    TRAILING = ("Names that an unknown option after `--fee` is still ignored: `tl refund alice bob 10.50 --fee --fees` "
                "refunds with the fee instead of failing, against the comment and AC2")

    DEBUG_BASE = dict(main="FULL_HISTORY", branch="bugfix/TL-21-fee-rounding")
    SCENARIOS = {
        "fv1": dict(layer="d-fix-good", docs="debug", inputs=verify_inputs(f"{CASE_DIR}/investigation-fee-rounding.md", FV1),
                    prompt="verify-task on a debug fix (TL-21, STANDARD): half-up restored in computeFee, regression test "
                           "for both kinds and the .49 edge. Correct.",
                    expected="VERIFY: PASS.",
                    assertions=[A("fv1.pass", "auto", "Returns VERIFY: PASS"), A("fv1.read_only", "auto", RO),
                                A("fv1.no_false_defects", "judge", "No defect it reports is invented: the fix is right")]),
        "fv2": dict(layer="d-fix-ceil", docs="debug", inputs=verify_inputs(f"{CASE_DIR}/investigation-fee-rounding.md", FV2),
                    prompt="verify-task on a debug fix (TL-21): Math.ceil passes 1050 -> 11 and 5025 -> 101 but "
                           "over-charges 1049 -> 11; not the Proposed Fix.",
                    expected="VERIFY: FAIL tied to the rounding.",
                    assertions=[A("fv2.fail", "auto", "Returns VERIFY: FAIL"), A("fv2.read_only", "auto", RO),
                                A("fv2.catches_rounding", "judge", ROUND), A("fv2.no_false_defects", "judge", NOFALSE_V)]),
        "fv3": dict(layer="d-fix-transfer-only", docs="debug",
                    inputs=verify_inputs(f"{CASE_DIR}/investigation-fee-rounding.md", FV3),
                    prompt="verify-task on a debug fix (TL-21): half-up for transfer only; withdraw still floors "
                           "(5025 -> 100); only a transfer test, though the case file lists both paths.",
                    expected="VERIFY: FAIL tied to withdraw.",
                    assertions=[A("fv3.fail", "auto", "Returns VERIFY: FAIL"), A("fv3.read_only", "auto", RO),
                                A("fv3.catches_withdraw", "judge", WD_CATCH), A("fv3.named_withdraw", "judge", WD_NAMED),
                                A("fv3.no_false_defects", "judge", NOFALSE_V)]),
        "fr1": dict(layer="d-fix-good", docs="debug", inputs=DEBUG_REVIEW + UNVERIFIED + NEVER,
                    prompt="pr-review of a debug fix (TL-21), no per-task verification. Correct fix.",
                    expected="Approve.",
                    assertions=[A("fr1.approve", "auto", "Returns Approve"), A("fr1.read_only", "auto", RO),
                                A("fr1.ran_checks", "auto", RAN), A("fr1.no_false_positive", "judge", NOFALSE_R)]),
        "fr2": dict(layer="d-fix-ceil", docs="debug", inputs=DEBUG_REVIEW + UNVERIFIED + NEVER,
                    prompt="pr-review of a debug fix (TL-21), no per-task verification: Math.ceil instead of half-up.",
                    expected="Request Changes tied to the rounding.",
                    assertions=[A("fr2.request_changes", "auto", "Returns Request Changes"), A("fr2.read_only", "auto", RO),
                                A("fr2.ran_checks", "auto", RAN), A("fr2.catches_rounding", "judge", ROUND),
                                A("fr2.no_false_positive", "judge", NOFALSE_R)]),
        "fr3": dict(layer="d-fix-transfer-only", docs="debug", inputs=DEBUG_REVIEW + UNVERIFIED + NEVER,
                    prompt="pr-review of a debug fix (TL-21), no per-task verification: transfer-only half-up.",
                    expected="Request Changes tied to withdraw.",
                    assertions=[A("fr3.request_changes", "auto", "Returns Request Changes"), A("fr3.read_only", "auto", RO),
                                A("fr3.ran_checks", "auto", RAN), A("fr3.catches_withdraw", "judge", WD_CATCH),
                                A("fr3.named_withdraw", "judge", WD_NAMED), A("fr3.no_false_positive", "judge", NOFALSE_R)]),
        "fr4": dict(layer="d-fix-good", docs="debug", inputs=DEBUG_REVIEW + VERIFIED + NEVER,
                    prompt="pr-review of a debug fix (TL-21) after verify-task passed it. Correct fix.",
                    expected="Approve without re-running build and test.",
                    assertions=[A("fr4.approve", "auto", "Returns Approve"), A("fr4.read_only", "auto", RO),
                                A("fr4.no_rerun", "auto", NORERUN), A("fr4.no_false_positive", "judge", NOFALSE_R)]),
        "av1": dict(layer="a-fix-good", docs="af", inputs=verify_inputs(f"{FIX_TASK_DIR}/fix-review-round-1.md", AV1),
                    prompt="verify-task on a review fix round (PR #7, 2 comments): both comments' named cases fixed, with "
                           "tests - but a second option after `--fee` (`--fee --fees`) is still ignored and the refund goes "
                           "through (a gap left in the fixture by accident; the runs found it, so the expected verdict was "
                           "corrected from PASS to FAIL before grading).",
                    expected="VERIFY: FAIL for the trailing unknown option only.",
                    assertions=[A("av1.fail", "auto", "Returns VERIFY: FAIL (a trailing unknown option is still ignored)"),
                                A("av1.read_only", "auto", RO),
                                A("av1.names_trailing_option", "judge", TRAILING),
                                A("av1.no_false_defects", "judge", NOFALSE_V)]),
        "av2": dict(layer="a-fix-partial", docs="af", inputs=verify_inputs(f"{FIX_TASK_DIR}/fix-review-round-1.md", AV2),
                    prompt="verify-task on a review fix round: the fees account is refused as toId only; the fromId side "
                           "has no check and no test.",
                    expected="VERIFY: FAIL tied to the fromId side.",
                    assertions=[A("av2.fail", "auto", "Returns VERIFY: FAIL"), A("av2.read_only", "auto", RO),
                                A("av2.catches_partial", "judge", PARTIAL), A("av2.no_false_defects", "judge", NOFALSE_V)]),
        "av3": dict(layer="a-fix-after-apply", docs="af", inputs=verify_inputs(f"{FIX_TASK_DIR}/fix-review-round-1.md", AV3),
                    prompt="verify-task on a review fix round: the unknown-option check runs after the refund, so "
                           "`--fees` moves money and then exits 1; the test checks the output only.",
                    expected="VERIFY: FAIL tied to money moving.",
                    assertions=[A("av3.fail", "auto", "Returns VERIFY: FAIL"), A("av3.read_only", "auto", RO),
                                A("av3.catches_after", "judge", AFTER), A("av3.names_test_gap", "judge", AFTER_TEST),
                                A("av3.no_false_defects", "judge", NOFALSE_V)]),
        "ar1": dict(layer="a-fix-good", docs="af", inputs=AF_REVIEW + UNVERIFIED + NEVER,
                    prompt="pr-review re-review of a review fix round, no per-task verification. The comments' named cases are "
                           "fixed, but `--fee --fees` still refunds (the accidental gap; expected verdict corrected from "
                           "Approve to Request Changes before grading).",
                    expected="Request Changes for the trailing unknown option only.",
                    assertions=[A("ar1.request_changes", "auto", "Returns Request Changes"), A("ar1.read_only", "auto", RO),
                                A("ar1.ran_checks", "auto", RAN), A("ar1.names_trailing_option", "judge", TRAILING),
                                A("ar1.no_false_positive", "judge", NOFALSE_R)]),
        "ar2": dict(layer="a-fix-partial", docs="af", inputs=AF_REVIEW + UNVERIFIED + NEVER,
                    prompt="pr-review re-review, no per-task verification: fees refused as toId only.",
                    expected="Request Changes tied to the fromId side.",
                    assertions=[A("ar2.request_changes", "auto", "Returns Request Changes"), A("ar2.read_only", "auto", RO),
                                A("ar2.ran_checks", "auto", RAN), A("ar2.catches_partial", "judge", PARTIAL),
                                A("ar2.no_false_positive", "judge", NOFALSE_R)]),
        "ar3": dict(layer="a-fix-after-apply", docs="af", inputs=AF_REVIEW + UNVERIFIED + NEVER,
                    prompt="pr-review re-review, no per-task verification: unknown option rejected after the refund moved "
                           "money.",
                    expected="Request Changes tied to money moving.",
                    assertions=[A("ar3.request_changes", "auto", "Returns Request Changes"), A("ar3.read_only", "auto", RO),
                                A("ar3.ran_checks", "auto", RAN), A("ar3.catches_after", "judge", AFTER),
                                A("ar3.names_test_gap", "judge", AFTER_TEST), A("ar3.no_false_positive", "judge", NOFALSE_R)]),
    }
    return SCENARIOS


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    for layer, files in LAYER_FILES.items():
        root = LAYERS / layer
        if root.exists():
            shutil.rmtree(root)
        for rel, text in files.items():
            write(root / rel, text)
        print(f"{layer}: {', '.join(sorted(files))}")
    scenarios = build_scenarios()
    for key, spec in scenarios.items():
        root = SCEN / key
        if root.exists():
            shutil.rmtree(root)
        repo = root / "common" / "repo"
        if spec["docs"] == "debug":
            write(repo / CASE_DIR / "investigation-fee-rounding.md", CASE_FILE)
            write(repo / CASE_DIR / "exploration.md", CASE_EXPLORATION)
        else:
            write(repo / FIX_TASK_DIR / "fix-review-round-1.md", FIX_TASK)
        write(root / "inputs.md", spec["inputs"])
        write(root / "eval.json", json.dumps({"prompt": spec["prompt"], "expected_output": spec["expected"],
                                              "assertions": spec["assertions"]}, indent=2, ensure_ascii=False) + "\n")
    print("scenarios:", ", ".join(scenarios))


if __name__ == "__main__":
    main()
