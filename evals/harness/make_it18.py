"""Write the iteration 18 scenarios: verify-task before and after the probe rules (probe each rule past its example,
read it from the quoted source, note behavior no rule covers). Reuses the worlds of iterations 14, 15 and 17 under new
keys, and adds one address-feedback world whose fix round is fully clean. Re-runnable; run make_it17.py first.
"""
import json
import shutil
from pathlib import Path

import make_it17 as m17

HERE = Path(__file__).resolve().parent
FIXTURE = HERE.parent / "fixture"
LAYERS = FIXTURE / "layers"
SCEN = FIXTURE / "scenarios"

# ---------------------------------------------------------------- the clean fix round: every option but --fee refused
CLI_REST = m17.sub(m17.CLI, m17.CLI_REFUND, """  async refund(ledger, [fromId, toId, amount, ...options]) {
    const unknown = options.find((option) => option !== '--fee');
    if (unknown !== undefined) {
      throw new RangeError(`Unknown option ${unknown}`);
    }
    const refundFee = options.includes('--fee');
    const receipt = await applyRefund(ledger, fromId, toId, parseAmount(amount), { refundFee });
""")
OPTION_TEST_CLEAN = """
test('refund rejects an option it does not know, wherever it comes, and moves nothing', async () => {
  const { ledger, path, cleanup } = await tempLedger();
  try {
    const refused = { code: 1, output: 'Error: Unknown option --fees' };
    assert.deepEqual(await main(['refund', 'alice', 'bob', '10.50', '--fees'], { ledgerPath: path }), refused);
    assert.deepEqual(await main(['refund', 'alice', 'bob', '10.50', '--fee', '--fees'], { ledgerPath: path }), refused);
    assert.equal(await ledger.getBalance('alice'), 10000);
    assert.equal(await ledger.getBalance('bob'), 5000);
  } finally {
    await cleanup();
  }
});
"""
CLEAN_FILES = {"src/refund.js": m17.REFUND_BOTH, "test/refund.test.js": m17.REFUND_TEST + m17.PARTY_TEST_BOTH,
               "src/cli.js": CLI_REST, "test/cli.test.js": m17.CLI_TEST + OPTION_TEST_CLEAN}
# The STANDARD refund() world with its one test gap closed: the limit test pins the error type AC5 names, on the same
# line, so the line numbers in the wv1/wv2 reports still hold.
LIMIT_LOOSE = "await assert.rejects(refund(ledger, 'alice', 'bob', 50001), /second approver/);"
LIMIT_TIGHT = ("await assert.rejects(refund(ledger, 'alice', 'bob', 50001), "
               "{ name: 'RangeError', message: 'Refunds above $500.00 need a second approver (TL-31)' });")
STD_CLEAN_FILES = {"src/refund.js": m17.read("layers/s-t1-good/src/refund.js"),
                   "test/refund.test.js": m17.sub(m17.read("layers/s-t1-good/test/refund.test.js"), LIMIT_LOOSE,
                                                  LIMIT_TIGHT)}
PARTY_TITLE = "the fees account cannot be a refund party"
OPTION_TITLE = "refund rejects an option it does not know, wherever it comes, and moves nothing"


def clean_report() -> str:
    layer = "a-fix-clean"
    rt, ct = f"{layer}/test/refund.test.js", f"{layer}/test/cli.test.js"
    party = m17.line_of(f"{layer}/src/refund.js", "FEES_ACCOUNT) {")
    option = m17.line_of(f"{layer}/src/cli.js", "unknown !== undefined")
    plain = m17.first(ct, "refund prints what went back to the sender")
    return m17.report(
        [f"- [AC1] fees account refused on either side with RangeError, nothing changes - src/refund.js:{party}; "
         f"test/refund.test.js:{m17.span(rt, PARTY_TITLE)}",
         f"- [AC2] any option but --fee -> Error: Unknown option <option>, exit 1, nothing moves, wherever it comes; "
         f"--fee and no option still work - src/cli.js:{option}; test/cli.test.js:{m17.span(ct, OPTION_TITLE)}, :{plain}",
         f"- [AC3] {m17.CHECKS_LINE}"],
        ["- src/refund.js - refuse the fees account as a refund party", "- src/cli.js - reject unknown refund options",
         "- test/refund.test.js - fees-party test", "- test/cli.test.js - unknown-option test"],
        [f"- test/refund.test.js:{m17.first(rt, PARTY_TITLE)} - fails if the fees account may be a refund party",
         f"- test/cli.test.js:{m17.first(ct, OPTION_TITLE)} - fails if an unknown option is accepted, first or later"])


# ---------------------------------------------------------------- scenarios
PROBED = ("Checks at least one acceptance rule with an input its example doesn't cover - another value, the other side, "
          "another position, past the edge, a second refused input - and runs it, with its result")
TRAILING = ("Names that an unknown option after `--fee` is still ignored: `tl refund alice bob 10.50 --fee --fees` "
            "refunds with the fee instead of failing, against the comment and AC2")
# new key -> (source key, extra assertions)
KEYS = {
    "xa1": ("av1", []),
    "xa2": ("av2", [("names_trailing_option", TRAILING)]),
    "xa3": ("av3", [("names_trailing_option", TRAILING)]),
    "xf1": ("fv1", []),
    "xf2": ("fv2", []),
    "xl1": ("lv1", []),
    "xl2": ("lv2", []),
    "xl3": ("lv3", []),
    "xw1": ("wv1", []),
    "xw2": ("wv2", []),
}


def renamed(meta: dict, source: str, key: str, extra) -> dict:
    assertions = []
    for a in meta["assertions"]:
        a = dict(a)
        a["id"] = a["id"].replace(f"{source}.", f"{key}.", 1)
        assertions.append(a)
    tail = [a for a in assertions if a["id"].endswith(".no_false_defects")]
    body = [a for a in assertions if not a["id"].endswith(".no_false_defects")]
    body += [{"id": f"{key}.{name}", "check": "judge", "text": text} for name, text in extra]
    body.append({"id": f"{key}.probed", "check": "judge", "text": PROBED})
    return {"prompt": meta["prompt"], "expected_output": meta.get("expected_output", ""), "assertions": body + tail}


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    root = LAYERS / "a-fix-clean"
    if root.exists():
        shutil.rmtree(root)
    for rel, text in CLEAN_FILES.items():
        write(root / rel, text)
    std = LAYERS / "s-t1-clean"
    if std.exists():
        shutil.rmtree(std)
    for rel, text in STD_CLEAN_FILES.items():
        write(std / rel, text)
    for key, (source, extra) in KEYS.items():
        dest = SCEN / key
        if dest.exists():
            shutil.rmtree(dest)
        meta = json.loads((SCEN / source / "eval.json").read_text(encoding="utf-8"))
        write(dest / "inputs.md", (SCEN / source / "inputs.md").read_text(encoding="utf-8").replace("\r\n", "\n"))
        write(dest / "eval.json", json.dumps(renamed(meta, source, key, extra), indent=2, ensure_ascii=False) + "\n")
    dest = SCEN / "xac"
    if dest.exists():
        shutil.rmtree(dest)
    write(dest / "inputs.md", m17.verify_inputs(f"{m17.FIX_TASK_DIR}/fix-review-round-1.md", clean_report()))
    write(dest / "eval.json", json.dumps({
        "prompt": "verify-task on a review fix round (PR #7, 2 comments), fully clean: the fees account is refused on "
                  "both sides, and every option but --fee is rejected before any ledger call, wherever it comes.",
        "expected_output": "VERIFY: PASS; behavior outside the fix round may be noted, not failed.",
        "assertions": [{"id": "xac.pass", "check": "auto", "text": "Returns VERIFY: PASS"},
                       {"id": "xac.read_only", "check": "auto", "text": "Leaves the working tree exactly as it found it"},
                       {"id": "xac.probed", "check": "judge", "text": PROBED},
                       {"id": "xac.no_false_defects", "check": "judge",
                        "text": "No defect or FAIL for anything but a real gap in the fix round; notes are fine"}]},
        indent=2, ensure_ascii=False) + "\n")
    print("layers a-fix-clean, s-t1-clean; scenarios:", ", ".join([*KEYS, "xac"]))


if __name__ == "__main__":
    main()
