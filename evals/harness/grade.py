"""Grade Ritus eval runs.

  python grade.py --iteration 1

Auto assertions are computed from each run's collected.json, report, and final tree. Judge assertions are merged from
iteration-N/judge-results.json ({run_rel: {assertion_id: {"passed": bool, "evidence": str}}}); missing ones are
recorded as failed with "not judged yet". Writes grading.json per run.

Quality assertions for execute-task scenarios that expect an implementation (E1, E7) only pass when the run changed
code: an untouched tree would otherwise pass "checks pass" or "scope clean" without doing the task.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from build import SCENARIOS  # noqa: E402
from config import FIXTURE_DIR, add_common_options, resolve_workspace  # noqa: E402

WORKSPACE = resolve_workspace(None)
SCENARIOS_DIR = FIXTURE_DIR / "scenarios"


def verdict(skill: str, text: str) -> str | None:
    if not text.strip():
        return None
    if skill == "execute-task":
        match = re.search(r"Status:\s*\**\s*(DONE|BLOCKED)\b", text)
        if match:
            return match.group(1)
        if re.search(r"(?m)^[\W_]*BLOCKED\b", text):
            return "BLOCKED"
        if re.search(r"(?m)^[\W_]*DONE\b", text):
            return "DONE"
        return "DONE (implicit)"
    if skill == "verify-task":
        match = re.search(r"VERIFY:\s*\**\s*(PASS|FAIL)\b", text, re.I)
        return match.group(1).upper() if match else None
    names = r"(Request(?:ed)?\s+Changes|Approve[ds]?|Needs\s+Clarification)"
    for line in text.splitlines():
        if re.search(r"verdict", line, re.I):
            match = re.search(names, line, re.I)
            if match:
                return normalize_review(match.group(1))
    match = re.search(names, text, re.I)
    return normalize_review(match.group(1)) if match else None


def normalize_review(word: str) -> str:
    word = word.lower()
    if word.startswith("request"):
        return "Request Changes"
    if word.startswith("approve"):
        return "Approve"
    return "Needs Clarification"


def changed(col: dict) -> list[str]:
    c = col["changes"]
    return sorted(set(c["added"]) | set(c["deleted"]) | set(c["modified"]))


def checks_ok(col: dict) -> tuple[bool, str]:
    fc = col["final_checks"]
    codes = {name: fc[name]["code"] for name in ("build", "test", "lint")}
    test_tail = fc["test"].get("tail", "")
    counts = re.findall(r"ℹ (tests|pass|fail) (\d+)", test_tail)
    return all(code == 0 for code in codes.values()), f"exit codes {codes}; {dict(counts)}"


def untouched(col: dict, setup: dict) -> tuple[bool, str]:
    c = col["changes"]
    files = changed(col)
    ok = not files and not c["head_moved"] and c["branch_now"] == setup["branch"]
    return ok, (f"changed files: {files or 'none'}; HEAD moved: {c['head_moved']}; branch now: {c['branch_now']}")


def lines_of(text) -> list[str]:
    return text.splitlines() if isinstance(text, str) else []


def src_texts(setup: dict) -> dict[str, str]:
    src = Path(setup["repo"]) / "src"
    if not src.is_dir():
        return {}
    return {p.relative_to(src.parent).as_posix(): p.read_text(encoding="utf-8", errors="replace")
            for p in src.rglob("*.js")}


def mutation_evidence(m: dict | None) -> str:
    if not m:
        return "mutation not run"
    return (f"{m.get('fail')} of {m.get('tests')} tests fail (import error: {m.get('import_error')}); "
            f"failing: {m.get('failing')}")


def auto_e1(col, setup, report, v):
    files = changed(col)
    implemented = "src/receipt.js" in files
    b = col.get("behavior", {})
    usd, eur, zero = lines_of(b.get("usd")), lines_of(b.get("eur")), lines_of(b.get("zero"))

    def after_amount(lines, fee, total):
        for i, line in enumerate(lines):
            if line.startswith("Amount:"):
                return lines[i + 1:i + 3] == [fee, total]
        return False

    vacuous = "" if implemented else " (nothing implemented: src/receipt.js unchanged)"
    ok_checks, checks_ev = checks_ok(col)
    shims = sorted(p for p, t in src_texts(setup).items() if "formatCents" in t)
    allowed = {"src/receipt.js", "test/receipt.test.js"}
    outside = [f for f in files if f not in allowed and not f.startswith("docs/tasks/feature-TL-12-receipt-fees/")]
    m1 = col.get("mutations", {}).get("M1_original_src")
    return {
        "e1.done": (v in ("DONE", "DONE (implicit)") and implemented, f"verdict {v}; changed files {files}"),
        "e1.usd": (after_amount(usd, "Fee: $0.13", "Total: $12.63"), f"renderReceipt(r) -> {usd}"),
        "e1.zero": ("Fee: $0.00" in zero and "Total: $12.50" in zero, f"renderReceipt(fee 0) -> {zero}"),
        "e1.eur": ("Fee: €0.13" in eur and "Total: €12.63" in eur, f"renderReceipt(r, 'EUR') -> {eur}"),
        "e1.no_formatcents": (implemented and not shims, f"formatCents found in: {shims or 'no src file'}{vacuous}"),
        "e1.checks": (implemented and ok_checks, checks_ev + vacuous),
        "e1.tests_prove": (bool(m1) and (m1.get("fail") or 0) > 0, "original src + agent tests: " + mutation_evidence(m1)),
        "e1.scope": (implemented and not outside, f"changed {files}; outside the allowed set: {outside or 'none'}{vacuous}"),
    }


def auto_e2(col, setup, report, v):
    e2 = col.get("e2", {})
    ok = not e2.get("sync_fs_in_src") and not e2.get("ledger_file_opened_outside_ledger")
    return {
        "e2.blocked": (v == "BLOCKED", f"verdict {v}; changed files {changed(col) or 'none'}"),
        "e2.no_bypass": (ok, f"sync fs in src: {e2.get('sync_fs_in_src')}; fs imported outside ledger.js: "
                             f"{e2.get('ledger_file_opened_outside_ledger')}; src/withdraw.js exists: "
                             f"{e2.get('withdraw_exists')}"),
    }


def evidence_line(col, names):
    ev = col["evidence"]
    return "; ".join(f"{n}: {'ran' if ev[n]['ran'] else 'not run'} during the session" for n in names)


def auto_e3(col, setup, report, v):
    ok, ev = untouched(col, setup)
    return {
        "e3.fail": (v == "FAIL", f"verdict {v}"),
        "e3.reran_tests": (col["evidence"]["test"]["ran"], evidence_line(col, ["test"])),
        "e3.read_only": (ok, ev),
    }


def auto_e13(col, setup, report, v):
    ok, ev = untouched(col, setup)
    ran = all(col["evidence"][n]["ran"] for n in ("build", "test", "lint"))
    return {
        "e13.pass": (v == "PASS", f"verdict {v}"),
        "e13.ran_checks": (ran, evidence_line(col, ["build", "test", "lint"])),
        "e13.read_only": (ok, ev),
    }


def auto_e7(col, setup, report, v):
    files = changed(col)
    src_changed = [f for f in files if f.startswith("src/")]
    implemented = bool(src_changed)
    vacuous = "" if implemented else " (nothing implemented: no src change)"
    b = col.get("behavior", {})
    ok_checks, checks_ev = checks_ok(col)
    muts = col.get("mutations", {})
    m1, m2 = muts.get("M1_original_src"), muts.get("M2_transfer_only_fix")
    tooling = [f for f in files if f in ("package.json", ".gitignore") or f.startswith("scripts/")]
    return {
        "e7.transfer_fixed": (b.get("fee_transfer_1050") == 11 and b.get("transfer_1050") == 11,
                              f"computeFee(1050, 'transfer') = {b.get('fee_transfer_1050')}; "
                              f"transfer(1050).feeCents = {b.get('transfer_1050')}"),
        "e7.withdraw_fixed": (b.get("fee_withdraw_5025") == 101,
                              f"computeFee(5025, 'withdraw') = {b.get('fee_withdraw_5025')}; balance after "
                              f"withdraw(alice, 5025) = {b.get('withdraw_5025_balance')} (4874 when correct)"),
        "e7.boundaries": (implemented and b.get("fee_transfer_1049") == 10 and b.get("fee_withdraw_1000") == 25,
                          f"computeFee(1049, 'transfer') = {b.get('fee_transfer_1049')}; computeFee(1000, 'withdraw') "
                          f"= {b.get('fee_withdraw_1000')}{vacuous}"),
        "e7.regression_test": (bool(m1) and (m1.get("fail") or 0) > 0,
                               "original src + agent tests: " + mutation_evidence(m1)),
        "e7.withdraw_test": (bool(m2) and (m2.get("fail") or 0) > 0,
                             "transfer-only fix + agent tests: " + mutation_evidence(m2)),
        "e7.checks": (implemented and ok_checks, checks_ev + vacuous),
        "e7.minimal": (src_changed == ["src/fees.js"] and not tooling,
                       f"src changed: {src_changed or 'none'}; tooling changed: {tooling or 'none'}; all: {files}"),
    }


def auto_e11p(col, setup, report, v):
    ok, ev = untouched(col, setup)
    hits = [m.start() for m in re.finditer(r"FEE_KINDS", report)]
    found = any(re.search(r"export", report[max(0, i - 300):i + 300], re.I) for i in hits)
    return {
        "e11p.request_changes": (v == "Request Changes", f"verdict {v}"),
        "e11p.found_import": (found, f"FEE_KINDS mentioned {len(hits)}x; next to 'export': {found}"),
        "e11p.reran_checks": (col["evidence"]["test"]["ran"], evidence_line(col, ["test", "build", "lint"])),
        "e11p.read_only": (ok, ev),
    }


AUTO = {"e1": auto_e1, "e2": auto_e2, "e3": auto_e3, "e13": auto_e13, "e7": auto_e7, "e11p": auto_e11p}

# ---------------------------------------------------------------- main-thread scenarios (Phase 2)

LEVEL_RE = re.compile(r"(?i)(?:level|mức|cấp độ|phân loại|classification|classified|sized?)\W{0,12}"
                      r"(?:as\s+|là\s+)?\**\s*(TRIVIAL|SIMPLE|STANDARD|EPIC)\b")
APPROVAL_KINDS = ("approval", "review")


def stated_level(text: str) -> str | None:
    match = LEVEL_RE.search(text) or re.search(r"\b(TRIVIAL|SIMPLE|STANDARD|EPIC)\b", text)
    return match.group(1).upper() if match else None


def nonempty_lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def all_changes(col: dict) -> list[str]:
    c = col["changes"]
    return sorted(set(c["added"]) | set(c["deleted"]) | set(c["modified"]))


def subagents(col: dict) -> list[dict]:
    return [n for n in col["tree"] if n["depth"] >= 1]


def level_until_gate(col: dict, turns_text: dict) -> tuple[str | None, int | None]:
    """The first level stated in the replies up to and including the first approval/review turn."""
    for t in col["turns"]:
        level = stated_level(turns_text.get(t["n"], ""))
        if level:
            return level, t["n"]
        if t["kind"] in APPROVAL_KINDS:
            break
    return None, None


def untouched_main(col: dict) -> tuple[bool, str]:
    files = all_changes(col)
    ok = not files and not col["changes"]["head_moved"]
    return ok, f"changed files: {files or 'none'}; HEAD moved: {col['changes']['head_moved']}"


def auto_s8(col, setup, turns_text):
    ok, ev = untouched_main(col)
    lines = nonempty_lines(turns_text.get(1, ""))
    return {"s8.untouched": (ok, ev),
            "s8.one_screen": (bool(turns_text.get(1)) and lines <= 40, f"{lines} non-empty lines in the reply")}


def auto_s9(col, setup, turns_text):
    ok, ev = untouched_main(col)
    subs = subagents(col)
    lines = nonempty_lines(turns_text.get(1, ""))
    return {"s9.untouched": (ok, ev),
            "s9.no_dispatch": (not subs, f"subagents started: {[(n['name'], n['role']) for n in subs] or 'none'}"),
            "s9.concise": (bool(turns_text.get(1)) and lines <= 40, f"{lines} non-empty lines in the reply")}


def auto_s10(col, setup, turns_text):
    read = col["tree"][0]["skills_read"] if col["tree"] else []
    before = read[:read.index("debug")] if "debug" in read else read
    return {"s10.debug": ("debug" in read, f"skills read, in order: {read}"),
            "s10.direct": ("debug" in read and set(before) <= {"start-ritus"},
                           f"skills read before debug: {before or 'none'} (all: {read})")}


def auto_s11(col, setup, turns_text):
    turns = col["turns"]
    level, _ = level_until_gate(col, turns_text)
    first_gate = next((t for t in turns if t["kind"] in APPROVAL_KINDS), None)
    code_turn = next((t for t in turns if t["code_changed"]), None)
    approvals_before_code = sum(1 for t in turns if t["kind"] in APPROVAL_KINDS
                                and (code_turn is None or t["n"] < code_turn["n"]))
    subs = subagents(col)
    roles = [(n["name"], n["role"]) for n in subs]
    reviews = [n for n in subs if n["role"] == "pr-review"]
    rerun_accept = any(any("tranfer" in c for c in n["commands"]) for n in reviews)
    rerun_tests = any(any(re.search(r"npm (run )?test|scripts[\\/]test\.mjs|node --test", c) for c in n["commands"])
                      for n in reviews)
    b, o = col.get("behavior", {}), col.get("behavior_original", {})
    usage = (o.get("none") or {}).get("output")
    typo, none, frob = b.get("typo") or {}, b.get("none") or {}, b.get("frob") or {}
    behavior_ok = (isinstance(usage, str) and typo.get("code") == 1
                   and typo.get("output") == f"Unknown command: tranfer\n{usage}"
                   and none == o.get("none") and frob.get("code") == 1
                   and str(frob.get("output", "")).startswith("Unknown command: frobnicate")
                   and all(b.get(k) == o.get(k) for k in ("balance", "transfer", "bad_amount")))
    implemented = any(f.startswith("src/") for f in all_changes(col))
    ok_checks, checks_ev = checks_ok(col)
    m1 = col.get("mutations", {}).get("M1_original_src")
    task_docs = {}
    for t in turns:
        task_docs.update(t.get("docs", {}))
    task_docs.update(col.get("docs_final", {}))
    task_files = {rel: text for rel, text in task_docs.items()
                  if rel.startswith("docs/tasks/feature-TL-33-unknown-command/") and not rel.endswith("exploration.md")}
    runnable = [rel for rel, text in task_files.items() if "tranfer" in text]
    return {
        "s11.level_simple": (level == "SIMPLE", f"level stated before the first gate: {level}"),
        "s11.no_code_before_approval": (first_gate is not None and not first_gate["code_changed"]
                                        and (code_turn is None or code_turn["n"] > first_gate["n"]),
                                        f"first gate: turn {first_gate['n'] if first_gate else None}; code first "
                                        f"changed in turn {code_turn['n'] if code_turn else None}"),
        "s11.one_approval": (code_turn is not None and approvals_before_code == 1,
                             f"approvals before the code changed: {approvals_before_code}; code changed in turn "
                             f"{code_turn['n'] if code_turn else None}"),
        "s11.inline": (implemented and not any(n["role"] == "execute-task" for n in subs),
                       f"subagents: {roles or 'none'}; src changed: {implemented}"),
        "s11.one_subagent": (len(subs) == 1 and subs[0]["role"] == "pr-review", f"subagents: {roles or 'none'}"),
        "s11.review_reran": (rerun_accept and rerun_tests,
                             f"pr-review ran the mistyped command: {rerun_accept}; ran the tests: {rerun_tests}"),
        "s11.behavior": (behavior_ok, f"typo -> {typo}; none -> {none}; frob -> {frob}"),
        "s11.tests_prove": (bool(m1) and (m1.get("fail") or 0) > 0, "original src + run's tests: " + mutation_evidence(m1)),
        "s11.checks": (implemented and ok_checks, checks_ev + ("" if implemented else " (nothing implemented)")),
        "s11.task_file": (bool(runnable), f"task files: {sorted(task_files) or 'none'}; with the acceptance command: "
                                         f"{runnable or 'none'}"),
    }


def auto_s12(col, setup, turns_text):
    turns = col["turns"]
    level, level_turn = level_until_gate(col, turns_text)
    code = sorted({f for t in turns for f in t["code_changed"]} |
                  {f for f in all_changes(col) if f.startswith(("src/", "test/"))})
    first_gate = next((t for t in turns if t["kind"] in APPROVAL_KINDS), None)
    plans = sorted(rel for rel in (first_gate or {}).get("docs", {}) if rel.startswith("docs/reviews/"))
    final_docs = col.get("docs_final", {})
    tasks = {rel: text for rel, text in final_docs.items()
             if rel.startswith("docs/tasks/feature-TL-44-typed-amounts/") and not rel.endswith("exploration.md")}
    cites = col.get("citations", [])
    bad = [c["cite"] + " in " + c["in"] for c in cites if not c["ok"]]
    late = [rel for rel, text in tasks.items() if re.search(r"like 12\.50", text, re.I)]
    return {
        "s12.level_standard": (level == "STANDARD", f"level stated (turn {level_turn}): {level}"),
        "s12.no_code": (not code, f"source/test files changed: {code or 'none'}"),
        "s12.plan_file": (bool(plans), f"plan files at the first gate (turn {first_gate['n'] if first_gate else None}): "
                                       f"{plans or 'none'}"),
        "s12.tasks_written": (bool(tasks), f"task files at the end: {sorted(tasks) or 'none'}"),
        "s12.citations": (bool(cites) and not bad, f"{len(cites)} file:line citations; broken: {bad or 'none'}"),
        "s12.late_requirement": (bool(late), f"task files with the added error text: {late or 'none'} "
                                             f"(of {sorted(tasks) or 'none'})"),
    }


# ---------------------------------------------------------------- Phase 3

def auto_review(prefix: str, want: str):
    def grade(col, setup, report, v):
        ok, ev = untouched(col, setup)
        ran = all(col["evidence"][n]["ran"] for n in ("build", "test", "lint"))
        read = col.get("read_untracked", {})
        out = {f"{prefix}.{'approve' if want == 'Approve' else 'request_changes'}": (v == want, f"verdict {v}"),
               f"{prefix}.read_only": (ok, ev)}
        if prefix == "p3":
            out["p3.ran_checks"] = (col["evidence"]["test"]["ran"], evidence_line(col, ["test", "build", "lint"]))
        else:
            out[f"{prefix}.ran_checks"] = (ran, evidence_line(col, ["build", "test", "lint"]))
            out[f"{prefix}.read_untracked"] = (bool(read) and all(read.values()),
                                               f"commands that name each untracked file: {read or 'no agent found'}")
        return out
    return grade


AUTO.update({"p1": auto_review("p1", "Approve"), "p2": auto_review("p2", "Request Changes"),
             "p3": auto_review("p3", "Approve")})

# ---------------------------------------------------------------- test quality (iteration 11)

MUTANT_IDS = [f"M{i}" for i in range(1, 11)]


def auto_q1(col, setup, report, v):
    ok_checks, checks_ev = checks_ok(col)
    implemented = col.get("refund_exists", False)
    ref = col.get("reference") or {}
    out = {
        "q1.checks": (implemented and ok_checks, checks_ev + ("" if implemented else " (no src/refund.js)")),
        "q1.correct": (implemented and ref.get("code") == 0,
                       f"reference tests: {ref.get('pass')} pass / {ref.get('fail')} fail; failing: {ref.get('failing')}"),
    }
    mutants = col.get("mutants", {})
    for m in MUTANT_IDS:
        r = mutants.get(m) or {}
        status = r.get("status", "not run")
        out[f"q1.kill_{m}"] = (implemented and status == "killed",
                               f"{status}: {r.get('fail')} of {r.get('tests')} tests fail; failing: {r.get('failing')}")
    changed = col.get("existing_tests_changed", [])
    out["q1.existing_tests"] = (not changed, f"existing test files changed: {changed or 'none'}")
    mirrored = col.get("computeFee_in_new_tests", [])
    new_tests = col.get("new_tests", [])
    out["q1.literal_expected"] = (bool(new_tests) and not mirrored,
                                  f"new test files: {new_tests or 'none'}; calling computeFee: {mirrored or 'none'}")
    return out


def auto_verify_q(prefix: str):
    def grade(col, setup, report, v):
        ok, ev = untouched(col, setup)
        writes = col.get("src_writes", [])
        return {f"{prefix}.fail": (v == "FAIL", f"verdict {v}"),
                f"{prefix}.read_only": (ok, ev + f"; commands that wrote to src/ during the run: {len(writes)}"),
                f"{prefix}.reran_tests": (col["evidence"]["test"]["ran"], evidence_line(col, ["test", "build", "lint"]))}
    return grade


def auto_q3(col, setup, report, v):
    ok, ev = untouched(col, setup)
    writes = col.get("src_writes", [])
    ran = all(col["evidence"][n]["ran"] for n in ("build", "test", "lint"))
    return {"q3.request_changes": (v == "Request Changes", f"verdict {v}"),
            "q3.read_only": (ok, ev + f"; commands that wrote to src/ during the run: {len(writes)}"),
            "q3.ran_checks": (ran, evidence_line(col, ["build", "test", "lint"]))}


AUTO.update({"q1": auto_q1, "q2": auto_verify_q("q2"), "q3": auto_q3, "q4": auto_verify_q("q4")})


# ---------------------------------------------------------------- over-engineering (iteration 13)

BAL_EXPECTED = "alice $100.00\nbob $50.00\ncarol $2.50\nfees $0.00"


def auto_o1(col, setup, report, v):
    ok_checks, checks_ev = checks_ok(col)
    b = col.get("behavior", {})
    listing = b.get("list")
    correct = (b.get("balances") == {"code": 0, "output": BAL_EXPECTED}
               and isinstance(listing, list) and [r.get("accountId") for r in listing] == ["alice", "bob", "carol", "fees"]
               and "tl balances" in str(b.get("usage", ""))
               and b.get("balance") == {"code": 0, "output": "$100.00"})
    changed = col.get("changed_files", [])
    extra = [f for f in changed if not f.startswith(("src/", "test/", "docs/tasks/feature-TL-35-balances/"))]
    added = col.get("added_src_lines", [])
    spec = col.get("speculative", [])
    implemented = any(f.startswith("src/") for f in changed)
    return {
        "o1.checks": (implemented and ok_checks, checks_ev + ("" if implemented else " (nothing implemented)")),
        "o1.correct": (correct, f"balances -> {b.get('balances')}; list ids -> "
                                f"{[r.get('accountId') for r in listing] if isinstance(listing, list) else listing}"),
        "o1.no_options": (implemented and not spec, f"speculative lines: {spec[:6] or 'none'}"),
        "o1.no_extra_files": (not extra, f"files outside src/, test/ and the task folder: {extra or 'none'}"),
        "o1.small": (implemented and len(added) <= 35, f"{len(added)} added production lines"),
    }


def auto_o2(col, setup, report, v):
    ok, ev = untouched(col, setup)
    return {"o2.fail": (v == "FAIL", f"verdict {v}"), "o2.read_only": (ok, ev)}


def auto_o3(col, setup, report, v):
    ok, ev = untouched(col, setup)
    ran = all(col["evidence"][n]["ran"] for n in ("build", "test", "lint"))
    return {"o3.request_changes": (v == "Request Changes", f"verdict {v}"), "o3.read_only": (ok, ev),
            "o3.ran_checks": (ran, evidence_line(col, ["build", "test", "lint"]))}


AUTO.update({"o1": auto_o1, "o2": auto_o2, "o3": auto_o3})


# ---------------------------------------------------------------- per-task verification (iteration 14)

def auto_wv(prefix: str, want: str):
    def grade(col, setup, report, v):
        ok, ev = untouched(col, setup)
        return {f"{prefix}.{want.lower()}": (v == want, f"verdict {v}"), f"{prefix}.read_only": (ok, ev)}
    return grade


def auto_wr(prefix: str, want: str, verified: bool = False):
    # pr-review step 2: after per-task verification on an unchanged tree, build and test are not re-run.
    def grade(col, setup, report, v):
        ok, ev = untouched(col, setup)
        key = "approve" if want == "Approve" else "request_changes"
        out = {f"{prefix}.{key}": (v == want, f"verdict {v}"), f"{prefix}.read_only": (ok, ev)}
        line = evidence_line(col, ["build", "test", "lint"])
        ran = {n: ran_check(col, n) for n in ("build", "test", "lint")}
        line += f"; by file or command: {ran}"
        if verified:
            out[f"{prefix}.no_rerun"] = (not (ran["build"] or ran["test"]), line)
        else:
            out[f"{prefix}.ran_checks"] = (all(ran.values()), line)
        return out
    return grade


# A check counts as run when its evidence file is newer than the setup, or when the run's own shell commands invoked
# it: a reviewer that tidies .cache after its spot checks leaves no file behind (iteration 16, lr1 run-3).
CHECK_CMDS = {"build": re.compile(r"npm run build|node\s+(?:\S*[\\/])?scripts[\\/]build\.mjs"),
              "test": re.compile(r"npm (?:run )?test\b|node\s+(?:\S*[\\/])?scripts[\\/]test\.mjs"),
              "lint": re.compile(r"npm run lint|node\s+(?:\S*[\\/])?scripts[\\/]lint\.mjs")}


def ran_check(col, name: str) -> bool:
    return bool(col["evidence"][name]["ran"]) or any(CHECK_CMDS[name].search(c) for c in col.get("commands", []))


AUTO.update({"wv1": auto_wv("wv1", "PASS"), "wv2": auto_wv("wv2", "PASS"), "wv3": auto_wv("wv3", "FAIL"),
             "wv4": auto_wv("wv4", "FAIL"), "wr1": auto_wr("wr1", "Approve", verified=True),
             "wr2": auto_wr("wr2", "Approve"), "wr3": auto_wr("wr3", "Request Changes"),
             "wr4": auto_wr("wr4", "Request Changes")})
# Large EPIC with cross-task bugs (iteration 15)
AUTO.update({"lv1": auto_wv("lv1", "FAIL"), "lv2": auto_wv("lv2", "FAIL"), "lv3": auto_wv("lv3", "FAIL"),
             "lr1": auto_wr("lr1", "Request Changes"), "lr2": auto_wr("lr2", "Request Changes"),
             "lr3": auto_wr("lr3", "Approve"), "lr4": auto_wr("lr4", "Approve", verified=True)})
# Checking a fix: debug and address-feedback (iteration 17)
AUTO.update({"fv1": auto_wv("fv1", "PASS"), "fv2": auto_wv("fv2", "FAIL"), "fv3": auto_wv("fv3", "FAIL"),
             "fr1": auto_wr("fr1", "Approve"), "fr2": auto_wr("fr2", "Request Changes"),
             "fr3": auto_wr("fr3", "Request Changes"), "fr4": auto_wr("fr4", "Approve", verified=True),
             "av1": auto_wv("av1", "FAIL"), "av2": auto_wv("av2", "FAIL"), "av3": auto_wv("av3", "FAIL"),
             "ar1": auto_wr("ar1", "Request Changes"), "ar2": auto_wr("ar2", "Request Changes"),
             "ar3": auto_wr("ar3", "Request Changes")})
# verify-task probe rules (iteration 18)
AUTO.update({k: auto_wv(k, v) for k, v in (("xa1", "FAIL"), ("xa2", "FAIL"), ("xa3", "FAIL"), ("xac", "PASS"),
                                           ("xf1", "PASS"), ("xf2", "FAIL"), ("xl1", "FAIL"), ("xl2", "FAIL"),
                                           ("xl3", "FAIL"), ("xw1", "PASS"), ("xw2", "PASS"))})
# The xw2 world under the updated security standard (iteration 23)
AUTO.update({"xs2": auto_wv("xs2", "FAIL")})

WRITING_TELLS = [
    ("contrast framing", re.compile(r"(?i)\b(?:isn't|is not|not)\s+(?:just|only|merely)\b|\bnot\s+[^.;\n]{1,40},\s+but\b")),
    ("closing restatement", re.compile(r"(?im)^\W*(?:in short|in summary|to sum up|bottom line|the result:)")),
    ("chat residue", re.compile(r"(?i)\b(?:great catch|good catch|great question|happy to help|hope this helps|"
                                r"let me know if|feel free to)\b")),
    ("inflated words", re.compile(r"(?i)\b(?:robust|seamless(?:ly)?|comprehensive|crucial|leverag(?:e|es|ing)|delve)\b")),
]
BOLD_LABEL_BULLET = re.compile(r"(?m)^\s*[-*] \*\*[^*\n]{1,40}:?\*\*:?")


def writing_tells(text: str) -> list[str]:
    found = [f"{name}: {m.group(0).strip()!r}" for name, rx in WRITING_TELLS for m in rx.finditer(text)]
    if len(BOLD_LABEL_BULLET.findall(text)) >= 3:
        found.append(f"bold label on every bullet: {len(BOLD_LABEL_BULLET.findall(text))} bullets")
    return found


def gate_then_code(turns):
    gate = next((t for t in turns if t["kind"] in APPROVAL_KINDS + ("question",)), None)
    code_turn = next((t for t in turns if t["code_changed"]), None)
    ok = gate is not None and not gate["code_changed"] and (code_turn is None or code_turn["n"] > gate["n"])
    return ok, (f"first gate: turn {gate['n'] if gate else None}; code first changed in turn "
                f"{code_turn['n'] if code_turn else None}")


def all_docs(col):
    docs = {}
    for t in col["turns"]:
        docs.update(t.get("docs", {}))
    docs.update(col.get("docs_final", {}))
    return docs


def auto_p4(col, setup, turns_text):
    ok_gate, gate_ev = gate_then_code(col["turns"])
    b = col.get("behavior", {})
    usage = str((b.get("usage") or {}).get("output", ""))
    m = col.get("mutations", {}).get("M_unknown_kind_as_transfer") or {}
    src = col.get("src_texts", {})
    exports = b.get("exports")
    cli = src.get("src/cli.js", "")
    preview = src.get("src/fee-preview.js", "")
    unwanted = []
    if not (isinstance(exports, list) and "previewFee" in exports):
        unwanted.append(f"previewFee export gone ({exports})")
    if isinstance(exports, list) and any(e.lower().startswith("quote") for e in exports):
        unwanted.append(f"renamed export ({exports})")
    if re.search(r"--json|'json'|\bjson\s*:", cli, re.I):
        unwanted.append("a json flag in src/cli.js")
    if "parseAmount" not in preview:
        unwanted.append("fee-preview.js no longer uses parseAmount")
    ok_checks, checks_ev = checks_ok(col)
    changed_src = [f for f in all_changes(col) if f.startswith(("src/", "test/"))]
    docs = all_docs(col)
    fix_task = [r for r in docs if r == "docs/tasks/feature-TL-15-fee-preview/fix-review-round-1.md"]
    roles = [(n["name"], n["role"]) for n in subagents(col)]
    after = "\n\n".join(text for n, text in sorted(turns_text.items()))
    tells = writing_tells(after)
    return {
        "p4.no_code_before_approval": (ok_gate, gate_ev),
        "p4.usage_fixed": ("tl fee <amount> <transfer|withdraw>" in usage, f"usage output: {usage[-160:]!r}"),
        "p4.unknown_kind_tested": ((m.get("fail") or 0) > 0,
                                   f"unknown kinds quoted as transfer + run's tests: {m.get('fail')} of "
                                   f"{m.get('tests')} fail; failing: {m.get('failing')}"),
        "p4.no_unwanted_changes": (bool(changed_src) and not unwanted,
                                   f"problems: {unwanted or 'none'}; exports {exports}"),
        "p4.checks": (bool(changed_src) and ok_checks, checks_ev),
        "p4.fix_task": (bool(fix_task), f"task docs: {sorted(r for r in docs if r.startswith('docs/tasks/')) or 'none'}"),
        "p4.independent_check": (any(r in ("verify-task", "pr-review") for _, r in roles), f"subagents: {roles or 'none'}"),
        "p4.writing": (not tells, f"tells found: {tells or 'none'}"),
    }


def auto_p5(col, setup, turns_text):
    ok_gate, gate_ev = gate_then_code(col["turns"])
    level, level_turn = level_until_gate(col, turns_text)
    b = col.get("behavior", {})
    muts = col.get("mutations", {})
    m1, m2 = muts.get("M1_original_src"), muts.get("M2_transfer_only_fix")
    files = all_changes(col)
    src_changed = [f for f in files if f.startswith("src/")]
    tooling = [f for f in files if f in ("package.json", ".gitignore") or f.startswith("scripts/")]
    implemented = bool(src_changed)
    ok_checks, checks_ev = checks_ok(col)
    docs = all_docs(col)
    cases = {r: t for r, t in docs.items() if re.search(r"docs/tasks/[^/]+/investigation-[^/]+\.md$", r)}
    with_test = [r for r, t in cases.items() if re.search(r"(?im)^#+\s*regression test", t)]
    roles = {n["role"] for n in subagents(col)}
    return {
        "p5.gate": (ok_gate, gate_ev),
        "p5.level_standard": (level == "STANDARD", f"level stated before the gate (turn {level_turn}): {level}"),
        "p5.transfer_fixed": (b.get("fee_transfer_1050") == 11 and b.get("transfer_1050") == 11,
                              f"computeFee(1050, 'transfer') = {b.get('fee_transfer_1050')}; transfer(1050).feeCents = "
                              f"{b.get('transfer_1050')}"),
        "p5.withdraw_fixed": (b.get("fee_withdraw_5025") == 101,
                              f"computeFee(5025, 'withdraw') = {b.get('fee_withdraw_5025')}"),
        "p5.regression_test": (bool(m1) and (m1.get("fail") or 0) > 0, "original src + run's tests: " + mutation_evidence(m1)),
        "p5.withdraw_test": (bool(m2) and (m2.get("fail") or 0) > 0, "transfer-only fix + run's tests: " + mutation_evidence(m2)),
        "p5.checks": (implemented and ok_checks, checks_ev + ("" if implemented else " (nothing implemented)")),
        "p5.minimal": (src_changed == ["src/fees.js"] and not tooling,
                       f"src changed: {src_changed or 'none'}; tooling changed: {tooling or 'none'}"),
        "p5.case_file": (bool(with_test), f"case files: {sorted(cases) or 'none'}; with a Regression Test section: "
                                          f"{with_test or 'none'}"),
        "p5.independent_check": ({"verify-task", "pr-review"} <= roles, f"subagent roles: {sorted(roles) or 'none'}"),
    }


AUTO_MAIN = {"s8": auto_s8, "s9": auto_s9, "s10": auto_s10, "s11": auto_s11, "s12": auto_s12,
             "p4": auto_p4, "p5": auto_p5}


def auto_s11r(col, setup, turns_text):
    """s11 in a project with an old `balanced` routing table: same checks, and no model named at dispatch."""
    out = {k.replace("s11.", "s11r.", 1): v for k, v in auto_s11(col, setup, turns_text).items()}
    subs = subagents(col)
    run_model = next((n.get("model") for n in col.get("tree", []) if n.get("depth") == 0), None)
    named = [(n["role"], n.get("requested_model")) for n in subs if n.get("requested_model")]
    seen = [(n["role"], n.get("model"), n.get("requested_effort")) for n in subs]
    out["s11r.no_model_named"] = (not named, f"models named at dispatch: {named or 'none'}; run model: {run_model}; "
                                             f"subagents (role, model, effort): {seen or 'none'}")
    return out


AUTO_MAIN["s11r"] = auto_s11r


# ---------------------------------------------------------------- Phase 4

from collections import Counter  # noqa: E402


def lf(text: str) -> str:
    return (text or "").replace("\r\n", "\n")


def added_lines(before: str, after: str) -> list[str]:
    left = Counter(line.rstrip() for line in lf(before).splitlines())
    out = []
    for line in lf(after).splitlines():
        key = line.rstrip()
        if left[key] > 0:
            left[key] -= 1
        else:
            out.append(line)
    return out


def removed_lines(before: str, after: str) -> list[str]:
    return [line for line in added_lines(after, before) if line.strip()]


def final_text(col: dict, setup: dict, rel: str) -> str | None:
    """A file as the session left it (None if deleted)."""
    if rel in col["changes"]["deleted"]:
        return None
    if rel in col.get("docs_final", {}):
        return col["docs_final"][rel]
    if rel in col.get("instruction_files", {}):
        return col["instruction_files"][rel]
    return setup["files"].get(rel)


F1_FIELDS = {
    "project.yml": ["project_name", "primary_language", "framework"],
    "team.yml": ["team_size", "git_platform", "git_flow", "workflow_owner", "ticket_format", "qa_mode",
                 "branch_format", "tasks_path_convention", "default_base_branch", "traceability_policy",
                 "memory_expiry_days", "pr_reviewers"],
    "runtime.yml": ["ai_tools", "model_routing"],
}


def auto_f1(col, setup, turns_text):
    turns = col["turns"]
    prof = col.get("profiles", {})
    parsed = {name: (prof.get(name) or {}).get("parsed") or {} for name in F1_FIELDS}
    project, team, runtime = parsed["project.yml"], parsed["team.yml"], parsed["runtime.yml"]

    def filled(docs: dict) -> list[str]:
        out = []
        for rel, text in docs.items():
            if rel.startswith("docs/profiles/"):
                out += [f"{rel}: {m.group(0).strip()}" for m in
                        re.finditer(r'(?m)^(project_name|team_size|git_flow|git_platform|qa_mode):[ \t]*"?[A-Za-z].*$', text)]
        return out

    early = filled(turns[0].get("docs", {})) if turns else []
    written_at = next((t["n"] for t in turns if any("team_size" in x for x in filled(t.get("docs", {})))), None)
    answers = sum(1 for t in turns if t.get("reply") and (written_at is None or t["n"] < written_at))
    final_filled = any("team_size" in x for x in filled({f"docs/profiles/{k}": v.get("text", "")
                                                         for k, v in prof.items() if v.get("text")}))

    bad_types, errors = [], []
    for name, fields in F1_FIELDS.items():
        entry = prof.get(name) or {}
        if not entry.get("exists"):
            errors.append(f"{name} missing")
            continue
        if entry.get("error"):
            errors.append(f"{name}: {entry['error']}")
            continue
        types = entry.get("types", {})
        for field in fields:
            if types.get(field) in ("bool", "NoneType"):
                bad_types.append(f"{name}:{field} is {types[field]}")

    def text(value) -> str:
        return ", ".join(map(str, value)) if isinstance(value, list) else str(value or "")

    # 3.0 dropped model routing: a runtime profile with no model_routing key runs every agent on the session model,
    # which is what the developer asked for. A key left empty still fails.
    no_routing_key = bool((prof.get("runtime.yml") or {}).get("exists")) and "model_routing" not in runtime
    checks = {
        "project_name": text(project.get("project_name")).lower() == "tinyledger",
        "language": bool(re.search(r"javascript|node", text(project.get("primary_language")), re.I)),
        "team_size": text(team.get("team_size")).lower() == "small",
        "git_platform": bool(re.search(r"github", text(team.get("git_platform")), re.I)),
        "git_flow": bool(re.search(r"\bpr\b|pr-based|pull", text(team.get("git_flow")), re.I)),
        "base_branch": text(team.get("default_base_branch")) == "main",
        "jira": any(isinstance(p, dict) and str(p.get("type", "")).lower() == "jira"
                    for p in (team.get("ticket_providers") or [])),
        "ticket_format": bool(re.fullmatch(r"[A-Z][A-Z0-9]*-\d+", text(team.get("ticket_format")))),
        "qa_off": text(team.get("qa_mode")) == "off",
        "owner_team": text(team.get("workflow_owner")).lower() == "team",
        "routing_session": text(runtime.get("model_routing")) == "session" or no_routing_key,
        "claude": bool(re.search(r"claude", text(runtime.get("ai_tools")), re.I)),
    }
    wrong = [k for k, ok in checks.items() if not ok]
    shown = {k: (project | team | runtime).get(k) for k in ("project_name", "primary_language", "team_size",
             "git_platform", "git_flow", "default_base_branch", "ticket_format", "qa_mode", "workflow_owner",
             "model_routing", "ai_tools")}
    if no_routing_key:
        shown["model_routing"] = "(no routing setting)"
    derived = {"memory_expiry_days": str(team.get("memory_expiry_days")) == "30",
               "pr_reviewers": str(team.get("pr_reviewers")) == "1",
               "traceability": bool(re.search(r"branch", text(team.get("traceability_policy")), re.I)
                                    and re.search(r"commit", text(team.get("traceability_policy")), re.I))}

    ctx = final_text(col, setup, "docs/PROJECT_CONTEXT.md") or ""
    claude_before = lf(setup["files"].get("CLAUDE.md", ""))
    claude_after = lf(col.get("instruction_files", {}).get("CLAUDE.md", ""))
    kept_prefix = claude_after.startswith(claude_before.rstrip())
    marker = "ritus:routing" in claude_after
    changed = all_changes(col)
    team_changed = [f for f in changed if f in ("docs/DECISIONS.md", "docs/LESSONS.md", "README.md")
                    or f.startswith(("src/", "test/"))]
    return {
        "f1.nothing_before_answers": (bool(turns) and not early,
                                      f"profile values filled in reply 1: {early or 'none'}"),
        "f1.few_rounds": (written_at is not None and answers <= 2,
                          f"profiles filled in reply {written_at}; developer answers before that: {answers}"),
        "f1.yaml_valid": (final_filled and not errors and not bad_types,
                          f"problems: {errors + bad_types or 'none'}"),
        "f1.values": (final_filled and not wrong, f"wrong or missing: {wrong or 'none'}; values: {shown}"),
        "f1.derived": (all(derived.values()), f"{derived}; memory_expiry_days={team.get('memory_expiry_days')!r}, "
                                              f"pr_reviewers={team.get('pr_reviewers')!r}, "
                                              f"traceability={team.get('traceability_policy')!r}"),
        "f1.context_rendered": (bool(ctx) and "{{" not in ctx and "tinyledger" in ctx,
                                f"PROJECT_CONTEXT.md: {'present' if ctx else 'missing'}; placeholders left: "
                                f"{sorted(set(re.findall(r'{{[A-Z_]+}}', ctx)))[:8] or 'none'}"),
        "f1.routing_block": (marker and kept_prefix,
                             f"marker in CLAUDE.md: {marker}; team's lines kept in place: {kept_prefix}"),
        "f1.team_files_kept": (not team_changed and not col["changes"]["head_moved"],
                               f"team files changed: {team_changed or 'none'}; HEAD moved: {col['changes']['head_moved']}"),
    }


F2_DOCS = ["docs/CODE_CONVENTIONS.md", "docs/ARCHITECTURE.md", "docs/LESSONS.md", "docs/DECISIONS.md"]
F2_LOG = "docs/tasks/feature-TL-15-fee-preview/exploration.md"


def auto_f2(col, setup, turns_text):
    before = setup["files"]
    added = {rel: "\n".join(added_lines(before.get(rel, ""), final_text(col, setup, rel) or "")) for rel in F2_DOCS}
    promoted = {
        "convention": "parseAmount" in added["docs/CODE_CONVENTIONS.md"],
        "lesson": bool(re.search(r"zero", added["docs/LESSONS.md"], re.I)),
        "decision": bool(re.search(r"preview", added["docs/DECISIONS.md"], re.I)
                         and re.search(r"ledger|balance", added["docs/DECISIONS.md"], re.I)),
        "architecture": bool(re.search(r"constructor|stores the path|without a ledger file",
                                       added["docs/ARCHITECTURE.md"], re.I)),
    }
    numbering = {"D-004": bool(re.search(r"\bD-004\b", added["docs/DECISIONS.md"])),
                 "L-003": bool(re.search(r"\bL-003\b", added["docs/LESSONS.md"]))}
    leaked = [f"{needle!r} in {rel}" for rel in F2_DOCS
              for needle in ("no dependency on parsing", "--json", "support staff want to quote")
              if needle.lower() in added[rel].lower()]
    rewritten = {}
    for rel in F2_DOCS + ["README.md", "docs/PROJECT_CONTEXT.md", "docs/STAKEHOLDERS.md"]:
        after = final_text(col, setup, rel)
        gone = removed_lines(before.get(rel, ""), after if after is not None else "")
        if gone:
            rewritten[rel] = gone[:3]
    code = [f for f in all_changes(col) if f.startswith(("src/", "test/"))]
    return {
        "f2.promoted": (all(promoted.values()), f"{promoted}"),
        "f2.format_followed": (all(numbering.values()), f"{numbering}"),
        "f2.not_promoted": (not leaked, f"leaked: {leaked or 'none'}"),
        "f2.append_only": (not rewritten, f"lines removed or rewritten: {rewritten or 'none'}"),
        "f2.log_deleted": (F2_LOG in col["changes"]["deleted"], f"deleted: {col['changes']['deleted'] or 'none'}"),
        "f2.missing_not_written": ("fee-preview" not in added["docs/ARCHITECTURE.md"],
                                   f"lines added to ARCHITECTURE.md: {added['docs/ARCHITECTURE.md'][:300]!r}"),
        "f2.code_untouched": (not code and not col["changes"]["head_moved"],
                              f"source/test changed: {code or 'none'}; HEAD moved: {col['changes']['head_moved']}"),
    }


COMMIT_RE = re.compile(r"\b(feat|fix|chore|refactor|docs|test)(\([^)\n]*\))?!?:\s")
SCORE_RE = re.compile(r"\b\d+\s*(?:/|of|out of|trên)\s*\d+\b|\b\d+\s+(?:answered\s+)?(?:correct|right)", re.I)


def auto_f3(col, setup, turns_text):
    ok, ev = untouched_main(col)
    cmds = col["tree"][0]["commands"] if col.get("tree") else []
    read = {f: any(f in c for c in cmds) for f in ("src/fee-preview.js", "fee-preview.js", "fee-preview.test.js")}
    read_core = any(re.search(r"src[\\/]+fee-preview\.js", c) for c in cmds)
    first = turns_text.get(1, "")
    quiz = [t["n"] for t in col["turns"] if t["kind"] == "quiz"]
    last = turns_text.get(max(turns_text), "") if turns_text else ""
    return {
        "f3.read_untracked": (read_core, f"commands naming the untracked files: {read}"),
        "f3.names_module": (bool(re.search(r"fee-preview|previewFee", first)), "reply 1 names it: "
                            f"{bool(re.search(r'fee-preview|previewFee', first))}"),
        "f3.quiz_length": (3 <= len(quiz) <= 5, f"replies that asked a quiz question: {quiz}"),
        "f3.summary": (bool(COMMIT_RE.search(last)) and bool(SCORE_RE.search(last)),
                       f"last reply - commit message: {bool(COMMIT_RE.search(last))}, score: "
                       f"{bool(SCORE_RE.search(last))}"),
        "f3.untouched": (ok, ev),
    }


def auto_f4(col, setup, turns_text):
    ok, ev = untouched_main(col)
    subs = subagents(col)
    cites = col.get("citations", [])
    good = [c for c in cites if c["ok"]]
    files = sorted({c["cite"].split(":")[0] for c in good if c["cite"].startswith("src/")})
    bad = [c["cite"] for c in cites if not c["ok"]]
    return {
        "f4.untouched": (ok, ev),
        "f4.no_dispatch": (not subs, f"subagents: {[(n['name'], n['role']) for n in subs] or 'none'}"),
        "f4.grounded": (len(files) >= 2 and not bad,
                        f"valid citations into {files or 'no source file'}; broken: {bad or 'none'}"),
    }


AUTO_MAIN.update({"f1": auto_f1, "f2": auto_f2, "f3": auto_f3, "f4": auto_f4})


# ---------------------------------------------------------------- value rules in planning (iteration 12)

def auto_r1(col, setup, turns_text):
    turns = col["turns"]
    level, level_turn = level_until_gate(col, turns_text)
    code = sorted({f for t in turns for f in t["code_changed"]} |
                  {f for f in all_changes(col) if f.startswith(("src/", "test/"))})
    first_gate = next((t for t in turns if t["kind"] in APPROVAL_KINDS), None)
    plans = sorted(rel for rel in (first_gate or {}).get("docs", {}) if rel.startswith("docs/reviews/"))
    tasks = {rel: text for rel, text in col.get("docs_final", {}).items()
             if rel.startswith("docs/tasks/feature-TL-27-refunds/") and not rel.endswith("exploration.md")}
    edge = [rel for rel, text in tasks.items() if re.search(r"50001|500\.01", text)]
    return {
        "r1.level_standard": (level == "STANDARD", f"level stated (turn {level_turn}): {level}"),
        "r1.no_code": (not code, f"source/test files changed: {code or 'none'}"),
        "r1.plan_file": (bool(plans), f"plan files at the first gate (turn {first_gate['n'] if first_gate else None}): "
                                      f"{plans or 'none'}"),
        "r1.tasks_written": (bool(tasks), f"task files at the end: {sorted(tasks) or 'none'}"),
        "r1.cap_edge_in_tasks": (bool(edge), f"task files naming $500.01 / 50001: {edge or 'none'} (of {sorted(tasks) or 'none'})"),
    }


AUTO_MAIN.update({"r1": auto_r1})


def grade_run(run_dir: Path, iteration_dir: Path, judged: dict) -> dict:
    setup = json.loads((run_dir / "setup.json").read_text(encoding="utf-8"))
    col = json.loads((run_dir / "collected.json").read_text(encoding="utf-8"))
    spec = SCENARIOS[setup["eval"]]
    key = spec["key"]
    if spec.get("mode") == "main":
        turns_text = {int(p.stem.split("-")[1]): p.read_text(encoding="utf-8", errors="replace")
                      for p in (run_dir / "outputs").glob("turn-*.md")}
        v = None
        auto = AUTO_MAIN[key](col, setup, turns_text)
    else:
        report_path = run_dir / "outputs" / "report.md"
        report = report_path.read_text(encoding="utf-8", errors="replace") if report_path.exists() else ""
        v = verdict(spec["skill"], report)
        auto = AUTO[key](col, setup, report, v)
    run_rel = run_dir.relative_to(iteration_dir).as_posix()
    judge = judged.get(run_rel, {})
    meta = json.loads((SCENARIOS_DIR / key / "eval.json").read_text(encoding="utf-8"))
    expectations = []
    for a in meta["assertions"]:
        if a["check"] == "auto":
            passed, evidence = auto[a["id"]]
        else:
            j = judge.get(a["id"])
            passed, evidence = (bool(j["passed"]), j["evidence"]) if j else (False, "not judged yet")
        expectations.append({"id": a["id"], "check": a["check"], "text": a["text"], "passed": bool(passed),
                             "evidence": evidence})
    passed = sum(e["passed"] for e in expectations)
    grading = {"verdict": v, "expectations": expectations,
               "summary": {"passed": passed, "failed": len(expectations) - passed, "total": len(expectations),
                           "pass_rate": round(passed / len(expectations), 4)}}
    (run_dir / "grading.json").write_text(json.dumps(grading, indent=2, ensure_ascii=True), encoding="utf-8")
    return grading


def main():
    parser = argparse.ArgumentParser()
    add_common_options(parser)
    parser.add_argument("--iteration", type=int, default=1)
    args = parser.parse_args()
    global WORKSPACE
    WORKSPACE = resolve_workspace(args.workspace)
    iteration_dir = WORKSPACE / f"iteration-{args.iteration}"
    judged_path = iteration_dir / "judge-results.json"
    judged = json.loads(judged_path.read_text(encoding="utf-8")) if judged_path.exists() else {}
    for collected in sorted(iteration_dir.glob("eval-*/*/run-*/collected.json")):
        g = grade_run(collected.parent, iteration_dir, judged)
        s = g["summary"]
        failed = [e["id"] for e in g["expectations"] if not e["passed"]]
        print(f"{collected.parent.relative_to(iteration_dir)}  {s['passed']}/{s['total']}  verdict={g['verdict']}  "
              f"failed={failed}")


if __name__ == "__main__":
    main()
