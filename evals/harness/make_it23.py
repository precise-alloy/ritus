"""Write the iteration 23 scenario: the STANDARD task 002 world (`tl refund`) under the updated security standard,
where CLI arguments and flags are boundary input and a CLI refuses a flag it doesn't know, in any position. The world is
the xw2 one; only the ground truth changes: accepting `--fees` / `--bogus` is now a real gap. Run make_it18.py first.
"""
import json
import shutil
from pathlib import Path

import make_it18 as m18

HERE = Path(__file__).resolve().parent
FIXTURE = HERE.parent / "fixture"
SCEN = FIXTURE / "scenarios"

UNKNOWN_FLAG = ("Names that `tl refund` accepts a flag it doesn't know - `--fees`, `--bogus` or another unknown fourth "
                "argument refunds (without the fee) instead of failing - against the security standard's check that a "
                "CLI refuses a flag it doesn't know")


def main() -> None:
    dest = SCEN / "xs2"
    if dest.exists():
        shutil.rmtree(dest)
    m18.write(dest / "inputs.md", (SCEN / "xw2" / "inputs.md").read_text(encoding="utf-8").replace("\r\n", "\n"))
    m18.write(dest / "eval.json", json.dumps({
        "prompt": "verify-task, STANDARD task 002 (`tl refund`), with task 001 already verified, under the updated "
                  "security standard: CLI arguments and flags are boundary input, and the command accepts an unknown "
                  "flag.",
        "expected_output": "VERIFY: FAIL naming the unknown flag the command accepts; nothing else failed.",
        "assertions": [{"id": "xs2.fail", "check": "auto", "text": "Returns VERIFY: FAIL"},
                       {"id": "xs2.read_only", "check": "auto", "text": "Leaves the working tree exactly as it found it"},
                       {"id": "xs2.names_unknown_flag", "check": "judge", "text": UNKNOWN_FLAG},
                       {"id": "xs2.probed", "check": "judge", "text": m18.PROBED},
                       {"id": "xs2.no_false_defects", "check": "judge",
                        "text": "Reports no other defect or gap: every other acceptance line is met"}]},
        indent=2, ensure_ascii=False) + "\n")
    print("scenario xs2")


if __name__ == "__main__":
    main()
