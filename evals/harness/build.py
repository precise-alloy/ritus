"""Build and collect Ritus Phase 1 eval runs on the tinyledger fixture.

  python build.py build --iteration 1 --runs 2 [--evals e1,e2] [--arms new_skill,old_skill]
  python build.py collect <run_dir> [<run_dir> ...]      (or: collect-all --iteration 1)
  python build.py cleanup --iteration 1                  (removes the agent-facing temp dirs)

Agents never see the workspace: each run's repo, remote, and output dir live under a random %TEMP%\\tl-<hex> dir, and
each arm's plugin is copied to a random %TEMP%\\rp-<hex>\\ritus, so no path gives away the scenario or the arm.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import tarfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from config import (FIXTURE_DIR, REPO_ROOT, add_common_options, default_arms, resolve_session_dir,
                    resolve_skill_creator, resolve_web_modules, resolve_workspace)  # noqa: E402

BASE = FIXTURE_DIR / "base"
LAYERS = FIXTURE_DIR / "layers"
WEB_BASE = FIXTURE_DIR / "web" / "base"
WEB_LAYERS = FIXTURE_DIR / "web" / "layers"
WEB_SELFTEST = FIXTURE_DIR / "web" / "selftest"
SCENARIOS_DIR = FIXTURE_DIR / "scenarios"
EVAL_DIR = ROOT.parent
WORKSPACE = resolve_workspace(None)
WEB_MODULES = resolve_web_modules(None)
ARM_SPECS = default_arms()
SKILL_CREATOR = resolve_skill_creator(None)


def phase(iteration: int) -> int:
    return 2 if iteration >= 4 else 1


# Arms are configured by --arm (dir:<path> or git:<ref>); no iteration uses a fixed plugin snapshot.
ITERATION_PLUGINS = {}
# Iterations whose plugin copies get a stub remote helper (canned PR #12 data, no network), in both arms.
STUB_HELPER = {8: FIXTURE_DIR / "stubs" / "remote-api-pr12.ts", 98: FIXTURE_DIR / "stubs" / "remote-api-pr12.ts"}
# Scenarios that need that stub in any other iteration (p4 reads PR #12 through the helper), in both arms.
SCENARIO_STUBS = {"p4": FIXTURE_DIR / "stubs" / "remote-api-pr12.ts"}

AGENT_TMP = WORKSPACE / ".agents"
ARMS = ["new_skill", "old_skill"]
SKIP_SNAPSHOT = {".git", ".cache", "dist", "node_modules", ".playwright-cli", ".playwright-mcp", ".ritus"}

DESIGN_SKILL_SENTENCE = ("Besides the plugin roots above, this session has Figma's `figma-design-to-code` skill "
                         "installed for design work; you may load it with your skill tool.")

V2_VS_V3_SCENARIO_KEYS = [
    "e1", "e7", "s11", "s12", "s11r", "p4", "p5", "f1", "f2", "q1", "q2", "r1", "o1", "o3", "wv3",
    "wr3", "lv1", "lr1", "fv3", "ar1", "xa1", "xl3", "xs2",
]

V2_VS_V3_GROUPS = [
    ("execute", ["e1", "e7"]),
    ("plan-simple", ["s11", "s11r"]),
    ("plan-standard", ["s12", "r1"]),
    ("address-feedback", ["p4"]),
    ("debug", ["p5"]),
    ("setup", ["f1"]),
    ("wrap-up", ["f2"]),
    ("test-quality", ["q1", "q2"]),
    ("over-engineering", ["o1", "o3"]),
    ("checks-standard", ["wv3", "wr3"]),
    ("checks-epic", ["lv1", "lr1"]),
    ("checks-fixes", ["fv3", "ar1"]),
    ("verify-probes", ["xa1", "xl3", "xs2"]),
]

FRONTEND_BASELINE_KEYS = ["up1", "ug1", "us1", "uc1", "ub1", "uv1", "uv2", "uv3", "uv4", "uv5", "ur1"]

FRONTEND_BASELINE_GROUPS = [
    ("system-plan", ["up1"]),
    ("system-gate", ["ug1"]),
    ("system-simple", ["us1"]),
    ("system-standalone", ["uc1"]),
    ("probe-build", ["ub1"]),
    ("probe-verify", ["uv1", "uv2", "uv3", "uv4", "uv5"]),
    ("probe-review", ["ur1"]),
]

ROUNDS = {
    "v2-vs-v3": {
        "iteration": 26,
        "runs": 3,
        "arms": ["old_skill", "new_skill"],
        "arm_specs": {"old_skill": "git:fcbd5d5", "new_skill": "git:a610dc5"},
        "scenarios": V2_VS_V3_SCENARIO_KEYS,
        "groups": V2_VS_V3_GROUPS,
    },
    "frontend-baseline": {
        "iteration": 27,
        "runs": 3,
        "arms": ["old_skill"],
        # ritus-frontend 0.2.0 is pinned to the commit that added it, so the round measures 0.2.0 whatever
        # plugins/ritus-frontend holds in the working tree (the rewrite changes it).
        "arm_specs": {"old_skill": "git:6c03d3a+git:7e57273:plugins/ritus-frontend"},
        "scenarios": FRONTEND_BASELINE_KEYS,
        "groups": FRONTEND_BASELINE_GROUPS,
    },
}

AUTHORS = {
    "mai": ("Mai Tran", "mai.tran@example.com"),
    "quan": ("Quan Le", "quan.le@example.com"),
    "dev": ("Dev", "dev@example.com"),
}

COMMITS = {
    "W1": dict(layers=[], days=30, author="mai",
               msg="feat: TinyLedger Web - accounts, account detail, transfer"),
    "W2": dict(layers=["transfer-good", "transfer-overflow", "transfer-nolabel"], days=1, author="quan",
               msg="feat(TLW-22): note field and fee preview on the transfer page (#14)"),
    "C1": dict(layers=["pre-rename"], days=40, author="mai",
               msg="feat: tinyledger core - ledger, transfers, fees, receipts, CLI"),
    "C2": dict(layers=[], days=15, author="quan",
               msg="refactor(money): rename formatCents to formatAmount, add currency support\n\n"
                   "Balances and receipts can be shown in EUR and GBP. formatCents(cents) is now\n"
                   "formatAmount(cents, currency = 'USD'), and renderReceipt takes the same optional currency."),
    "C3": dict(layers=["parse-amount"], days=10, author="mai",
               msg="feat(TL-9): accept typed amounts like 12.50 in the CLI"),
    "C4": dict(layers=["parse-amount", "withdraw"], days=6, author="mai",
               msg="feat(TL-14): withdrawals with a 2% fee (25 cent minimum)"),
    "C4R": dict(layers=["parse-amount", "withdraw", "fees-halfup-test"], days=5, author="quan",
                msg="test(fees): pin half-up rounding for both fee kinds (D-002)"),
    "C5": dict(layers=["parse-amount", "withdraw", "fees-floor"], days=3, author="quan",
               msg="refactor(fees): table-driven fee schedule\n\n"
                   "One SCHEDULE entry per fee kind instead of two parallel maps, ahead of the refund fee."),
}

FULL_HISTORY = ["C1", "C2", "C3", "C4", "C5"]
TL27_MAIN = ["C1", "C2", "C3", "C4", "C4R"]
TL27_LAYERS = ["parse-amount", "withdraw", "fees-halfup-test"]
TL40_TASKS = [f"l-t{i}" for i in range(1, 9)]
TL21_C5 = ["parse-amount", "withdraw", "fees-floor"]
TL27_PR_LAYERS = TL27_LAYERS + ["s-t1-good", "s-t2", "a-pr-docs"]
TL27_PR_COMMIT = dict(layers=TL27_PR_LAYERS, days=2, author="dev",
                      msg="feat(TL-27): refund a mistaken transfer\n\n"
                          "- refund() moves the amount back, and the transfer fee with --fee; refuses above $500.00 "
                          "until TL-31\n- tl refund <from> <to> <amount> [--fee]\n\nBreaking: none\nMigration: none")
NO_RITUS = ["docs/PROJECT_CONTEXT.md", "docs/STAKEHOLDERS.md", "docs/tasks/README.md"]
TL16_COMMIT_001 = dict(layers=["receipt-fee"], days=1, author="dev",
                       msg="feat(TL-16): show fee and total on receipts\n\n"
                           "- receipts list Fee and Total (amount + fee) after Amount, in the receipt currency\n\n"
                           "Breaking: none\nMigration: none")

# world: main commits, branch, branch commits (layers on top of base), uncommitted working-tree layers.
# mode "main": the agent plays the main thread of a user's session (multi-turn); otherwise it is a dispatched worker.
SCENARIOS = {
    "eval-1-stale-helper": dict(
        key="e1", skill="execute-task", main=["C1", "C2"], branch="feature/TL-12-receipt-fees",
        branch_commits=[], worktree=None, push_branch=False),
    "eval-2-binding-conflict": dict(
        key="e2", skill="execute-task", main=["C1", "C2", "C3"], branch="feature/TL-14-withdrawals",
        branch_commits=[], worktree=None, push_branch=False),
    "eval-3-verify-unmet-acceptance": dict(
        key="e3", skill="verify-task", main=["C1", "C2"], branch="feature/TL-16-friendly-amounts", doc_sets=["tl16"],
        branch_commits=[dict(layers=["receipt-fee"], days=1, author="dev",
                             msg="feat(TL-16): show fee and total on receipts\n\n"
                                 "- receipts list Fee and Total (amount + fee) after Amount, in the receipt currency\n\n"
                                 "Breaking: none\nMigration: none")],
        worktree=["receipt-fee", "e3-impl"], push_branch=True),
    "eval-4-verify-uncommitted-prior": dict(
        key="e13", skill="verify-task", main=["C1", "C2"], branch="feature/TL-16-friendly-amounts", doc_sets=["tl16"],
        branch_commits=[], worktree=["receipt-fee", "e13-impl"], push_branch=False),
    "eval-5-shared-function-fix": dict(
        key="e7", skill="execute-task", main=["C1", "C2", "C3", "C4", "C5"],
        branch="bugfix/TL-21-transfer-fee-rounding", branch_commits=[], worktree=None, push_branch=False),
    "eval-6-review-reruns-checks": dict(
        key="e11p", skill="pr-review", main=["C1", "C2", "C3", "C4"], branch="feature/TL-15-fee-preview",
        branch_commits=[], worktree=["parse-amount", "withdraw", "fee-cmd-broken"], push_branch=False),
    "eval-7-start-no-setup": dict(
        key="s8", mode="main", skill="start-ritus", main=FULL_HISTORY, branch="main", branch_commits=[],
        worktree=None, push_branch=False, world_layers=["no-ritus"], drop=NO_RITUS),
    "eval-8-start-resume": dict(
        key="s9", mode="main", skill="start-ritus", main=["C1", "C2"], branch="feature/TL-16-friendly-amounts",
        doc_sets={"old_skill": ["tl16"], "new_skill": []}, branch_commits=[TL16_COMMIT_001],
        worktree=["receipt-fee", "e13-impl"], push_branch=True),
    "eval-9-start-bug-handoff": dict(
        key="s10", mode="main", skill="start-ritus", main=FULL_HISTORY, branch="main", branch_commits=[],
        worktree=None, push_branch=False),
    "eval-10-simple-inline": dict(
        key="s11", mode="main", skill="ticket-review", main=FULL_HISTORY, branch="feature/TL-33-unknown-command",
        branch_commits=[], worktree=None, push_branch=False),
    "eval-11-standard-constraint": dict(
        key="s12", mode="main", skill="ticket-review", main=["C1", "C2"], branch="feature/TL-44-typed-amounts",
        branch_commits=[], worktree=None, push_branch=False),
    # Phase 3
    "eval-12-pr-clean-untracked": dict(
        key="p1", skill="pr-review", main=["C1", "C2", "C3", "C4"], branch="feature/TL-15-fee-preview",
        doc_sets=["fee15"], branch_commits=[], worktree=["parse-amount", "withdraw", "fee15-clean"], push_branch=False),
    "eval-13-pr-bug-untracked": dict(
        key="p2", skill="pr-review", main=["C1", "C2", "C3", "C4"], branch="feature/TL-15-fee-preview",
        doc_sets=["fee15"], branch_commits=[],
        worktree=["parse-amount", "withdraw", "fee15-clean", "fee15-bug"], push_branch=False),
    "eval-14-pr-rereview": dict(
        key="p3", skill="pr-review", main=["C1", "C2", "C3", "C4"], branch="feature/TL-15-fee-preview",
        doc_sets=["fee15"],
        branch_commits=[dict(layers=["parse-amount", "withdraw", "fee15-clean", "fee15-bug"], days=1, author="dev",
                             msg="feat(TL-15): tl fee previews the fee of a transfer or a withdrawal")],
        worktree=["parse-amount", "withdraw", "fee15-clean"], push_branch=False),
    "eval-15-af-six-comments": dict(
        key="p4", mode="main", skill="address-feedback", main=["C1", "C2", "C3", "C4"],
        branch="feature/TL-15-fee-preview",
        branch_commits=[dict(layers=["parse-amount", "withdraw", "fee15-clean", "fee15-af"], days=1, author="dev",
                             msg="feat(TL-15): tl fee previews the fee of a transfer or a withdrawal")],
        worktree=None, push_branch=True),
    "eval-16-debug-shared-fee": dict(
        key="p5", mode="main", skill="debug", main=FULL_HISTORY, branch="bugfix/fee-rounding", branch_commits=[],
        worktree=None, push_branch=False),
    # Phase 4
    "eval-17-setup-detect": dict(
        key="f1", mode="main", skill="setup", main=FULL_HISTORY, branch="main", branch_commits=[],
        worktree=None, push_branch=False, world_layers=["no-ritus", "claude-md"], drop=NO_RITUS,
        remote_url="https://github.com/tinyledger-dev/tinyledger.git"),
    "eval-18-wrapup-docs": dict(
        key="f2", mode="main", skill="wrap-up", main=["C1", "C2", "C3", "C4"], branch="feature/TL-15-fee-preview",
        branch_commits=[], worktree=["parse-amount", "withdraw", "fee15-clean"], push_branch=False,
        world_layers=["conventions"]),
    "eval-19-comprehension-untracked": dict(
        key="f3", mode="main", skill="comprehension", main=["C1", "C2", "C3", "C4"],
        branch="feature/TL-15-fee-preview", branch_commits=[], worktree=["parse-amount", "withdraw", "fee15-clean"],
        push_branch=False),
    "eval-20-brainstorm-refunds": dict(
        key="f4", mode="main", skill="brainstorm", main=["C1", "C2", "C3", "C4"], branch="main", branch_commits=[],
        worktree=None, push_branch=False),
    # Test quality (iteration 11)
    "eval-21-execute-refund-tests": dict(
        key="q1", skill="execute-task", main=TL27_MAIN, branch="feature/TL-27-refunds", doc_sets=["tl27"],
        branch_commits=[], worktree=None, push_branch=False),
    "eval-22-verify-hollow-tests": dict(
        key="q2", skill="verify-task", main=TL27_MAIN, branch="feature/TL-27-refunds", doc_sets=["tl27", "tl27impl"],
        branch_commits=[], worktree=TL27_LAYERS + ["refund-impl", "refund-tests-hollow"], push_branch=False),
    "eval-23-review-hollow-tests": dict(
        key="q3", skill="pr-review", main=TL27_MAIN, branch="feature/TL-27-refunds", doc_sets=["tl27", "tl27impl"],
        branch_commits=[], worktree=TL27_LAYERS + ["refund-impl", "refund-tests-hollow"], push_branch=False),
    "eval-24-verify-weakened-test": dict(
        key="q4", skill="verify-task", main=TL27_MAIN, branch="feature/TL-27-refunds", doc_sets=["tl27", "tl27impl"],
        branch_commits=[],
        worktree=TL27_LAYERS + ["refund-impl", "refund-tests-good-norounding", "fees-floor-tamper"],
        push_branch=False),
    # Value rules in planning (iteration 12)
    "eval-25-plan-value-rules": dict(
        key="r1", mode="main", skill="ticket-review", main=TL27_MAIN, branch="feature/TL-27-refunds",
        branch_commits=[], worktree=None, push_branch=False),
    # Over-engineering (iteration 13)
    "eval-26-execute-balances": dict(
        key="o1", skill="execute-task", main=["C1", "C2", "C3", "C4"], branch="feature/TL-35-balances",
        doc_sets=["tl35"], branch_commits=[], worktree=None, push_branch=False),
    "eval-27-verify-overbuilt": dict(
        key="o2", skill="verify-task", main=["C1", "C2", "C3", "C4"], branch="feature/TL-35-balances",
        doc_sets=["tl35", "tl35impl"], branch_commits=[],
        worktree=["parse-amount", "withdraw", "balances-overbuilt"], push_branch=False),
    "eval-28-review-overbuilt": dict(
        key="o3", skill="pr-review", main=["C1", "C2", "C3", "C4"], branch="feature/TL-35-balances",
        doc_sets=["tl35", "tl35impl"], branch_commits=[],
        worktree=["parse-amount", "withdraw", "balances-overbuilt"], push_branch=False),
    # Per-task verification: cost on clean work, catch rate on a planted boundary bug (iteration 14)
    "eval-29-verify-s-clean-t1": dict(key="wv1", skill="verify-task", main=TL27_MAIN, branch="feature/TL-27-refunds",
                                      branch_commits=[], worktree=TL27_LAYERS + ["s-t1-good"], push_branch=False),
    "eval-30-verify-s-clean-t2": dict(key="wv2", skill="verify-task", main=TL27_MAIN, branch="feature/TL-27-refunds",
                                      branch_commits=[], worktree=TL27_LAYERS + ["s-t1-good", "s-t2"], push_branch=False),
    "eval-31-verify-s-bug-t1": dict(key="wv3", skill="verify-task", main=TL27_MAIN, branch="feature/TL-27-refunds",
                                    branch_commits=[], worktree=TL27_LAYERS + ["s-t1-bug"], push_branch=False),
    "eval-32-verify-e-bug-t2": dict(key="wv4", skill="verify-task", main=TL27_MAIN, branch="feature/TL-27-refunds",
                                    branch_commits=[], worktree=TL27_LAYERS + ["e-t1", "e-t2-bug"], push_branch=False),
    "eval-33-review-s-clean-verified": dict(key="wr1", skill="pr-review", main=TL27_MAIN, branch="feature/TL-27-refunds",
                                            branch_commits=[], worktree=TL27_LAYERS + ["s-t1-good", "s-t2"],
                                            push_branch=False),
    "eval-34-review-s-clean-unverified": dict(key="wr2", skill="pr-review", main=TL27_MAIN,
                                              branch="feature/TL-27-refunds", branch_commits=[],
                                              worktree=TL27_LAYERS + ["s-t1-good", "s-t2"], push_branch=False),
    "eval-35-review-s-bug-unverified": dict(key="wr3", skill="pr-review", main=TL27_MAIN, branch="feature/TL-27-refunds",
                                            branch_commits=[], worktree=TL27_LAYERS + ["s-t1-bug", "s-t2"],
                                            push_branch=False),
    "eval-36-review-e-bug-unverified": dict(key="wr4", skill="pr-review", main=TL27_MAIN, branch="feature/TL-27-refunds",
                                            branch_commits=[],
                                            worktree=TL27_LAYERS + ["e-t1", "e-t2-bug", "e-t3", "e-t4"],
                                            push_branch=False),
    # Per-task verification vs end review on a large EPIC (TL-40, 8 tasks) with cross-task bugs (iteration 15)
    "eval-37-verify-l-fee-t1": dict(key="lv1", skill="verify-task", main=TL27_MAIN, branch="feature/TL-40-refunds",
                                    branch_commits=[], worktree=TL27_LAYERS + ["l-b1-t1"], push_branch=False),
    "eval-38-verify-l-list-t6": dict(key="lv2", skill="verify-task", main=TL27_MAIN, branch="feature/TL-40-refunds",
                                     branch_commits=[], worktree=TL27_LAYERS + TL40_TASKS[:6] + ["l-b2-t6"],
                                     push_branch=False),
    "eval-39-verify-l-clean-t7": dict(key="lv3", skill="verify-task", main=TL27_MAIN, branch="feature/TL-40-refunds",
                                      branch_commits=[], worktree=TL27_LAYERS + TL40_TASKS[:7], push_branch=False),
    "eval-40-review-l-fee-unverified": dict(key="lr1", skill="pr-review", main=TL27_MAIN,
                                            branch="feature/TL-40-refunds", branch_commits=[],
                                            worktree=TL27_LAYERS + TL40_TASKS + ["l-b1-full"], push_branch=False),
    "eval-41-review-l-list-unverified": dict(key="lr2", skill="pr-review", main=TL27_MAIN,
                                            branch="feature/TL-40-refunds", branch_commits=[],
                                            worktree=TL27_LAYERS + TL40_TASKS + ["l-b2-t6"], push_branch=False),
    "eval-42-review-l-clean-unverified": dict(key="lr3", skill="pr-review", main=TL27_MAIN,
                                             branch="feature/TL-40-refunds", branch_commits=[],
                                             worktree=TL27_LAYERS + TL40_TASKS, push_branch=False),
    "eval-43-review-l-clean-verified": dict(key="lr4", skill="pr-review", main=TL27_MAIN,
                                            branch="feature/TL-40-refunds", branch_commits=[],
                                            worktree=TL27_LAYERS + TL40_TASKS, push_branch=False),
    # Checking a fix: verify-task against pr-review, debug (TL-21 case file) and address-feedback (PR #7 round 1)
    **{name: dict(key=key, skill=skill, main=FULL_HISTORY, branch="bugfix/TL-21-fee-rounding", branch_commits=[],
                  worktree=TL21_C5 + [layer], push_branch=False)
       for name, key, skill, layer in (
           ("eval-44-fixcheck-debug-verify-good", "fv1", "verify-task", "d-fix-good"),
           ("eval-45-fixcheck-debug-verify-ceil", "fv2", "verify-task", "d-fix-ceil"),
           ("eval-46-fixcheck-debug-verify-transfer-only", "fv3", "verify-task", "d-fix-transfer-only"),
           ("eval-47-fixcheck-debug-review-good", "fr1", "pr-review", "d-fix-good"),
           ("eval-48-fixcheck-debug-review-ceil", "fr2", "pr-review", "d-fix-ceil"),
           ("eval-49-fixcheck-debug-review-transfer-only", "fr3", "pr-review", "d-fix-transfer-only"),
           ("eval-50-fixcheck-debug-review-good-verified", "fr4", "pr-review", "d-fix-good"))},
    **{name: dict(key=key, skill=skill, main=TL27_MAIN, branch="feature/TL-27-refunds", branch_commits=[TL27_PR_COMMIT],
                  worktree=TL27_PR_LAYERS + [layer], push_branch=True)
       for name, key, skill, layer in (
           ("eval-51-fixcheck-af-verify-good", "av1", "verify-task", "a-fix-good"),
           ("eval-52-fixcheck-af-verify-partial", "av2", "verify-task", "a-fix-partial"),
           ("eval-53-fixcheck-af-verify-after-apply", "av3", "verify-task", "a-fix-after-apply"),
           ("eval-54-fixcheck-af-review-good", "ar1", "pr-review", "a-fix-good"),
           ("eval-55-fixcheck-af-review-partial", "ar2", "pr-review", "a-fix-partial"),
           ("eval-56-fixcheck-af-review-after-apply", "ar3", "pr-review", "a-fix-after-apply"))},
}

def _reuse(source_eval: str, key: str, worktree=None) -> dict:
    """An earlier verify world under a new key: its docs come from the source scenario, its inputs from the new one."""
    spec = dict(SCENARIOS[source_eval])
    spec["doc_sets"] = [*spec.get("doc_sets", []), spec["key"]]
    spec["key"] = key
    if worktree is not None:
        spec["worktree"] = worktree
    return spec


# Iteration 18: verify-task before and after the probe rules, on the worlds of iterations 14, 15 and 17.
SCENARIOS.update({
    "eval-57-probe-af-good": _reuse("eval-51-fixcheck-af-verify-good", "xa1"),
    "eval-58-probe-af-partial": _reuse("eval-52-fixcheck-af-verify-partial", "xa2"),
    "eval-59-probe-af-after-apply": _reuse("eval-53-fixcheck-af-verify-after-apply", "xa3"),
    "eval-60-probe-af-clean": _reuse("eval-51-fixcheck-af-verify-good", "xac",
                                     worktree=TL27_PR_LAYERS + ["a-fix-clean"]),
    "eval-61-probe-debug-good": _reuse("eval-44-fixcheck-debug-verify-good", "xf1"),
    "eval-62-probe-debug-ceil": _reuse("eval-45-fixcheck-debug-verify-ceil", "xf2"),
    "eval-63-probe-epic-fee": _reuse("eval-37-verify-l-fee-t1", "xl1"),
    "eval-64-probe-epic-list": _reuse("eval-38-verify-l-list-t6", "xl2"),
    "eval-65-probe-epic-usage": _reuse("eval-39-verify-l-clean-t7", "xl3"),
    "eval-66-probe-std-refund-clean": _reuse("eval-29-verify-s-clean-t1", "xw1", worktree=TL27_LAYERS + ["s-t1-clean"]),
    "eval-67-probe-std-cli-clean": _reuse("eval-30-verify-s-clean-t2", "xw2",
                                          worktree=TL27_LAYERS + ["s-t1-clean", "s-t2"]),
})
# Iteration 24: the SIMPLE ticket (s11) in a project whose docs still carry an old `balanced` routing table.
SCENARIOS["eval-69-simple-oldrouting"] = dict(
    key="s11r", mode="main", skill="ticket-review", main=FULL_HISTORY, branch="feature/TL-33-unknown-command",
    branch_commits=[], worktree=None, push_branch=False, world_layers=["old-routing"])
# Iteration 23: the xw2 world under the updated security standard (CLI flags are boundary input).
SCENARIOS["eval-68-probe-std-cli-sec"] = _reuse("eval-30-verify-s-clean-t2", "xs2",
                                                worktree=TL27_LAYERS + ["s-t1-clean", "s-t2"])

# Frontend eval UI verdicts. `ui_verdicts()` records every verdict; scenario
# entries declare which ones apply to the world and should be shown to judges.
UI_BASE_VERDICTS = ("routes_ok", "no_overflow", "axe_clean", "console_clean", "tokens_only")
UI_CARD_VERDICTS = ("card_geometry", "card_colors", "card_type", "card_total", "card_full_width",
                    "card_reuses_component")
UI_TRANSFER_VERDICTS = ("transfer_layout",)
UI_EMPTY_VERDICTS = ("empty_state",)


def scenario_ui_verdicts(key: str) -> tuple[str, ...]:
    for spec in SCENARIOS.values():
        if spec["key"] == key:
            return tuple(spec.get("ui_verdicts", ()))
    raise KeyError(f"unknown scenario key {key}")


# Frontend eval main-thread scenarios (iteration 27).
SCENARIOS.update({
    "eval-70-ui-plan": dict(
        key="up1", mode="main", skill="ticket-review", fixture="web", main=["W1"],
        branch="feature/TLW-22-transfer-note-fee", branch_commits=[], worktree=None, push_branch=False,
        ui_verdicts=()),
    "eval-78-ui-gate": dict(
        key="ug1", mode="main", skill="start-ritus", fixture="web", main=["W1"],
        branch="feature/TLW-22-transfer-note-fee", doc_sets=["tlw22"],
        branch_commits=[dict(layers=["transfer-good", "transfer-overflow", "transfer-nolabel"], days=1,
                             author="quan",
                             msg="feat(TLW-22): note field and fee preview on the transfer page")],
        worktree=None, push_branch=True, ui_verdicts=UI_BASE_VERDICTS + UI_TRANSFER_VERDICTS),
    "eval-79-ui-simple-empty": dict(
        key="us1", mode="main", skill="ticket-review", fixture="web", main=["W1"],
        branch="feature/TLW-31-empty-transactions", branch_commits=[], worktree=None, push_branch=False,
        ui_verdicts=UI_BASE_VERDICTS + UI_EMPTY_VERDICTS),
    "eval-80-ui-check-standalone": dict(
        key="uc1", mode="main", skill="none", fixture="web", main=["W1", "W2"],
        branch="main", branch_commits=[], worktree=None, push_branch=False,
        ui_verdicts=UI_BASE_VERDICTS + UI_TRANSFER_VERDICTS),
})

# Frontend eval worker probes (iteration 27).
SCENARIOS.update({
    "eval-71-ui-build-design": dict(
        key="ub1", skill="execute-task", fixture="web", main=["W1"],
        branch="feature/TLW-21-total-balance-card", doc_sets=["tlw21"],
        branch_commits=[], worktree=None, push_branch=False,
        ui_verdicts=UI_BASE_VERDICTS + UI_CARD_VERDICTS),
    "eval-72-ui-verify-gap": dict(
        key="uv1", skill="verify-task", fixture="web", main=["W1"],
        branch="feature/TLW-21-total-balance-card", doc_sets=["tlw21"],
        branch_commits=[], worktree=["card-good", "card-gap"], push_branch=False,
        ui_verdicts=UI_BASE_VERDICTS + UI_CARD_VERDICTS),
    "eval-73-ui-verify-overflow": dict(
        key="uv2", skill="verify-task", fixture="web", main=["W1"],
        branch="feature/TLW-22-transfer-note-fee", doc_sets=["tlw22"],
        branch_commits=[], worktree=["transfer-good", "transfer-overflow"], push_branch=False,
        ui_verdicts=UI_BASE_VERDICTS + UI_TRANSFER_VERDICTS),
    "eval-74-ui-verify-label": dict(
        key="uv3", skill="verify-task", fixture="web", main=["W1"],
        branch="feature/TLW-22-transfer-note-fee", doc_sets=["tlw22"],
        branch_commits=[], worktree=["transfer-good", "transfer-nolabel"], push_branch=False,
        ui_verdicts=UI_BASE_VERDICTS + UI_TRANSFER_VERDICTS),
    "eval-75-ui-verify-empty": dict(
        key="uv4", skill="verify-task", fixture="web", main=["W1"],
        branch="feature/TLW-23-transactions-polish", doc_sets=["tlw23"],
        branch_commits=[], worktree=["txn-good", "txn-noempty"], push_branch=False,
        ui_verdicts=UI_BASE_VERDICTS + UI_EMPTY_VERDICTS),
    "eval-76-ui-verify-clean": dict(
        key="uv5", skill="verify-task", fixture="web", main=["W1"],
        branch="feature/TLW-22-transfer-note-fee", doc_sets=["tlw22"],
        branch_commits=[], worktree=["transfer-good"], push_branch=False,
        ui_verdicts=UI_BASE_VERDICTS + UI_TRANSFER_VERDICTS),
    "eval-77-ui-review-hex-console": dict(
        key="ur1", skill="pr-review", fixture="web", main=["W1"],
        branch="feature/TLW-21-total-balance-card", doc_sets=["tlw21"],
        branch_commits=[dict(layers=["card-good", "card-hex-console"], days=1, author="dev",
                             msg="feat(TLW-21): total balance card on the accounts page")],
        worktree=None, push_branch=True, ui_verdicts=UI_BASE_VERDICTS + UI_CARD_VERDICTS),
})

# The one line where each arm's task-generation template (templates/task-files.md) differs.
STANDARDS_LINE = {
    "old_skill": "- [ ] Standards validated: all applicable gates from `definition-of-done` skill checked",
    "new_skill": '- [ ] Standards validated: "Done means" in `skills/shared/standards/engineering.md` and every '
                 "applicable check in `testing.md` / `security.md`",
}

PROMPT_TEMPLATE = """\
You are a subagent dispatched by the Ritus main thread. You cannot talk to the user: everything you get is in this
brief and on disk.

Ritus plugin root: {plugin}
Paths such as `skills/...` inside the skills are relative to the plugin root. Read Ritus skills only from there, with
absolute paths. Other copies of Ritus may exist on this machine (an installed plugin, a skill tool, a source checkout);
do not use any of them.
{companion_worker_context}{design_skill_context}
Follow the `{skill}` skill: read {plugin}\\skills\\{skill}\\SKILL.md and do what it says.

Project repository: {repo} (current branch `{branch}`, base branch `main`, remote `origin`).
This is Windows PowerShell and each shell call starts in an unrelated directory, so begin every shell command with
`Set-Location '{repo}';`. Do not read or change anything outside the plugin root{worker_companion_clause} and the project repository.

Inputs from the main thread:

{inputs}

When you finish, write your final report verbatim to {outputs}\\report.md and return the same report as your final
message.
"""


MAIN_PROMPT_TEMPLATE = """\
You are the assistant in a developer's coding session on the project repository below, and the Ritus workflow plugin
is installed in this session. Play that role for the whole conversation: the developer's messages arrive as turns, and
you work the way Ritus says.

Ritus plugin root: {plugin}
A Ritus skill is a folder under `{plugin}\\skills\\`: to use a skill, read its `SKILL.md` with an absolute path and do
what it says. Paths such as `skills/...` inside the skills are relative to the plugin root. Other copies of Ritus may
exist on this machine (an installed plugin, a skill tool, a source checkout); do not use any of them.
{companion_main_context}{design_skill_context}
The Ritus skills in this session, as the harness lists them (name: description):

{skills}
{session_start_registry}
Project repository: {repo} (current branch `{branch}`, base branch `main`, remote `origin`).
This is Windows PowerShell and each shell call starts in an unrelated directory, so begin every shell command with
`Set-Location '{repo}';`. Do not read or change anything outside the plugin root, the project repository{main_companion_clause} and
{outputs}.

How this session works:

- The developer is here. This session is interactive, whatever your harness says about non-interactive mode: every
  reply you send reaches the developer, and their answer comes back to you as a new turn. So when a skill tells you
  to ask, to present something for approval, or to wait for the developer, do that: end your turn there instead of
  going on without them.
- Subagents. Where a skill says to dispatch or start a subagent, start one with your subagent tool (agent type
  general-purpose). It cannot see this conversation or resolve plugin paths, so give it the absolute paths it needs
  (the plugin root and the repository) and tell it to begin every shell command with `Set-Location '{repo}';`.
- TODO lists. Other sessions share your todo and SQL tools, so keep any TODO list a skill asks for in
  `{outputs}\\todo.md` and update it there.
- Talking to the developer. They see only your replies. Whenever you reply - a question, a request for approval, a
  progress or final report - write the reply verbatim to `{outputs}\\turn-<N>.md` (N counts your replies, starting at
  1), then end your turn with the same text. Their answer arrives as your next turn; never answer for them.
- Git. Commits, pushes and branches are the developer's; make none.

{invocation}
{message}"""


def _skill_lines(root: Path, marker: str = "") -> list[str]:
    lines = []
    for skill_md in sorted(Path(root, "skills").glob("*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        name = re.search(r"^name:\s*(.+)$", text, re.M).group(1).strip()
        desc = re.search(r"^description:\s*(.+)$", text, re.M).group(1).strip()
        prefix = f"- {name}{marker}:" if marker else f"- {name}:"
        lines.append(f"{prefix} {desc}")
    return lines


def skill_catalog(plugin: Path, companion: Path | None = None) -> str:
    """Name and description of every skill in a plugin copy, the way a harness lists them."""
    lines = _skill_lines(plugin)
    if companion is not None:
        companion_name = companion_manifest(companion).get("name", companion.name)
        lines.extend(_skill_lines(companion, f" (companion {companion_name})"))
    return "\n".join(lines)



def configure_paths(workspace: str | Path | None = None, arm_specs: dict[str, str] | None = None,
                    skill_creator: str | Path | None = None, web_modules: str | Path | None = None):
    global WORKSPACE, AGENT_TMP, WEB_MODULES, ARM_SPECS, SKILL_CREATOR
    WORKSPACE = Path(workspace).expanduser().resolve() if workspace else resolve_workspace(None)
    AGENT_TMP = WORKSPACE / ".agents"
    WEB_MODULES = Path(web_modules).expanduser().resolve() if web_modules else resolve_web_modules(None)
    if arm_specs is not None:
        ARM_SPECS = arm_specs
    SKILL_CREATOR = Path(skill_creator).expanduser().resolve() if skill_creator else resolve_skill_creator(None)


def arm_spec_error(item: str) -> SystemExit:
    return SystemExit("invalid arm " + repr(item) + "; spec must be <name>=<ritus spec> or "
                      "<name>=<ritus spec>+<companion spec>; ritus spec is dir:<path> or git:<ref>; "
                      "companion spec is dir:<path> or git:<ref>:<path in repo>")


def parse_companion_git_spec(spec: str) -> tuple[str, str]:
    body = spec[4:]
    if ":" not in body:
        raise ValueError("missing companion path")
    ref, path = body.split(":", 1)
    if not ref or not path:
        raise ValueError("missing companion ref or path")
    return ref, path.replace("\\", "/").strip("/")


def validate_arm_spec(item: str, spec: str):
    parts = spec.split("+")
    if len(parts) > 2 or any(not part for part in parts):
        raise arm_spec_error(item)
    ritus = parts[0]
    if not (ritus.startswith("dir:") and ritus[4:] or ritus.startswith("git:") and ritus[4:]):
        raise arm_spec_error(item)
    if len(parts) == 2:
        companion = parts[1]
        if companion.startswith("dir:") and companion[4:]:
            return
        if companion.startswith("git:"):
            try:
                parse_companion_git_spec(companion)
                return
            except ValueError:
                pass
        raise arm_spec_error(item)


def parse_arm_specs(overrides: list[str] | None) -> dict[str, str]:
    specs = default_arms()
    for item in overrides or []:
        if "=" not in item:
            raise SystemExit(f"--arm must be <name>=<spec>, got {item!r}")
        name, spec = item.split("=", 1)
        if not name:
            raise arm_spec_error(item)
        validate_arm_spec(item, spec)
        specs[name] = spec
    return specs


def split_arm_spec(spec: str) -> tuple[str, str | None]:
    if "+" not in spec:
        return spec, None
    ritus, companion = spec.split("+", 1)
    return ritus, companion


def scratch_root() -> Path:
    root = WORKSPACE / ".tmp"
    root.mkdir(parents=True, exist_ok=True)
    return root


def tempdir(prefix: str):
    return tempfile.TemporaryDirectory(prefix=prefix, dir=scratch_root())


def marketplace_source(ref: str) -> str:
    for manifest in (".claude-plugin/marketplace.json", "marketplace.json"):
        proc = git(REPO_ROOT, "show", f"{ref}:{manifest}", check=False)
        if proc.returncode != 0 or not proc.stdout.strip():
            continue
        data = json.loads(proc.stdout)
        for plugin in data.get("plugins", []):
            if plugin.get("name") == "ritus":
                source = plugin.get("source", "./")
                return source.get("path", "./") if isinstance(source, dict) else source
    raise RuntimeError(f"could not read ritus source from marketplace manifest at {ref}")


def archive_treeish(treeish: str, dest: Path):
    archive = scratch_root() / f"arm-{secrets.token_hex(3)}.tar"
    try:
        git(REPO_ROOT, "archive", "--format=tar", "-o", str(archive), treeish)
        dest.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive) as tf:
            tf.extractall(dest)
    finally:
        if archive.exists():
            archive.unlink()


def archive_ref(ref: str, dest: Path):
    source = marketplace_source(ref).replace("\\", "/").strip("/")
    treeish = ref if source in ("", ".") else f"{ref}:{source}"
    archive_treeish(treeish, dest)


def archive_companion_ref(spec: str, dest: Path):
    ref, path = parse_companion_git_spec(spec)
    archive_treeish(f"{ref}:{path}", dest)


def copy_dir_source(spec: str, dest: Path):
    source = Path(spec[4:]).expanduser().resolve()
    if not source.is_dir():
        raise RuntimeError(f"arm source does not exist: {source}")
    shutil.copytree(source, dest)


def build_source_copy(spec: str, dest: Path, *, companion: bool = False):
    if spec.startswith("dir:"):
        copy_dir_source(spec, dest)
    elif spec.startswith("git:") and companion:
        archive_companion_ref(spec, dest)
    elif spec.startswith("git:"):
        archive_ref(spec[4:], dest)
    else:
        raise RuntimeError(f"unsupported arm spec: {spec}")


def companion_manifest(root: Path) -> dict:
    path = root / "ritus-companion.json"
    if not path.is_file():
        raise RuntimeError(f"companion {root} is missing ritus-companion.json")
    return json.loads(path.read_text(encoding="utf-8"))


def companion_plugin_name(root: Path) -> str:
    plugin_json = root / ".claude-plugin" / "plugin.json"
    if plugin_json.is_file():
        name = json.loads(plugin_json.read_text(encoding="utf-8")).get("name")
        if name:
            return str(name)
    name = companion_manifest(root).get("name")
    if not name:
        raise RuntimeError(f"companion {root} manifest is missing name")
    return str(name)


def plugin_version(root: Path) -> str | None:
    plugin_json = root / ".claude-plugin" / "plugin.json"
    if not plugin_json.is_file():
        return None
    return json.loads(plugin_json.read_text(encoding="utf-8")).get("version")


def content_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
        rel = path.relative_to(root)
        if any(part in {".git", "node_modules"} for part in rel.parts):
            continue
        if path.is_dir():
            continue
        rel_text = rel.as_posix()
        digest.update(rel_text.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized_text_sha256(path: Path) -> str:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def git_commit(ref: str) -> str:
    return git(REPO_ROOT, "rev-parse", f"{ref}^{{commit}}").stdout.strip()


def resolved_source(spec: str, *, companion: bool = False) -> str:
    if spec.startswith("dir:"):
        return "dir:" + content_hash(Path(spec[4:]).expanduser().resolve())
    if companion:
        ref, path = parse_companion_git_spec(spec)
        return "git-tree:" + git(REPO_ROOT, "rev-parse", f"{ref}:{path}").stdout.strip()
    return "git-commit:" + git_commit(spec[4:])


def arm_cache_digest(spec: str) -> str:
    ritus_spec, companion_spec = split_arm_spec(spec)
    digest = hashlib.sha256()
    digest.update(spec.encode("utf-8"))
    digest.update(b"\0ritus\0")
    digest.update(resolved_source(ritus_spec).encode("utf-8"))
    if companion_spec:
        digest.update(b"\0companion\0")
        digest.update(resolved_source(companion_spec, companion=True).encode("utf-8"))
    return digest.hexdigest()


def source_commit(spec: str) -> str | None:
    if spec.startswith("git:"):
        ref = parse_companion_git_spec(spec)[0] if ":" in spec[4:] else spec[4:]
        return git_commit(ref)
    return None


def plugin_provenance(root: Path, spec: str) -> dict:
    return {"spec": spec, "commit": source_commit(spec), "version": plugin_version(root),
            "tree_sha256": content_hash(root)}


def companion_root(ritus_copy: Path) -> Path | None:
    plugins_dir = Path(ritus_copy).parent
    if plugins_dir.name != "plugins":
        return None
    companions = [child for child in sorted(plugins_dir.iterdir())
                  if child.is_dir() and child.name != "ritus" and (child / "ritus-companion.json").is_file()]
    return companions[0] if companions else None


def build_arm_copy(name: str, spec: str, dest: Path):
    ritus_spec, companion_spec = split_arm_spec(spec)
    if companion_spec is None:
        build_source_copy(ritus_spec, dest)
        return
    plugins_dir = dest.parent
    if plugins_dir.name != "plugins":
        raise RuntimeError(f"composite arm {name} destination must be under a plugins directory")
    build_source_copy(ritus_spec, dest)
    with tempdir("companion-") as tmp:
        tmp_root = Path(tmp) / "companion"
        build_source_copy(companion_spec, tmp_root, companion=True)
        companion_manifest(tmp_root)
        companion_name = companion_plugin_name(tmp_root)
        companion_dest = plugins_dir / companion_name
        shutil.copytree(tmp_root, companion_dest)

def standards_line(iteration: int, arm: str) -> str:
    # Phase 2's old arm is the Phase 1 rewrite, whose task-files template carries Phase 1's new standards line.
    return STANDARDS_LINE["new_skill"] if phase(iteration) == 2 else STANDARDS_LINE[arm]


def run(cmd, cwd=None, env=None, check=True, timeout=300):
    proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout, shell=isinstance(cmd, str))
    if check and proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}): {cmd}\n{proc.stdout}\n{proc.stderr}")
    return proc


def git(repo, *args, env=None, check=True):
    return run(["git", *args], cwd=repo, env=env, check=check)


def is_junction(path: Path) -> bool:
    return bool(getattr(os.path, "isjunction", lambda _p: False)(path))


def unlink_junctions(path: Path):
    if not path.exists():
        return
    for root, dirs, _files in os.walk(path, topdown=True):
        keep = []
        for name in dirs:
            child = Path(root) / name
            if is_junction(child):
                child.rmdir()
            else:
                keep.append(name)
        dirs[:] = keep


def remove_tree_entry(path: Path):
    if is_junction(path):
        path.rmdir()
    elif path.is_dir():
        force_rmtree(path)
    elif path.exists():
        path.unlink()


def copy_tree_lf(src: Path, dest: Path, subst=None):
    for path in sorted(src.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(src)
        # Build output left in a fixture by running its scripts in place must never reach a world.
        if rel.parts[0] in SKIP_SNAPSHOT:
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        if subst:
            text = subst(text)
        target.write_text(text, encoding="utf-8", newline="\n")


def force_rmtree(path: Path):
    """rmtree that also removes git's read-only object files on Windows."""
    def retry_writable(func, target, _exc):
        os.chmod(target, 0o700)
        func(target)

    if Path(path).exists():
        unlink_junctions(Path(path))
        shutil.rmtree(path, onexc=retry_writable)


def clear_worktree(repo: Path):
    for child in repo.iterdir():
        if child.name == ".git":
            continue
        remove_tree_entry(child)


def web_package_dev_dependencies() -> dict:
    package = json.loads((WEB_BASE / "package.json").read_text(encoding="utf-8"))
    return package["devDependencies"]


def expected_web_versions() -> dict:
    deps = web_package_dev_dependencies()
    return {"playwright": deps["playwright"], "axe-core": deps["axe-core"]}


def installed_package_version(root: Path, package: str) -> str | None:
    package_json = root / "node_modules" / package / "package.json"
    if not package_json.is_file():
        return None
    return json.loads(package_json.read_text(encoding="utf-8")).get("version")


def web_modules_ready(root: Path) -> bool:
    expected = expected_web_versions()
    return (installed_package_version(root, "playwright") == expected["playwright"]
            and installed_package_version(root, "axe-core") == expected["axe-core"]
            and (root / "node_modules" / "axe-core" / "axe.min.js").is_file())


def web_modules_dir() -> Path:
    root = WEB_MODULES
    if not web_modules_ready(root):
        expected = ", ".join(f"{name}@{version}" for name, version in expected_web_versions().items())
        raise RuntimeError(f"{root} is missing web fixture tooling ({expected}); run build.py web-modules")
    return root


def install_web_modules(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    if web_modules_ready(root):
        print(f"{root} already has matching web modules")
        print(root)
        return
    package = {
        "name": "ritus-web-modules",
        "private": True,
        "devDependencies": web_package_dev_dependencies(),
    }
    (root / "package.json").write_text(json.dumps(package, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    run(["npm.cmd", "install"], cwd=root, check=True, timeout=900)
    run(["npx.cmd", "playwright", "install", "chromium"], cwd=root, check=True, timeout=900)
    print(root)


def command_version(cmd: list[str]) -> str | None:
    try:
        proc = run(cmd, check=False, timeout=30)
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return (proc.stdout or proc.stderr).strip().splitlines()[0] if (proc.stdout or proc.stderr).strip() else None


def fixture_guidance_path() -> Path:
    return FIXTURE_DIR / "web" / "design" / "figma-design-to-code" / "SKILL.md"


def write_environment_record(iteration: int, guidance_skill: Path, playwright_mcp: str, note: str) -> int:
    guidance = guidance_skill.expanduser().resolve()
    fixture_guidance = fixture_guidance_path()
    guidance_exists = guidance.is_file()
    matches_fixture = guidance_exists and normalized_text_sha256(guidance) == normalized_text_sha256(fixture_guidance)
    web_modules = WEB_MODULES.resolve()
    record = {
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": command_version([sys.executable, "--version"]),
        "node": command_version(["node", "--version"]),
        "web_modules": {
            "path": str(web_modules),
            "playwright": installed_package_version(web_modules, "playwright"),
            "axe-core": installed_package_version(web_modules, "axe-core"),
        },
        "guidance_skill": {
            "path": str(guidance),
            "sha256": file_sha256(guidance) if guidance_exists else None,
            "matches_fixture": matches_fixture,
        },
        "figma_stub": {
            "path": str(ROOT / "figma_stub.mjs"),
            "sha256": file_sha256(ROOT / "figma_stub.mjs"),
        },
        "playwright_mcp": playwright_mcp,
        "note": note,
    }
    out = WORKSPACE / f"iteration-{iteration}" / "environment.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(f"python: {record['python']}")
    print(f"node: {record['node']}")
    print("web modules: "
          f"playwright={record['web_modules']['playwright']} axe-core={record['web_modules']['axe-core']} "
          f"at {web_modules}")
    print(f"guidance: {guidance} sha256={record['guidance_skill']['sha256']} "
          f"matches_fixture={matches_fixture}")
    print(f"figma stub: {record['figma_stub']['path']} sha256={record['figma_stub']['sha256']}")
    print(f"playwright mcp: {playwright_mcp}")
    if note:
        print(f"note: {note}")
    if not guidance_exists:
        print(f"ERROR: guidance skill is missing: {guidance}", file=sys.stderr)
        return 1
    if not matches_fixture:
        print(f"ERROR: guidance skill does not match fixture guidance: {fixture_guidance}", file=sys.stderr)
        return 1
    return 0


def update_package_port(repo: Path, port: int | None):
    if port is None:
        return
    package_path = repo / "package.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    package["config"] = {**package.get("config", {}), "port": port}
    package_path.write_text(json.dumps(package, indent=2, ensure_ascii=True) + "\n", encoding="utf-8", newline="\n")


def create_node_modules_junction(repo: Path, modules_root: Path):
    target = modules_root / "node_modules"
    if not target.is_dir():
        raise RuntimeError(f"{target} is missing; run build.py web-modules")
    link = repo / "node_modules"
    if link.exists() or is_junction(link):
        remove_tree_entry(link)
    proc = run(["cmd", "/c", "mklink", "/J", str(link), str(target)], cwd=repo, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"failed to create node_modules junction\n{proc.stdout}\n{proc.stderr}")


def materialize(repo: Path, layers, spec: dict | None = None, dev_port: int | None = None):
    spec = spec or {}
    fixture = spec.get("fixture")
    base = WEB_BASE if fixture == "web" else BASE
    layer_root = WEB_LAYERS if fixture == "web" else LAYERS
    clear_worktree(repo)
    copy_tree_lf(base, repo)
    for layer in [*layers, *spec.get("world_layers", [])]:
        copy_tree_lf(layer_root / layer, repo)
    update_package_port(repo, dev_port)
    for rel in spec.get("drop", []):
        target = repo / rel
        if target.exists():
            target.unlink()
        parent = target.parent
        while parent != repo and parent.exists() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent


def dev_ports_file(workspace: Path) -> Path:
    return workspace / "dev-ports.json"


def read_dev_ports(workspace: Path) -> dict[str, str]:
    path = dev_ports_file(workspace)
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_dev_ports(workspace: Path, ports: dict[str, str]):
    path = dev_ports_file(workspace)
    if ports:
        path.write_text(json.dumps(dict(sorted(ports.items(), key=lambda item: int(item[0]))), indent=2) + "\n",
                        encoding="utf-8")
    elif path.exists():
        path.unlink()


def port_is_free(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def allocate_dev_port(workspace: Path, owner: str) -> int:
    workspace.mkdir(parents=True, exist_ok=True)
    ports = read_dev_ports(workspace)
    ports = {port: path for port, path in ports.items() if path != owner}
    held = {int(port) for port in ports}
    start = 41000 + (int(hashlib.sha256(owner.encode("utf-8")).hexdigest()[:8], 16) % 8000)
    for offset in range(8000):
        port = 41000 + ((start - 41000 + offset) % 8000)
        if port not in held and port_is_free(port):
            ports[str(port)] = owner
            write_dev_ports(workspace, ports)
            return port
    raise RuntimeError("no free web dev port in 41000-48999")


def release_dev_ports(workspace: Path, owners):
    owner_set = {str(owner) for owner in owners}
    ports = {port: owner for port, owner in read_dev_ports(workspace).items() if owner not in owner_set}
    write_dev_ports(workspace, ports)


def commit_env(days: float, author: str, now: datetime):
    name, email = AUTHORS[author]
    stamp = (now - timedelta(days=days)).replace(hour=10, minute=12, second=0, microsecond=0)
    date = stamp.strftime("%Y-%m-%dT%H:%M:%S")
    env = dict(os.environ)
    env.update(GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=email, GIT_COMMITTER_NAME=name, GIT_COMMITTER_EMAIL=email,
               GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    return env


def make_subst(now: datetime, extra: dict):
    def ts(match):
        days, hh, mm = int(match.group(1)), int(match.group(2)), int(match.group(3))
        return (now - timedelta(days=days)).replace(hour=hh, minute=mm).strftime("%Y-%m-%d %H:%M")

    def date(match):
        return (now - timedelta(days=int(match.group(1)))).strftime("%Y-%m-%d")

    def ago(match):
        return (now - timedelta(minutes=int(match.group(1)))).strftime("%Y-%m-%d %H:%M")

    def subst(text: str) -> str:
        text = re.sub(r"\{\{ts:(\d+):(\d\d):(\d\d)\}\}", ts, text)
        text = re.sub(r"\{\{date:(\d+)\}\}", date, text)
        text = re.sub(r"\{\{ago:(\d+)\}\}", ago, text)
        for key, value in extra.items():
            text = text.replace("{{" + key + "}}", str(value))
        return text

    return subst


def snapshot(repo: Path) -> dict:
    files = {}
    for root, dirs, names in os.walk(repo):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_SNAPSHOT)
        for name in sorted(names):
            path = Path(root) / name
            rel = path.relative_to(repo)
            if rel.parts[0] in SKIP_SNAPSHOT:
                continue
            files[rel.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def tree_text(repo: Path) -> dict:
    return {rel: (repo / rel).read_text(encoding="utf-8", errors="replace") for rel in snapshot(repo)}


def git_tree_text(repo: Path, ref: str, prefixes: tuple[str, ...]) -> dict:
    proc = git(repo, "ls-tree", "-r", "--name-only", ref, "--", *prefixes)
    files = {}
    for rel in proc.stdout.splitlines():
        if rel:
            files[rel] = git(repo, "show", f"{ref}:{rel}").stdout
    return files


def write_tree(dest: Path, files: dict):
    for rel, text in files.items():
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")


def agent_diff(setup_files: dict, repo: Path) -> str:
    """Diff from the state the agent was handed to the state it left, tracked or not (build outputs excluded)."""
    with tempdir("tl-diff-") as tmp:
        write_tree(Path(tmp) / "before", setup_files)
        write_tree(Path(tmp) / "after", tree_text(repo))
        (Path(tmp) / "before").mkdir(exist_ok=True)
        (Path(tmp) / "after").mkdir(exist_ok=True)
        out = run(["git", "diff", "--no-index", "--no-color", "before", "after"], cwd=tmp, check=False).stdout
    return out.replace("a/before/", "a/").replace("b/after/", "b/")


def parse_test_output(text: str) -> dict:
    out = {}
    for key in ("tests", "pass", "fail"):
        match = re.search(rf"^\S*\s*{key} (\d+)\s*$", text, re.M)
        out[key] = int(match.group(1)) if match else None
    return out


def run_checks(repo: Path, test_args=()) -> dict:
    """Run build/test/lint in a throwaway copy of the repo so the run's own evidence files stay untouched.

    A web world's `node_modules` is a junction to the shared install. The copy gets its own junction to that install,
    so tests that use the project's declared devDependencies (Playwright, axe-core) resolve them there as well.
    """
    with tempdir("tl-check-") as tmp:
        copy = Path(tmp) / "repo"
        shutil.copytree(repo, copy, ignore=shutil.ignore_patterns(".git", ".cache", "dist", "node_modules"))
        modules = repo / "node_modules"
        if is_junction(modules):
            create_node_modules_junction(copy, Path(os.path.realpath(modules)).parent)
        try:
            result = {}
            for name, cmd in (("build", "node scripts/build.mjs"),
                              ("test", "node scripts/test.mjs " + " ".join(test_args)),
                              ("lint", "node scripts/lint.mjs")):
                proc = run(cmd, cwd=copy, check=False, timeout=600)
                entry = {"code": proc.returncode, "tail": (proc.stdout + proc.stderr)[-1500:]}
                if name == "test":
                    entry.update(parse_test_output(proc.stdout))
                result[name] = entry
            return result
        finally:
            # Unlink before the temp dir is deleted, so the deletion can never reach the shared install.
            unlink_junctions(copy)


def powershell_json(script: str):
    proc = run(["powershell", "-NoProfile", "-Command", script], check=False, timeout=120)
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def listener_rows() -> list[dict]:
    script = ("Get-NetTCPConnection -State Listen | "
              "Select-Object LocalAddress,LocalPort,OwningProcess | ConvertTo-Json -Compress")
    data = powershell_json(script)
    if data is None:
        return []
    return data if isinstance(data, list) else [data]


def process_facts(pids) -> dict[int, dict]:
    ids = sorted({int(pid) for pid in pids if pid})
    if not ids:
        return {}
    joined = ",".join(str(pid) for pid in ids)
    script = (
        f"$ids=@({joined}); $out=@(); foreach ($id in $ids) {{ "
        "$p=Get-CimInstance Win32_Process -Filter \"ProcessId = $id\"; "
        "if ($p) { $out += [pscustomobject]@{pid=[int]$p.ProcessId; name=$p.Name; "
        "command_line=$p.CommandLine; started_at=$p.CreationDate.ToString('o')} } }; "
        "$out | ConvertTo-Json -Compress"
    )
    data = powershell_json(script)
    if data is None:
        return {}
    rows = data if isinstance(data, list) else [data]
    return {int(row["pid"]): row for row in rows if row.get("pid") is not None}


def stop_pid(pid: int):
    run(["powershell", "-NoProfile", "-Command", f"Stop-Process -Id {int(pid)} -Force"], check=False, timeout=30)


def stopped_entry(pid: int, port: int, how: str, facts: dict) -> dict:
    return {"pid": pid, "port": port, "how": how, "name": facts.get("name"),
            "command_line": (facts.get("command_line") or "")[:200], "started_at": facts.get("started_at")}


def iso_to_timestamp(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def stop_dev_servers(setup: dict) -> list[dict]:
    repo = Path(setup["repo"])
    dev_port = setup.get("dev_port")
    pidfile = repo / ".cache" / "dev-server.pids"
    listeners = listener_rows()
    by_pid_port = {(int(row.get("OwningProcess")), int(row.get("LocalPort"))) for row in listeners
                   if row.get("OwningProcess") is not None and row.get("LocalPort") is not None}
    stopped = []
    pidfile_pairs = []
    if pidfile.is_file():
        for line in pidfile.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                pidfile_pairs.append((int(parts[0]), int(parts[1])))
    facts = process_facts([pid for pid, _port in pidfile_pairs] + [row.get("OwningProcess") for row in listeners])
    covered = set()
    for pid, port in pidfile_pairs:
        if (pid, port) in by_pid_port:
            stop_pid(pid)
            stopped.append(stopped_entry(pid, port, "pidfile", facts.get(pid, {})))
            covered.add(pid)
        else:
            print(f"skip dev server pidfile pid={pid} port={port}: pid is not listening on that port",
                  file=sys.stderr)
    if dev_port is not None:
        for row in listeners:
            pid, port = int(row.get("OwningProcess") or 0), int(row.get("LocalPort") or 0)
            if port != int(dev_port) or pid in covered:
                continue
            started = iso_to_timestamp((facts.get(pid) or {}).get("started_at"))
            if started is not None and started >= float(setup["built_at"]):
                stop_pid(pid)
                stopped.append(stopped_entry(pid, port, "listener", facts.get(pid, {})))
            else:
                print(f"skip listener pid={pid} port={port}: started before this run was built", file=sys.stderr)
    return stopped


def command_session_names(command: str) -> set[str]:
    if not re.search(r"(?:playwright(?:\.cmd)?\s+cli|playwright-cli)", command, re.I):
        return set()
    names = set()
    for pattern in (r"(?:^|\s)(?:-s|--session)=([^\s]+)", r"(?:^|\s)(?:-s|--session)\s+([^\s]+)"):
        for match in re.finditer(pattern, command):
            names.add(match.group(1).strip("\"'"))
    return names or {"default"}


def close_browser_sessions(setup: dict, commands: list[str]) -> list[dict]:
    repo = Path(setup["repo"])
    out = []
    for session in sorted({name for command in commands for name in command_session_names(command)}):
        proc = run(["npx.cmd", "playwright", "cli", f"-s={session}", "close"], cwd=repo, check=False, timeout=120)
        out.append({"session": session, "exit_code": proc.returncode, "output": (proc.stdout + proc.stderr)[-1500:]})
    return out


def run_tree_commands(setup: dict, events) -> list[str]:
    if events is None:
        return []
    name = Path(setup["agent_root"]).name
    agent = None
    for attempt in [name, f"{name}-r", *(f"{name}-r{i}" for i in range(2, 10))]:
        agent = events.by_name(attempt) or agent
    if not agent:
        return []
    commands = []
    for node in events.tree(agent["id"]):
        commands.extend(events.commands(node["id"]))
    return commands


def cleanup_web_run(setup: dict, events=None) -> dict:
    if setup.get("fixture") != "web":
        return {}
    commands = run_tree_commands(setup, events)
    return {"dev_servers_stopped": stop_dev_servers(setup),
            "browser_sessions_closed": close_browser_sessions(setup, commands)}


def plugin_copies(iteration: int, arm_names: list[str] | None = None, stub: Path | None = None) -> dict:
    """Build each arm into a private workspace dir; reuse the copies on later builds.

    A stub helper (the iteration's `STUB_HELPER`, else the `stub` a scenario asks for) replaces the copy's
    `scripts/remote-api.ts`; a stubbed copy is kept apart from the arm's plain copy.
    """
    arms = arm_names or ARMS
    stub = STUB_HELPER.get(iteration, stub)
    suffix = f"+{stub.stem}" if stub else ""
    index = WORKSPACE / f"iteration-{iteration}" / "plugins.json"
    known = {key: Path(p) for key, p in json.loads(index.read_text(encoding="utf-8")).items()} if index.exists() else {}
    paths = {}
    for arm in arms:
        if arm not in ARM_SPECS:
            raise RuntimeError(f"no --arm spec for {arm!r}")
        spec = ARM_SPECS[arm]
        key = f"{arm}|{arm_cache_digest(spec)}{suffix}"
        if key in known and known[key].is_dir():
            paths[arm] = known[key]
            continue
        if split_arm_spec(spec)[1] is None:
            dest = AGENT_TMP / f"rp-{secrets.token_hex(3)}" / "ritus"
        else:
            dest = AGENT_TMP / f"rp-{secrets.token_hex(3)}" / "plugins" / "ritus"
        build_arm_copy(arm, spec, dest)
        if stub:
            shutil.copyfile(stub, dest / "scripts" / "remote-api.ts")
        known[key] = paths[arm] = dest
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(json.dumps({key: str(p) for key, p in known.items()}, indent=2), encoding="utf-8")
    return paths


def extract_hook_context(stdout: str) -> str:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"companion hook printed invalid JSON: {exc}") from exc
    context = data.get("additionalContext")
    if not context and isinstance(data.get("hookSpecificOutput"), dict):
        context = data["hookSpecificOutput"].get("additionalContext")
    if not context:
        raise RuntimeError("companion hook output did not include additionalContext")
    return context


def run_companion_hook(ritus_copy: Path, repo: Path) -> str | None:
    companion = companion_root(ritus_copy)
    if companion is None:
        return None
    env = dict(os.environ)
    env["CLAUDE_PLUGIN_ROOT"] = str(ritus_copy)
    env["CLAUDE_PROJECT_DIR"] = str(repo)
    env.pop("COPILOT_CLI", None)
    proc = subprocess.run(["node", str(ritus_copy / "scripts" / "companion-bootstrap.ts")], cwd=repo, env=env,
                          input=json.dumps({"cwd": str(repo)}), capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=60)
    if proc.returncode != 0:
        raise RuntimeError(f"companion hook failed ({proc.returncode})\n{proc.stdout}\n{proc.stderr}")
    if not proc.stdout.strip():
        raise RuntimeError("companion hook printed nothing")
    context = extract_hook_context(proc.stdout.strip())
    expected = norm_path(companion / "ritus-companion.json")
    manifests = {norm_path(match) for match in re.findall(r"[A-Za-z]:[^\n`]*?ritus-companion\.json", context)}
    if manifests != {expected}:
        raise RuntimeError(f"companion hook registry named unexpected manifests: {sorted(manifests)}; expected {expected}")
    return context


def norm_path(path: str | Path) -> str:
    return str(path).replace("/", "\\").lower().rstrip("\\.")


def companion_prompt_parts(ritus_copy: Path, web: bool, registry: str | None = None) -> dict:
    companion = companion_root(ritus_copy)
    design = f"\n{DESIGN_SKILL_SENTENCE}\n" if web else ""
    if companion is None:
        return {"companion_worker_context": "", "companion_main_context": "", "worker_companion_clause": "",
                "main_companion_clause": "", "session_start_registry": "", "design_skill_context": design}
    worker = (f"\nCompanion plugin root: {companion}\n"
              "You may read the companion root when the inputs name a companion skill.\n")
    main = (f"\nCompanion plugin root: {companion}\n"
            "You may read the companion root like the Ritus plugin root for companion manifests and skills.\n")
    registry_block = ""
    if registry:
        registry_block = ("\nAt session start, an installed plugin's hook injected this companion registry verbatim:\n\n"
                          f"{registry}\n\n")
    return {"companion_worker_context": worker, "companion_main_context": main,
            "worker_companion_clause": ", the companion plugin root,", "main_companion_clause": ", the companion plugin root,",
            "session_start_registry": registry_block, "design_skill_context": design}



def build_run(eval_name: str, arm: str, run_idx: int, iteration: int, now: datetime, plugins: dict) -> Path:
    spec = SCENARIOS[eval_name]
    run_dir = WORKSPACE / f"iteration-{iteration}" / eval_name / arm / f"run-{run_idx}"
    if run_dir.exists():
        old = run_dir / "setup.json"
        if old.exists():
            old_setup = json.loads(old.read_text(encoding="utf-8"))
            release_dev_ports(WORKSPACE, [old_setup["agent_root"]])
            force_rmtree(old_setup["agent_root"])
        shutil.rmtree(run_dir)
    (run_dir / "outputs").mkdir(parents=True)
    agent_root = AGENT_TMP / f"tl-{secrets.token_hex(3)}"
    web = spec.get("fixture") == "web"
    dev_port = allocate_dev_port(WORKSPACE, str(agent_root)) if web else None
    web_modules = web_modules_dir() if web else None
    repo_name = "tinyledger-web" if web else "tinyledger"
    repo, origin, outputs = agent_root / repo_name, agent_root / "origin.git", agent_root / "out"
    repo.mkdir(parents=True)
    outputs.mkdir()

    git(repo, "init", "-q", "-b", "main")
    for key, value in (("core.autocrlf", "false"), ("user.name", "Dev"), ("user.email", "dev@example.com"),
                       ("commit.gpgsign", "false")):
        git(repo, "config", key, value)
    for commit_id in spec["main"]:
        commit = COMMITS[commit_id]
        materialize(repo, commit["layers"], spec, dev_port)
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", commit["msg"], env=commit_env(commit["days"], commit["author"], now))
    git(repo, "init", "-q", "--bare", str(origin))
    git(repo, "remote", "add", "origin", str(origin))
    git(repo, "push", "-q", "-u", "origin", "main")
    if spec["branch"] != "main":
        git(repo, "checkout", "-q", "-b", spec["branch"])
    for commit in spec["branch_commits"]:
        materialize(repo, commit["layers"], spec, dev_port)
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", commit["msg"], env=commit_env(commit["days"], commit["author"], now))
    if spec["push_branch"]:
        git(repo, "push", "-q", "-u", "origin", spec["branch"])
    if spec.get("remote_url"):
        # What the developer's clone would show; the local bare remote keeps the origin/* refs it already pushed.
        git(repo, "remote", "set-url", "origin", spec["remote_url"])
    if spec["worktree"] is not None:
        materialize(repo, spec["worktree"], spec, dev_port)

    checks = run_checks(repo)
    companion = companion_root(plugins[arm])
    registry = run_companion_hook(plugins[arm], repo)
    extra = {"TESTS_PASS": checks["test"].get("pass"), "TESTS_TOTAL": checks["test"].get("tests"),
             "REPO": str(repo), "OUTPUTS": str(outputs), "STANDARDS_LINE": standards_line(iteration, arm),
             "COMPANION": str(companion) if companion else ""}
    subst = make_subst(now, extra)
    scen = SCENARIOS_DIR / spec["key"]
    doc_sets = spec.get("doc_sets", [])
    if isinstance(doc_sets, dict):
        doc_sets = doc_sets.get(arm, [])
    for doc_set in [*doc_sets, spec["key"]]:
        for part in ("common", arm):
            docs = SCENARIOS_DIR / doc_set / part / "repo"
            if docs.is_dir():
                copy_tree_lf(docs, repo, subst)
                update_package_port(repo, dev_port)
    if web:
        create_node_modules_junction(repo, web_modules)

    if spec.get("mode") == "main":
        meta = json.loads((scen / "eval.json").read_text(encoding="utf-8"))
        message_file = scen / "message.md"
        message = subst(message_file.read_text(encoding="utf-8").replace("\r\n", "\n")).strip() \
            if message_file.exists() else ""
        block = f"\nThe developer's message:\n\n```text\n{message}\n```\n" if message else ""
        prompt_parts = companion_prompt_parts(plugins[arm], web, registry)
        prompt = MAIN_PROMPT_TEMPLATE.format(plugin=plugins[arm], skills=skill_catalog(plugins[arm], companion),
                                             repo=repo, branch=spec["branch"], outputs=outputs,
                                             invocation=meta["invocation"], message=block, **prompt_parts)
    else:
        inputs_file = scen / arm / "inputs.md" if (scen / arm / "inputs.md").exists() else scen / "inputs.md"
        inputs = subst(inputs_file.read_text(encoding="utf-8").replace("\r\n", "\n")).strip()
        prompt_parts = companion_prompt_parts(plugins[arm], web, registry)
        prompt = PROMPT_TEMPLATE.format(plugin=plugins[arm], skill=spec["skill"], repo=repo, branch=spec["branch"],
                                        inputs=inputs, outputs=outputs, **prompt_parts)
    (run_dir / "prompt.md").write_text(prompt, encoding="utf-8", newline="\n")
    (agent_root / "brief.md").write_text(prompt, encoding="utf-8", newline="\n")
    kickoff = (f"Read {agent_root / 'brief.md'}: it sets up a practice session on a test repository and it is your "
               f"whole task: nothing else you may know about other sessions or projects is part of it. Follow it "
               f"exactly."
               if spec.get("mode") == "main" else
               f"Read {agent_root / 'brief.md'} and follow it exactly. It is your whole task.")

    head = git(repo, "rev-parse", "HEAD").stdout.strip()
    status = git(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout
    ritus_spec, companion_spec = split_arm_spec(ARM_SPECS[arm])
    setup = {"eval": eval_name, "arm": arm, "run": run_idx, "built_at": time.time(),
             "built_at_iso": datetime.now().isoformat(timespec="seconds"), "agent_root": str(agent_root),
             "repo": str(repo), "agent_outputs": str(outputs), "plugin": str(plugins[arm]), "kickoff": kickoff,
             "head": head, "arm_spec": ARM_SPECS[arm], "ritus": plugin_provenance(plugins[arm], ritus_spec),
             "companion": ({**plugin_provenance(companion, companion_spec), "path": str(companion)}
                           if companion and companion_spec else None),
             "branch": spec["branch"], "status": status, "snapshot": snapshot(repo), "files": tree_text(repo),
             "baseline_checks": checks}
    if web:
        setup.update({"fixture": "web", "web_modules": str(web_modules), "dev_port": dev_port})
    (run_dir / "setup.json").write_text(json.dumps(setup, indent=2, ensure_ascii=True), encoding="utf-8")
    metadata = {"eval_id": int(eval_name.split("-")[1]), "eval_name": eval_name, "prompt": prompt, "assertions": []}
    (run_dir / "eval_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=True), encoding="utf-8")
    return run_dir


# ---------------------------------------------------------------- collect


BEHAVIOR_SCRIPTS = {
    "e1": r"""
import { renderReceipt } from './src/receipt.js';
const r = { id: 'R-1001', fromId: 'alice', toId: 'bob', amountCents: 1250, feeCents: 13 };
const out = {};
for (const [name, fn] of Object.entries({
  usd: () => renderReceipt(r),
  eur: () => renderReceipt(r, 'EUR'),
  zero: () => renderReceipt({ ...r, feeCents: 0 }),
})) {
  try { out[name] = fn(); } catch (e) { out[name] = 'THROWS: ' + e.message; }
}
console.log(JSON.stringify(out));
""",
    "e7": r"""
import { computeFee } from './src/fees.js';
import { transfer } from './src/transfer.js';
import { withdraw } from './src/withdraw.js';
import { tempLedger } from './test/helpers.js';
const out = {};
const safe = async (name, fn) => { try { out[name] = await fn(); } catch (e) { out[name] = 'THROWS: ' + e.message; } };
await safe('fee_transfer_1050', () => computeFee(1050, 'transfer'));
await safe('fee_withdraw_5025', () => computeFee(5025, 'withdraw'));
await safe('fee_transfer_1049', () => computeFee(1049, 'transfer'));
await safe('fee_withdraw_1000', () => computeFee(1000, 'withdraw'));
await safe('transfer_1050', async () => {
  const { ledger, cleanup } = await tempLedger();
  try { return (await transfer(ledger, 'alice', 'bob', 1050)).feeCents; } finally { await cleanup(); }
});
await safe('withdraw_5025_balance', async () => {
  const { ledger, cleanup } = await tempLedger();
  try { return await withdraw(ledger, 'alice', 5025); } finally { await cleanup(); }
});
console.log(JSON.stringify(out));
""",
}

E7_TRANSFER_ONLY_FIX = """\
// Mutation M2: half-up only for transfer; withdraw keeps the floor bug.
const SCHEDULE = {
  transfer: { rateBps: 100, minCents: 0 },
  withdraw: { rateBps: 200, minCents: 25 },
};

export const FEE_RATES_BPS = Object.fromEntries(Object.entries(SCHEDULE).map(([kind, rule]) => [kind, rule.rateBps]));
export const MIN_FEE_CENTS = Object.fromEntries(Object.entries(SCHEDULE).map(([kind, rule]) => [kind, rule.minCents]));

export function computeFee(amountCents, kind) {
  const rule = Object.hasOwn(SCHEDULE, kind) ? SCHEDULE[kind] : undefined;
  if (!rule) {
    throw new RangeError(`Unknown fee kind: ${kind}`);
  }
  if (!Number.isInteger(amountCents) || amountCents <= 0) {
    throw new RangeError(`amountCents must be a positive integer, got ${amountCents}`);
  }
  const offset = kind === 'transfer' ? 5000 : 0;
  return Math.max(Math.floor((amountCents * rule.rateBps + offset) / 10000), rule.minCents);
}
"""


def node_eval(repo: Path, script: str) -> dict:
    with tempdir("tl-behave-") as tmp:
        copy = Path(tmp) / "repo"
        shutil.copytree(repo, copy, ignore=shutil.ignore_patterns(".git", ".cache", "dist", "node_modules"))
        (copy / "behave.mjs").write_text(script, encoding="utf-8")
        proc = run(["node", "behave.mjs"], cwd=copy, check=False, timeout=120)
        try:
            return json.loads(proc.stdout.strip().splitlines()[-1])
        except (IndexError, json.JSONDecodeError):
            return {"error": (proc.stdout + proc.stderr)[-1500:]}



def free_ui_port() -> int:
    for port in range(39000, 41000):
        if port_is_free(port):
            return port
    raise RuntimeError("no free UI port in 39000-40999")


def wait_http_ok(url: str, timeout_seconds: float = 20) -> bool:
    import urllib.request
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return True
        except OSError:
            time.sleep(0.2)
    return False


def ui_eval(repo: Path, web_modules: Path, checks: list[str]) -> dict:
    with tempdir("tl-ui-") as tmp:
        copy = Path(tmp) / "repo"
        shutil.copytree(repo, copy, ignore=shutil.ignore_patterns(*SKIP_SNAPSHOT))
        port = free_ui_port()
        log_path = Path(tmp) / "ui-server.log"
        log_file = log_path.open("w", encoding="utf-8", errors="replace")
        proc = subprocess.Popen(["node", "scripts/serve.mjs", "--port", str(port)], cwd=copy,
                                stdout=log_file, stderr=subprocess.STDOUT, text=True,
                                encoding="utf-8", errors="replace")
        try:
            if not wait_http_ok(f"http://localhost:{port}/accounts", 20):
                log_file.flush()
                output = log_path.read_text(encoding="utf-8", errors="replace")[-1500:]
                return {"error": "app did not start", "output": output}
            request = {"baseUrl": f"http://localhost:{port}", "checks": checks}
            request_path = Path(tmp) / "ui-input.json"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            modules = web_modules / "node_modules" if (web_modules / "node_modules").is_dir() else web_modules
            env = dict(os.environ, UI_MODULES=str(modules))
            proc_measure = run(["node", str(ROOT / "ui_measure.mjs"), str(request_path)], cwd=copy, env=env,
                               check=False, timeout=90)
            text = proc_measure.stdout + proc_measure.stderr
            try:
                data = json.loads(proc_measure.stdout.strip().splitlines()[-1])
            except (IndexError, json.JSONDecodeError):
                data = {"error": "ui_measure failed", "output": text[-1500:]}
            if proc_measure.returncode != 0 and "error" not in data:
                data = {"error": "ui_measure failed", "output": text[-1500:]}
            return data
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=10)
            try:
                log_file.close()
            except OSError:
                pass


def _num(value) -> float | None:
    if value is None:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    return float(match.group(0)) if match else None


def _hex_color(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if value.startswith("#"):
        raw = value[1:]
        if len(raw) == 3:
            raw = "".join(ch * 2 for ch in raw)
        return "#" + raw[:6].upper()
    match = re.match(r"rgba?\(([^)]+)\)", value)
    if not match:
        return value.upper()
    parts = [part.strip() for part in match.group(1).split(",")]
    try:
        return "#" + "".join(f"{int(float(part)):02X}" for part in parts[:3])
    except ValueError:
        return value.upper()


def _near(value, expected, tolerance) -> bool:
    return value is not None and abs(float(value) - expected) <= tolerance


UI_WIDTHS = (375, 768, 1280)
UI_ROUTES = ("/accounts", "/accounts/checking", "/accounts/travel", "/transfer")


def _width_data(mapping: dict, width: int):
    return mapping.get(width, mapping.get(str(width))) if isinstance(mapping, dict) else None


def _measurement_error(data) -> str | None:
    if data is None:
        return "measurement missing"
    if isinstance(data, dict) and data.get("error"):
        return str(data["error"])
    return None


def _all_widths(measurements: dict, key: str) -> list[tuple[str, dict]]:
    by_width = measurements.get(key) or {}
    return [(str(width), _width_data(by_width, width) or {}) for width in UI_WIDTHS]


def _changed_lines(setup_files: dict | None, final_files: dict | None, rel: str) -> list[str]:
    return [line for _line_no, line in _changed_line_entries(setup_files, final_files, rel)]


def _changed_line_entries(setup_files: dict | None, final_files: dict | None, rel: str) -> list[tuple[int, str]]:
    if final_files is None or rel not in final_files:
        return []
    before = (setup_files or {}).get(rel)
    after = final_files[rel]
    if before == after:
        return []
    if before is None:
        return list(enumerate(after.splitlines(), 1))
    import difflib
    out = []
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    for tag, _i1, _i2, j1, j2 in difflib.SequenceMatcher(None, before_lines, after_lines).get_opcodes():
        if tag in ("insert", "replace"):
            out.extend((line_no, after_lines[line_no - 1]) for line_no in range(j1 + 1, j2 + 1))
    return out


def _imports_card_and_calls(source: str) -> bool:
    import_line = re.compile(r"^\s*import\s+(.+?)\s+from\s+['\"]([^'\"]*components/card\.js)['\"]\s*;?\s*$", re.M)
    for match in import_line.finditer(source):
        clause = match.group(1).strip()
        names: list[tuple[str, str]] = []
        ns = re.search(r"\*\s+as\s+(\w+)", clause)
        if ns:
            names.append((ns.group(1), "namespace"))
        named = re.search(r"\{([^}]+)\}", clause)
        if named:
            for part in named.group(1).split(","):
                bits = part.strip().split()
                if not bits:
                    continue
                if bits[0] == "card":
                    names.append((bits[-1] if len(bits) >= 3 and bits[-2] == "as" else "card", "binding"))
        elif clause and not clause.startswith("{") and not clause.startswith("*"):
            names.append((clause.split(",", 1)[0].strip(), "binding"))
        body = source[:match.start()] + source[match.end():]
        for name, kind in names:
            if kind == "namespace" and re.search(rf"\b{re.escape(name)}\.card\s*\(", body):
                return True
            if kind == "binding" and re.search(rf"\b{re.escape(name)}\s*\(", body):
                return True
    return False


def ui_verdicts(measurements: dict, setup_files: dict | None, final_files: dict | None) -> dict[str, tuple[bool, str]]:
    verdicts: dict[str, tuple[bool, str]] = {}
    routes_expected = {"/accounts": "Accounts", "/accounts/checking": "Checking", "/accounts/travel": "Travel fund", "/transfer": "Transfer"}
    failures = []
    for route, h1 in routes_expected.items():
        by_width = (measurements.get("routes") or {}).get(route, {})
        for width in UI_WIDTHS:
            data = _width_data(by_width, width)
            error = _measurement_error(data)
            if error:
                failures.append(f"{route}@{width} expected 200/{h1!r}, observed error: {error}")
            elif data.get("status") != 200 or data.get("h1") != h1:
                failures.append(f"{route}@{width} expected 200/{h1!r}, observed {data.get('status')}/{data.get('h1')!r}")
    verdicts["routes_ok"] = (not failures, "; ".join(failures[:2]) if failures else "all routes returned 200 with expected h1")

    over = []
    for route in UI_ROUTES:
        by_width = (measurements.get("overflow") or {}).get(route, {})
        for width in UI_WIDTHS:
            value = _width_data(by_width, width)
            error = _measurement_error(value)
            if error:
                over.append(f"{route}@{width} expected overflow <= 0, observed error: {error}")
            elif value > 0:
                over.append(f"{route}@{width} expected overflow <= 0, observed {value}")
    verdicts["no_overflow"] = (not over, "; ".join(over[:2]) if over else "overflow <= 0 at every route and width")

    axe = []
    for route in UI_ROUTES:
        by_width = (measurements.get("axe") or {}).get(route, {})
        for width in UI_WIDTHS:
            violations = _width_data(by_width, width)
            error = _measurement_error(violations)
            if error:
                axe.append(f"{route}@{width} expected 0 axe violations, observed error: {error}")
            elif violations:
                axe.append(f"{route}@{width} expected 0 axe violations, observed {len(violations)} ({violations[0].get('id')})")
    verdicts["axe_clean"] = (not axe, "; ".join(axe[:2]) if axe else "zero axe violations at every route and width")

    logs = []
    for route in UI_ROUTES:
        by_width = (measurements.get("console") or {}).get(route, {})
        for width in UI_WIDTHS:
            messages = _width_data(by_width, width)
            error = _measurement_error(messages)
            if error:
                logs.append(f"{route}@{width} expected no console/page/400 errors, observed error: {error}")
            elif messages is None:
                logs.append(f"{route}@{width} expected no console/page/400 errors, observed missing measurement")
            elif messages:
                first = messages[0]
                logs.append(f"{route}@{width} expected no console/page/400 errors, observed {first}")
    verdicts["console_clean"] = (not logs, "; ".join(logs[:2]) if logs else "no console errors, pageerrors, or >=400 responses")

    card_missing = []
    geom = []
    colors = []
    type_fail = []
    total_fail = []
    full_fail = []
    signature_fail = []
    for width, card in _all_widths(measurements, "summary_card"):
        if not card.get("found"):
            reason = card.get("reason", "card target missing")
            card_missing.append(f"{width}: {reason}")
            continue
        if card.get("label_value_same_block"):
            geom.append(f"{width}: label and value share one block")
        for key, expected in (("top", 16), ("left", 16), ("bottom", 16)):
            observed = (card.get("insets") or {}).get(key)
            if not _near(observed, expected, 1):
                geom.append(f"{width}: {key} inset expected {expected}±1, observed {observed}")
        observed_gap = card.get("gap")
        if not _near(observed_gap, 16, 1):
            geom.append(f"{width}: gap expected 16±1, observed {observed_gap}")
        intrusion = (card.get("insets") or {}).get("right_intrusion")
        if intrusion is None or intrusion > 1:
            geom.append(f"{width}: right intrusion expected <=1, observed {intrusion}")
        radii = [_num(value) for value in card.get("radius", [])]
        if len(radii) != 4 or any(not _near(value, 8, 0.5) for value in radii):
            geom.append(f"{width}: radii expected 8±0.5, observed {radii}")
        if _hex_color(card.get("background")) != "#FFFFFF":
            colors.append(f"{width}: background expected #FFFFFF, observed {_hex_color(card.get('background'))}")
        for side, border in zip(["top", "right", "bottom", "left"], card.get("borders", [])):
            if border.get("style") != "solid" or not _near(_num(border.get("width")), 1, 0.5) or _hex_color(border.get("color")) != "#D0D7DE":
                colors.append(f"{width}: {side} border expected 1px solid #D0D7DE, observed {border}")
        label_style = card.get("label_style") or {}
        value_style = card.get("value_style") or {}
        if _hex_color(label_style.get("color")) != "#57606A":
            colors.append(f"{width}: label color expected #57606A, observed {_hex_color(label_style.get('color'))}")
        if _hex_color(value_style.get("color")) != "#1F2328":
            colors.append(f"{width}: value color expected #1F2328, observed {_hex_color(value_style.get('color'))}")
        if not (_near(_num(label_style.get("fontSize")), 14, 0.1) and _near(_num(label_style.get("lineHeight")), 20, 0.1) and str(label_style.get("fontWeight")) == "400"):
            type_fail.append(f"{width}: label type expected 14/20/400, observed {label_style}")
        if not (_near(_num(value_style.get("fontSize")), 24, 0.1) and _near(_num(value_style.get("lineHeight")), 32, 0.1) and str(value_style.get("fontWeight")) == "600"):
            type_fail.append(f"{width}: value type expected 24/32/600, observed {value_style}")
        if card.get("value_text") != "$12,345.67":
            total_fail.append(f"{width}: total expected $12,345.67, observed {card.get('value_text')}")
        left = abs((card.get("container_edges") or {}).get("left", 99999) - (card.get("content_column") or {}).get("left", 0))
        right = abs((card.get("container_edges") or {}).get("right", 99999) - (card.get("content_column") or {}).get("right", 0))
        if left > 1 or right > 1:
            full_fail.append(f"{width}: edges expected within 1px of content column, observed left {left:.2f}, right {right:.2f}")
        if not card.get("component_signature"):
            signature_fail.append(f"{width}: expected summary container or ancestor to carry data-ui-probe-card, observed false")
    if card_missing:
        geom = geom or card_missing
        colors = colors or card_missing
        type_fail = type_fail or card_missing
        total_fail = total_fail or card_missing
        full_fail = full_fail or card_missing
        signature_fail = signature_fail or card_missing
    verdicts["card_geometry"] = (not geom, "; ".join(geom[:2]) if geom else "summary card geometry matches design")
    verdicts["card_colors"] = (not colors, "; ".join(colors[:2]) if colors else "summary card colors match design")
    verdicts["card_type"] = (not type_fail, "; ".join(type_fail[:2]) if type_fail else "summary card typography matches design")
    verdicts["card_total"] = (not total_fail, "; ".join(total_fail[:2]) if total_fail else "summary total is $12,345.67")
    verdicts["card_full_width"] = (not full_fail, "; ".join(full_fail[:2]) if full_fail else "summary card fills the content column")
    reuse_source = False
    if final_files is not None:
        for rel, source in final_files.items():
            if rel.startswith("src/") and rel != "src/components/card.js" and source != (setup_files or {}).get(rel):
                if _imports_card_and_calls(source):
                    reuse_source = True
                    break
    reuse_ok = not signature_fail
    if signature_fail:
        reuse_evidence = "; ".join(signature_fail[:2])
    elif reuse_source:
        reuse_evidence = "component signature present at every width; changed src file imports and calls components/card.js"
    else:
        reuse_evidence = "component signature present at every width; no changed src static import/call evidence"
    verdicts["card_reuses_component"] = (reuse_ok, reuse_evidence)

    literal_patterns = {
        ".css": re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\("),
        ".js": re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{8}\b|rgba?\(|hsla?\("),
        ".html": re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{8}\b|rgba?\(|hsla?\("),
    }
    literal_hits = []
    if final_files is not None:
        for rel in sorted(final_files):
            if not (rel.startswith("src/") or rel.startswith("public/")) or rel == "src/styles/tokens.css":
                continue
            suffix = Path(rel).suffix
            pattern = literal_patterns.get(suffix)
            if not pattern:
                continue
            for line_no, line in _changed_line_entries(setup_files, final_files, rel):
                match = pattern.search(line)
                if match:
                    literal_hits.append(f"{rel}:{line_no}: expected tokens only, observed {match.group(0)} in {line.strip()}")
                    break
    verdicts["tokens_only"] = (not literal_hits, "; ".join(literal_hits[:2]) if literal_hits else "no added color literals under src/ or public/")

    empty_fail = []
    travel = (measurements.get("empty_state") or {}).get("/accounts/travel", {})
    checking = (measurements.get("empty_state") or {}).get("/accounts/checking", {})
    for width in UI_WIDTHS:
        data = _width_data(travel, width)
        error = _measurement_error(data)
        if error:
            empty_fail.append(f"travel@{width} expected message/link visible and 0 tables, observed error: {error}")
        elif not (data.get("message_visible") and data.get("link_visible") and data.get("visible_tables") == 0):
            empty_fail.append(f"travel@{width} expected message/link visible and 0 tables, observed {data}")
    for width in UI_WIDTHS:
        data = _width_data(checking, width)
        error = _measurement_error(data)
        if error:
            empty_fail.append(f"checking@{width} expected one table with 3 rows, observed error: {error}")
        elif data.get("visible_tables") != 1 or data.get("tbody_rows") != [3]:
            empty_fail.append(f"checking@{width} expected one table with 3 rows, observed {data}")
    verdicts["empty_state"] = (not empty_fail, "; ".join(empty_fail[:2]) if empty_fail else "empty state and populated transaction table match")

    layout_fail = []
    for width, data in _all_widths(measurements, "transfer_layout"):
        error = _measurement_error(data)
        if error:
            layout_fail.append(f"{width}: {error}")
            continue
        if not data.get("found"):
            layout_fail.append(f"{width}: {data.get('reason', 'form or panel missing')}")
            continue
        form, panel = data.get("form") or {}, data.get("panel") or {}
        if int(width) == 1280:
            intersects = not (panel.get("left") >= form.get("right") or panel.get("right") <= form.get("left") or panel.get("top") >= form.get("bottom") or panel.get("bottom") <= form.get("top"))
            vertical_overlap = min(form.get("bottom"), panel.get("bottom")) > max(form.get("top"), panel.get("top"))
            if intersects or not vertical_overlap:
                layout_fail.append(f"{width}: expected side-by-side nonintersecting boxes with vertical overlap, observed form {form}, panel {panel}")
        else:
            if panel.get("top") < form.get("bottom") - 1:
                layout_fail.append(f"{width}: expected panel below form, observed form bottom {form.get('bottom')}, panel top {panel.get('top')}")
    verdicts["transfer_layout"] = (not layout_fail, "; ".join(layout_fail[:2]) if layout_fail else "transfer panel layout matches widths")
    return verdicts

def mutation(repo: Path, setup_src: dict, replace: dict) -> dict:
    """Restore src/ to the setup state (plus `replace` overrides), keep the agent's tests, run the suite."""
    with tempdir("tl-mut-") as tmp:
        copy = Path(tmp) / "repo"
        shutil.copytree(repo, copy, ignore=shutil.ignore_patterns(".git", ".cache", "dist", "node_modules"))
        shutil.rmtree(copy / "src")
        write_tree(copy, {**setup_src, **replace})
        proc = run("node scripts/test.mjs", cwd=copy, check=False, timeout=600)
        text = proc.stdout + proc.stderr
        return {"code": proc.returncode, **parse_test_output(proc.stdout),
                "import_error": bool(re.search(r"does not provide an export named|Cannot find module|ERR_MODULE_NOT_FOUND",
                                               text)),
                "failing": re.findall(r"^\s*✖ (.+?)(?: \(\d)", proc.stdout, re.M)[:20]}


VERDICT_PATTERNS = {
    "execute-task": r"\b(?:Status:\s*)?(DONE|BLOCKED)\b",
    "verify-task": r"VERIFY:\s*(PASS|FAIL)",
    "pr-review": r"\b(Request(?:ed)? Changes|Approve(?:d)?|Needs Clarification|BLOCKED)\b",
}


def report_verdict(skill: str, text: str):
    match = re.search(VERDICT_PATTERNS[skill], text, re.I)
    return match.group(1) if match else None


S11_SCRIPT = r"""
import { main } from './src/cli.js';
import { tempLedger } from './test/helpers.js';
const out = {};
const safe = async (name, fn) => { try { out[name] = await fn(); } catch (e) { out[name] = 'THROWS: ' + e.message; } };
await safe('typo', () => main(['tranfer', 'alice', 'bob', '10.50']));
await safe('none', () => main([]));
await safe('frob', () => main(['frobnicate']));
const { path, cleanup } = await tempLedger();
try {
  await safe('balance', () => main(['balance', 'alice'], { ledgerPath: path }));
  await safe('transfer', () => main(['transfer', 'alice', 'bob', '10.50'], { ledgerPath: path }));
  await safe('bad_amount', () => main(['transfer', 'alice', 'bob', '20,00'], { ledgerPath: path }));
} finally { await cleanup(); }
console.log(JSON.stringify(out));
"""

P4_SCRIPT = r"""
import { main } from './src/cli.js';
const out = {};
const safe = async (name, fn) => { try { out[name] = await fn(); } catch (e) { out[name] = 'THROWS: ' + e.message; } };
await safe('usage', () => main(['frobnicate']));
await safe('fee_transfer', () => main(['fee', '10.50', 'transfer']));
await safe('fee_withdraw', () => main(['fee', '50.25', 'withdraw']));
await safe('fee_unknown', () => main(['fee', '10', 'foo']));
await safe('fee_float', () => main(['fee', '12.345', 'transfer']));
try { out.exports = Object.keys(await import('./src/fee-preview.js')); } catch (e) { out.exports = 'THROWS: ' + e.message; }
console.log(JSON.stringify(out));
"""


def mutation_keep_src(repo: Path, replace: dict) -> dict:
    """Run the suite on the run's final tree with `replace` overrides (its own src and tests otherwise kept)."""
    with tempdir("tl-mutk-") as tmp:
        copy = Path(tmp) / "repo"
        shutil.copytree(repo, copy, ignore=shutil.ignore_patterns(".git", ".cache", "dist", "node_modules"))
        write_tree(copy, replace)
        proc = run("node scripts/test.mjs", cwd=copy, check=False, timeout=600)
        return {"code": proc.returncode, **parse_test_output(proc.stdout),
                "failing": re.findall(r"^\s*✖ (.+?)(?: \(\d)", proc.stdout, re.M)[:20]}


MUTANTS_DIR = FIXTURE_DIR / "mutants" / "refund"
REFERENCE_TEST = FIXTURE_DIR / "reference" / "refund.reference.test.js"
IMPORT_ERROR = re.compile(r"does not provide an export named|Cannot find module|ERR_MODULE_NOT_FOUND|SyntaxError")
# A command that writes to a source file: an edit tool on src/, or a shell write that names src/.
SRC_WRITE = re.compile(r"^(?:edit|create|apply_patch) .*src[\\/]|^\$ (?=.*(?:Set-Content|Out-File|Copy-Item|Move-Item|"
                       r"WriteAllText|WriteAllBytes|writeFile|sed -i))(?=.*src[\\/])", re.I)


def run_suite(repo: Path, replace: dict, targets=()) -> dict:
    """Run the suite (or `targets`) on a copy of the final tree with `replace` overrides."""
    with tempdir("tl-q1-") as tmp:
        copy = Path(tmp) / "repo"
        shutil.copytree(repo, copy, ignore=shutil.ignore_patterns(".git", ".cache", "dist", "node_modules"))
        write_tree(copy, replace)
        proc = run(["node", "scripts/test.mjs", *targets], cwd=copy, check=False, timeout=600)
        text = proc.stdout + proc.stderr
        return {"code": proc.returncode, **parse_test_output(proc.stdout), "import_error": bool(IMPORT_ERROR.search(text)),
                "failing": re.findall(r"^\s*✖ (.+?)(?: \(\d)", proc.stdout, re.M)[:20]}


def collect_q1(repo: Path, setup: dict) -> dict:
    out = {"refund_exists": (repo / "src" / "refund.js").is_file()}
    mutants = {}
    for path in sorted(MUTANTS_DIR.glob("M*.js"), key=lambda p: int(p.stem[1:])):
        r = run_suite(repo, {"src/refund.js": path.read_text(encoding="utf-8")})
        r["status"] = "invalid" if r["import_error"] else ("killed" if r["code"] != 0 else "survived")
        mutants[path.stem] = r
    out["mutants"] = mutants
    out["reference"] = run_suite(repo, {"test/refund.reference.test.js": REFERENCE_TEST.read_text(encoding="utf-8")},
                                 ["test/refund.reference.test.js"])
    before, after = setup["snapshot"], snapshot(repo)
    out["existing_tests_changed"] = sorted(p for p in before if p.startswith("test/")
                                           and (p not in after or after[p] != before[p]))
    new_tests = {p: (repo / p).read_text(encoding="utf-8", errors="replace") for p in after
                 if p.startswith("test/") and p not in before}
    out["new_tests"] = sorted(new_tests)
    out["computeFee_in_new_tests"] = sorted(p for p, t in new_tests.items() if "computeFee(" in t)
    return out


UI_WORKER_KEYS = {"ub1", "uv1", "uv2", "uv3", "uv4", "uv5", "ur1"}
UI_MAIN_KEYS = {"ug1", "us1", "uc1"}
UI_MAIN_EVENT_KEYS = {"up1", *UI_MAIN_KEYS}
DESIGN_TOOL_NAMES = {"get_design_context", "get_variable_defs", "get_metadata", "get_screenshot",
                     "get_code_connect_map"}


def mcp_tool_base(tool: str) -> str:
    """A tool's own name without the MCP server prefix a host adds: `figma-get_metadata`, `mcp__figma__get_metadata`."""
    return re.split(r"__|-", tool)[-1]


PLAYWRIGHT_IMPORT = re.compile(r"""['"](?:@playwright/test|playwright(?:-core)?)['"]""")
TEST_COMMAND = re.compile(r"(?i)\bnpm(?:\.cmd)?\s+(?:run\s+)?test\b|scripts[\\/]test\.mjs|\bnode(?:\.exe)?\s+--test\b")
SCRIPT_PATH = re.compile(r"""[\w.:\\/-]+\.(?:mjs|cjs|js|ts)\b""")


def playwright_files(setup: dict) -> list[Path]:
    """Files under the world repo that the run created or changed and that import Playwright."""
    repo = Path(setup["repo"])
    if not repo.is_dir():
        return []
    before = setup.get("snapshot", {})
    found = []
    for rel, digest in snapshot(repo).items():
        if before.get(rel) == digest or not rel.endswith((".js", ".mjs", ".cjs", ".ts")):
            continue
        text = (repo / rel).read_text(encoding="utf-8", errors="replace")
        if PLAYWRIGHT_IMPORT.search(text):
            found.append(repo / rel)
    return found


def runs_playwright_file(command: str, repo: Path, files: list[Path]) -> bool:
    """Whether a shell command runs a test suite or a script that drives a browser through Playwright."""
    if files and TEST_COMMAND.search(command):
        return True
    for raw in SCRIPT_PATH.findall(command):
        path = Path(raw.strip("'\""))
        path = path if path.is_absolute() else repo / path
        try:
            if path.resolve() in {f.resolve() for f in files}:
                return True
            if path.is_file() and PLAYWRIGHT_IMPORT.search(path.read_text(encoding="utf-8", errors="replace")):
                return True
        except OSError:
            continue
    return False


def collect_ui_events(setup: dict, events) -> tuple[list[str], list[str]]:
    """Return arm-blind browser/design activity for one run agent and its descendants.

    Browser use is a browser tool call, a shell command that names Playwright, or a shell command that runs a test
    suite or script using a Playwright-importing file the run wrote (its own browser tests).
    """
    name = Path(setup["agent_root"]).name
    agent = None
    for attempt in [name, f"{name}-r", *(f"{name}-r{i}" for i in range(2, 10))]:
        agent = events.by_name(attempt) or agent
    if not agent:
        return [], []
    repo = Path(setup["repo"])
    pw_files = playwright_files(setup)
    browser_use, design_calls = [], []
    for node in events.tree(agent["id"]):
        for entry in events.tools.get(node["id"], []):
            tool = str(entry.get("tool") or "")
            base = mcp_tool_base(tool)
            args = entry.get("args") if isinstance(entry.get("args"), dict) else {}
            command = str(args.get("command", ""))
            if "playwright" in tool.lower() or base.startswith("browser_"):
                browser_use.append(f"{base} {json.dumps(args, ensure_ascii=False)[:220]}")
            elif tool == "powershell" and re.search(r"\bplaywright\b", command, re.I):
                browser_use.append("$ " + command[:300])
            elif tool == "powershell" and runs_playwright_file(command, repo, pw_files):
                browser_use.append("$ " + command[:300] + "  [runs Playwright tests or script]")
            if base in DESIGN_TOOL_NAMES:
                design_calls.append(base)
    return browser_use, design_calls


BALANCES_SCRIPT = r"""
import { main } from './src/cli.js';
import { tempLedger } from './test/helpers.js';
const out = {};
const safe = async (name, fn) => { try { out[name] = await fn(); } catch (e) { out[name] = 'THROWS: ' + e.message; } };
const { ledger, path, cleanup } = await tempLedger({ carol: 250, alice: 10000, bob: 5000 });
try {
  await safe('balances', () => main(['balances'], { ledgerPath: path }));
  await safe('list', () => ledger.listBalances());
  await safe('usage', async () => (await main(['frobnicate'])).output);
  await safe('balance', () => main(['balance', 'alice'], { ledgerPath: path }));
} finally { await cleanup(); }
console.log(JSON.stringify(out));
"""
SPECULATIVE = re.compile(r"\bcsv\b|\bjson\b|sortBy|sortOrder|\blimit\b|\boffset\b|pageSize|\bformat\s*=|\[\s*format\b|--\w+", re.I)


def collect_o1(repo: Path, setup: dict) -> dict:
    before, after = setup["snapshot"], snapshot(repo)
    changed = sorted((set(after) ^ set(before)) | {p for p in set(before) & set(after) if before[p] != after[p]})
    added_src = []
    for rel in changed:
        if not rel.startswith("src/") or rel not in after:
            continue
        old = setup["files"].get(rel, "").splitlines()
        new = (repo / rel).read_text(encoding="utf-8", errors="replace").splitlines()
        from collections import Counter
        left = Counter(old)
        for line in new:
            if left[line] > 0:
                left[line] -= 1
            elif line.strip() and not line.strip().startswith("//"):
                added_src.append(f"{rel}: {line.strip()}")
    return {"changed_files": changed, "added_src_lines": added_src,
            "speculative": [l for l in added_src if SPECULATIVE.search(l)],
            "behavior": node_eval(repo, BALANCES_SCRIPT)}


CITATION_RE = re.compile(r"((?:src|test|docs|scripts)/[\w./-]+\.(?:js|mjs|md|json)):(\d+)(?:-(\d+))?")


def node_eval_original(repo: Path, setup_src: dict, script: str) -> dict:
    """Run a behavior script against the setup's src/ with the agent's tests and helpers left in place."""
    with tempdir("tl-orig-") as tmp:
        copy = Path(tmp) / "repo"
        shutil.copytree(repo, copy, ignore=shutil.ignore_patterns(".git", ".cache", "dist", "node_modules"))
        shutil.rmtree(copy / "src")
        write_tree(copy, setup_src)
        return node_eval(copy, script)


def check_citations(repo: Path, files: dict) -> list[dict]:
    out = []
    for rel, text in sorted(files.items()):
        # Windows-style citations (src\\cli.js:14) count too.
        for match in CITATION_RE.finditer(text.replace("\\", "/")):
            path, first = match.group(1), int(match.group(2))
            last = int(match.group(3) or first)
            target = repo / path
            count = len(target.read_text(encoding="utf-8", errors="replace").splitlines()) if target.is_file() else 0
            out.append({"in": rel, "cite": match.group(0), "exists": target.is_file(),
                        "ok": target.is_file() and 1 <= first <= last <= count, "lines_in_file": count})
    return out


def find_run(ref: str) -> Path:
    """A run dir, given its path or its agent name (tl-xxxxxx, optionally with a -r suffix)."""
    if Path(ref).is_dir():
        return Path(ref)
    name = re.sub(r"-r\d*$", "", ref)
    for setup in WORKSPACE.glob("iteration-*/eval-*/*/run-*/setup.json"):
        if Path(json.loads(setup.read_text(encoding="utf-8"))["agent_root"]).name == name:
            return setup.parent
    raise SystemExit(f"no run for {ref}")


def record_turn(run_dir: Path, n: int, kind: str) -> str:
    """Save the agent's reply for turn n, snapshot the repo, and pick the scripted user reply (or STOP)."""
    setup = json.loads((run_dir / "setup.json").read_text(encoding="utf-8"))
    spec = SCENARIOS[setup["eval"]]
    script = json.loads((SCENARIOS_DIR / spec["key"] / "eval.json").read_text(encoding="utf-8")).get("user_script", {})
    repo, agent_outputs = Path(setup["repo"]), Path(setup["agent_outputs"])
    source = agent_outputs / f"turn-{n}.md"
    text = source.read_text(encoding="utf-8", errors="replace") if source.exists() else ""
    (run_dir / "outputs").mkdir(exist_ok=True)
    if text.strip():
        (run_dir / "outputs" / f"turn-{n}.md").write_text(text, encoding="utf-8", newline="\n")
    turns_file = run_dir / "turns.json"
    turns = json.loads(turns_file.read_text(encoding="utf-8")) if turns_file.exists() else []
    turns = [t for t in turns if t["n"] < n]
    before, after = setup["snapshot"], snapshot(repo)
    changed = sorted((set(after) ^ set(before)) | {p for p in set(before) & set(after) if before[p] != after[p]})
    docs = {rel: (repo / rel).read_text(encoding="utf-8", errors="replace") for rel in changed
            if rel.startswith("docs/") and (repo / rel).is_file()}
    replies = sum(1 for t in turns if t.get("reply"))
    # "review": the agent presented its result without asking; the developer answers as they would an approval.
    approvals = sum(1 for t in turns if t["kind"] in ("approval", "review"))
    reply = None
    if kind in ("approval", "review", "question", "quiz") and replies < script.get("max_replies", 0):
        as_approval = kind in ("approval", "review")
        reply = script["first_approval"] if as_approval and not approvals and script.get("first_approval") \
            else script.get("approval" if as_approval else kind)
        if isinstance(reply, list):
            # A list is used in order, one entry per reply of this kind; the last entry repeats.
            same = sum(1 for t in turns if t.get("reply") and (t["kind"] in ("approval", "review")) == as_approval
                       and (as_approval or t["kind"] == kind))
            reply = reply[min(same, len(reply) - 1)] if reply else None
    turns.append({"n": n, "kind": kind, "at": datetime.now().isoformat(timespec="seconds"),
                  "reply_file": bool(text.strip()), "changed": changed,
                  "code_changed": [c for c in changed if c.startswith(("src/", "test/"))],
                  "head_moved": git(repo, "rev-parse", "HEAD").stdout.strip() != setup["head"],
                  "docs": docs, "reply": reply})
    turns_file.write_text(json.dumps(turns, indent=2, ensure_ascii=False), encoding="utf-8")
    return reply or "STOP"


def collect_main(run_dir: Path, setup: dict, spec: dict, events) -> dict:
    result = None
    try:
        repo, agent_outputs, outputs = Path(setup["repo"]), Path(setup["agent_outputs"]), run_dir / "outputs"
        # The agent's own files (it writes one per progress note, so their numbers are not the conversation's turns).
        (outputs / "agent-files").mkdir(exist_ok=True)
        for item in sorted(agent_outputs.iterdir()) if agent_outputs.is_dir() else []:
            if item.is_file():
                (outputs / "agent-files" / item.name).write_text(item.read_text(encoding="utf-8", errors="replace"),
                                                                 encoding="utf-8", newline="\n")
        for stale in outputs.glob("turn-*.md"):
            stale.unlink()
        before, after = setup["snapshot"], snapshot(repo)
        changes = {"added": sorted(set(after) - set(before)), "deleted": sorted(set(before) - set(after)),
                   "modified": sorted(p for p in set(before) & set(after) if before[p] != after[p])}
        changes["head_moved"] = git(repo, "rev-parse", "HEAD").stdout.strip() != setup["head"]
        changes["branch_now"] = git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        changes["status_now"] = git(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout
        (outputs / "final-diff.patch").write_text(agent_diff(setup["files"], repo), encoding="utf-8", newline="\n")
        turns_file = run_dir / "turns.json"
        turns = json.loads(turns_file.read_text(encoding="utf-8")) if turns_file.exists() else []

        name = Path(setup["agent_root"]).name
        agent = None
        for attempt in [name, f"{name}-r", *(f"{name}-r{i}" for i in range(2, 10))]:
            agent = events.by_name(attempt) or agent
        tree = []
        if agent:
            from events import replies
            said = replies({agent["id"]}).get(agent["id"], [])
            for index, text in enumerate(said, 1):
                (outputs / f"turn-{index}.md").write_text(text.strip() + "\n", encoding="utf-8", newline="\n")
            for entry in turns:
                entry["reply_found"] = entry["n"] <= len(said)
            for node in events.tree(agent["id"]):
                node = {k: v for k, v in node.items() if k != "tool_call_id"}
                node["commands"] = events.commands(node["id"])
                node["skills_read"] = events.skills_read(node["id"], setup["plugin"])
                tree.append(node)
        evidence = {}
        for label, rel in (("test", ".cache/junit.xml"), ("lint", ".cache/lint-report.json"),
                           ("build", "dist/build-info.json")):
            path = repo / rel
            evidence[label] = {"ran": path.exists() and path.stat().st_mtime > setup["built_at"]}
        result = {"mode": "main", "turns": turns, "changes": changes, "evidence": evidence,
                  "final_checks": run_checks(repo), "agent_found": bool(agent), "tree": tree,
                  "docs_final": {rel: (repo / rel).read_text(encoding="utf-8", errors="replace")
                                 for rel in sorted(set(after)) if rel.startswith("docs/") and rel not in before
                                 or rel.startswith("docs/") and before.get(rel) != after.get(rel)}}
        key = spec["key"]
        setup_src = {rel: text for rel, text in setup["files"].items() if rel.startswith("src/")}
        if key in ("s11", "s11r"):
            result["behavior"] = node_eval(repo, S11_SCRIPT)
            result["behavior_original"] = node_eval_original(repo, setup_src, S11_SCRIPT)
            result["mutations"] = {"M1_original_src": mutation(repo, setup_src, {})}
        if key == "p4":
            result["behavior"] = node_eval(repo, P4_SCRIPT)
            result["mutations"] = {"M_unknown_kind_as_transfer": mutation_keep_src(
                repo, {"src/fee-preview.js": (LAYERS / "fee15-bug/src/fee-preview.js").read_text(encoding="utf-8")})}
            texts = {p.relative_to(repo).as_posix(): p.read_text(encoding="utf-8", errors="replace")
                     for p in (repo / "src").rglob("*.js")}
            result["src_texts"] = {k: v for k, v in texts.items() if k in ("src/cli.js", "src/fee-preview.js")}
        if key == "p5":
            result["behavior"] = node_eval(repo, BEHAVIOR_SCRIPTS["e7"])
            result["mutations"] = {
                "M1_original_src": mutation(repo, setup_src, {}),
                "M2_transfer_only_fix": mutation(repo, setup_src, {"src/fees.js": E7_TRANSFER_ONLY_FIX}),
            }
        if key in ("s12", "up1"):
            written = {}
            for t in turns:
                written.update(t.get("docs", {}))
            written.update(result["docs_final"])
            result["citations"] = check_citations(repo, {rel: text for rel, text in written.items()
                                                         if rel.startswith(("docs/reviews/", "docs/tasks/"))})
        if key in UI_MAIN_EVENT_KEYS:
            browser_use, design_calls = collect_ui_events(setup, events)
            result["browser_use"] = browser_use
            result["design_calls"] = design_calls
        if key in UI_MAIN_KEYS:
            main_tree_files = git_tree_text(repo, "main", ("src", "public"))
            result["ui"] = ui_eval(repo, Path(setup["web_modules"]), [])
            result["main_tree_files"] = main_tree_files
            result["setup_files"] = main_tree_files
            result["final_files"] = tree_text(repo)
        if key in ("f1", "f2", "f3", "f4"):
            result["instruction_files"] = {rel: (repo / rel).read_text(encoding="utf-8", errors="replace")
                                           for rel in ("CLAUDE.md", "AGENTS.md", ".github/copilot-instructions.md", "README.md")
                                           if (repo / rel).is_file()}
            texts = {p.stem: p.read_text(encoding="utf-8", errors="replace") for p in sorted(outputs.glob("turn-*.md"))}
            result["citations"] = check_citations(repo, texts)
        if key == "f1":
            import yaml
            profiles = {}
            for name in ("project.yml", "team.yml", "runtime.yml"):
                path = repo / "docs" / "profiles" / name
                entry = {"exists": path.is_file()}
                if path.is_file():
                    text = path.read_text(encoding="utf-8", errors="replace")
                    entry["text"] = text
                    try:
                        parsed = yaml.safe_load(text)
                        entry["types"] = {k: type(v).__name__ for k, v in (parsed or {}).items()} \
                            if isinstance(parsed, dict) else {}
                        entry["parsed"] = json.loads(json.dumps(parsed, default=str))
                    except yaml.YAMLError as error:
                        entry["error"] = str(error).splitlines()[0]
                profiles[name] = entry
            result["profiles"] = profiles
        return result
    finally:
        cleanup = cleanup_web_run(setup, events)
        if result is not None:
            result.update(cleanup)


def collect(run_dir: Path, events=None):
    run_dir = Path(run_dir)
    setup = json.loads((run_dir / "setup.json").read_text(encoding="utf-8"))
    repo, agent_outputs, outputs = Path(setup["repo"]), Path(setup["agent_outputs"]), run_dir / "outputs"
    outputs.mkdir(exist_ok=True)
    spec = SCENARIOS[setup["eval"]]
    key = spec["key"]
    if spec.get("mode") == "main":
        from events import Events
        result = collect_main(run_dir, setup, spec, events or Events())
        (run_dir / "collected.json").write_text(json.dumps(result, indent=2, ensure_ascii=True), encoding="utf-8")
        return result

    result = None
    try:
        evidence = {}
        for name, rel in (("test", ".cache/junit.xml"), ("lint", ".cache/lint-report.json"),
                          ("build", "dist/build-info.json")):
            path = repo / rel
            evidence[name] = {"ran": path.exists() and path.stat().st_mtime > setup["built_at"],
                              "mtime": path.stat().st_mtime if path.exists() else None}
        junit = repo / ".cache/junit.xml"
        if junit.exists():
            evidence["test"]["testcases_in_last_run"] = junit.read_text(encoding="utf-8", errors="replace").count("<testcase")

        before, after = setup["snapshot"], snapshot(repo)
        changes = {"added": sorted(set(after) - set(before)), "deleted": sorted(set(before) - set(after)),
                   "modified": sorted(p for p in set(before) & set(after) if before[p] != after[p])}
        changes["head_moved"] = git(repo, "rev-parse", "HEAD").stdout.strip() != setup["head"]
        changes["branch_now"] = git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        changes["status_now"] = git(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout
        (outputs / "final-diff.patch").write_text(agent_diff(setup["files"], repo), encoding="utf-8", newline="\n")

        report = agent_outputs / "report.md"
        report_text = report.read_text(encoding="utf-8", errors="replace") if report.exists() else ""
        if report_text.strip():
            (outputs / "report.md").write_text(report_text, encoding="utf-8", newline="\n")
        extra_outputs = sorted(p.name for p in agent_outputs.iterdir() if p.name != "report.md") \
            if agent_outputs.is_dir() else []
        result = {"report_present": bool(report_text.strip()), "verdict": report_verdict(spec["skill"], report_text),
                  "extra_agent_outputs": extra_outputs, "evidence": evidence, "changes": changes,
                  "final_checks": run_checks(repo)}
        if key in ("p1", "p2", "p3"):
            from events import Events
            events = events or Events()
            name = Path(setup["agent_root"]).name
            agent = None
            for attempt in [name, f"{name}-r", *(f"{name}-r{i}" for i in range(2, 10))]:
                agent = events.by_name(attempt) or agent
            cmds = events.commands(agent["id"]) if agent else []
            result["agent_found"] = bool(agent)
            result["read_untracked"] = {f: any(f in c for c in cmds) for f in ("fee-preview.js", "fee-preview.test.js")}
            result["commands"] = [c[:300] for c in cmds]
        if key == "q1":
            result.update(collect_q1(repo, setup))
        if key == "o1":
            result.update(collect_o1(repo, setup))
        if key in ("q2", "q3", "q4", "o2", "o3", "wv1", "wv2", "wv3", "wv4", "wr1", "wr2", "wr3", "wr4",
                   "lv1", "lv2", "lv3", "lr1", "lr2", "lr3", "lr4", "fv1", "fv2", "fv3", "fr1", "fr2", "fr3", "fr4",
                   "av1", "av2", "av3", "ar1", "ar2", "ar3", "xa1", "xa2", "xa3", "xac", "xf1", "xf2", "xl1", "xl2",
                   "xl3", "xw1", "xw2", "xs2"):
            from events import Events
            events = events or Events()
            name = Path(setup["agent_root"]).name
            agent = None
            for attempt in [name, f"{name}-r", *(f"{name}-r{i}" for i in range(2, 10))]:
                agent = events.by_name(attempt) or agent
            cmds = events.commands(agent["id"]) if agent else []
            result["agent_found"] = bool(agent)
            result["commands"] = [c[:400] for c in cmds]
            result["src_writes"] = [c[:300] for c in cmds if SRC_WRITE.search(c)]
        if key in UI_WORKER_KEYS:
            from events import Events
            events = events or Events()
            browser_use, design_calls = collect_ui_events(setup, events)
            main_tree_files = git_tree_text(repo, "main", ("src", "public"))
            result["browser_use"] = browser_use
            result["design_calls"] = design_calls
            result["ui"] = ui_eval(repo, Path(setup["web_modules"]), [])
            result["main_tree_files"] = main_tree_files
            result["setup_files"] = main_tree_files
            result["final_files"] = tree_text(repo)
        if key in BEHAVIOR_SCRIPTS:
            result["behavior"] = node_eval(repo, BEHAVIOR_SCRIPTS[key])
        setup_src = {rel: text for rel, text in setup["files"].items() if rel.startswith("src/")}
        if key == "e1":
            result["mutations"] = {"M1_original_src": mutation(repo, setup_src, {})}
        if key == "e7":
            result["mutations"] = {
                "M1_original_src": mutation(repo, setup_src, {}),
                "M2_transfer_only_fix": mutation(repo, setup_src, {"src/fees.js": E7_TRANSFER_ONLY_FIX}),
            }
        if key == "e2":
            src_text = {p.relative_to(repo).as_posix(): p.read_text(encoding="utf-8", errors="replace")
                        for p in (repo / "src").rglob("*.js")}
            result["e2"] = {
                "withdraw_exists": "src/withdraw.js" in src_text,
                "sync_fs_in_src": sorted(p for p, t in src_text.items()
                                         if re.search(r"\b(readFileSync|writeFileSync|appendFileSync|renameSync)\b", t)),
                "ledger_file_opened_outside_ledger": sorted(
                    p for p, t in src_text.items() if p != "src/ledger.js" and re.search(r"node:fs|from 'fs'", t)),
                "withdraw_source": src_text.get("src/withdraw.js"),
            }
        return result
    finally:
        cleanup = cleanup_web_run(setup, events)
        if result is not None:
            if cleanup:
                result.update(cleanup)
            (run_dir / "collected.json").write_text(json.dumps(result, indent=2, ensure_ascii=True), encoding="utf-8")



# ---------------------------------------------------------------- CLI


def eval_names_for_keys(keys: list[str]) -> list[str]:
    names = []
    for key in keys:
        matches = [name for name, spec in SCENARIOS.items() if spec["key"] == key]
        if len(matches) != 1:
            raise RuntimeError(f"expected exactly one scenario for key {key!r}, found {matches}")
        names.append(matches[0])
    return names


def round_definition(name: str) -> dict:
    if name not in ROUNDS:
        raise SystemExit(f"unknown round {name!r}; known rounds: {', '.join(sorted(ROUNDS))}")
    definition = dict(ROUNDS[name])
    definition["evals"] = eval_names_for_keys(definition["scenarios"])
    return definition


def show_round(name: str):
    definition = round_definition(name)
    print(f"round: {name}")
    print(f"iteration: {definition['iteration']}")
    print(f"runs: {definition['runs']}")
    print("arms:")
    for arm in definition["arms"]:
        print(f"  {arm}={definition['arm_specs'][arm]}")
    print("scenarios:")
    for key, eval_name in zip(definition["scenarios"], definition["evals"]):
        print(f"  {key}: {eval_name}")
    print("groups:")
    for group, keys in definition["groups"]:
        print(f"  {group}: {', '.join(keys)}")


def main():
    common = argparse.ArgumentParser(add_help=False)
    add_common_options(common, arms=True, skill_creator=True)
    parser = argparse.ArgumentParser(parents=[common])
    sub = parser.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", parents=[common])
    b.add_argument("--round", dest="round_name", default="")
    b.add_argument("--iteration", type=int, default=1)
    b.add_argument("--runs", type=int, default=2)
    b.add_argument("--evals", default="")
    b.add_argument("--arms", default=",".join(ARMS))
    r = sub.add_parser("round", parents=[common])
    r.add_argument("--show", metavar="NAME")
    c = sub.add_parser("collect", parents=[common])
    c.add_argument("run_dirs", nargs="+")
    ca = sub.add_parser("collect-all", parents=[common])
    ca.add_argument("--iteration", type=int, default=1)
    t = sub.add_parser("turn", parents=[common])
    t.add_argument("run", help="run dir or agent name")
    t.add_argument("--n", type=int, required=True)
    t.add_argument("--kind", required=True, choices=["approval", "review", "question", "final", "quiz", "other"])
    cl = sub.add_parser("cleanup", parents=[common])
    cl.add_argument("--iteration", type=int, default=1)
    sub.add_parser("web-modules", parents=[common])
    env_parser = sub.add_parser("environment", parents=[common])
    env_parser.add_argument("--iteration", type=int, required=True)
    env_parser.add_argument("--guidance-skill", type=Path, required=True)
    env_parser.add_argument("--playwright-mcp", required=True)
    env_parser.add_argument("--note", default="")
    args = parser.parse_args()
    configure_paths(args.workspace, parse_arm_specs(args.arm), args.skill_creator, args.web_modules)

    if args.cmd == "web-modules":
        install_web_modules(WEB_MODULES)
        return 0
    elif args.cmd == "environment":
        return write_environment_record(args.iteration, args.guidance_skill, args.playwright_mcp, args.note)
    elif args.cmd == "build":
        round_def = round_definition(args.round_name) if args.round_name else None
        if round_def:
            ARM_SPECS.update(round_def["arm_specs"])
            arm_names = [a for a in args.arms.split(",") if a] if args.arms != ",".join(ARMS) else round_def["arms"]
            wanted = round_def["evals"]
            if args.evals:
                selected = set(args.evals.split(","))
                wanted = [e for e in wanted if SCENARIOS[e]["key"] in selected or e in selected]
            if args.iteration == 1:
                args.iteration = round_def["iteration"]
            if args.runs == 2:
                args.runs = round_def["runs"]
        else:
            arm_names = [a for a in args.arms.split(",") if a]
            wanted = [e for e in SCENARIOS if not args.evals or SCENARIOS[e]["key"] in args.evals.split(",")]
        now = datetime.now()
        for eval_name in wanted:
            spec = SCENARIOS[eval_name]
            plugins = plugin_copies(args.iteration, arm_names, SCENARIO_STUBS.get(spec["key"]))
            eval_dir = WORKSPACE / f"iteration-{args.iteration}" / eval_name
            eval_dir.mkdir(parents=True, exist_ok=True)
            meta = json.loads((SCENARIOS_DIR / spec["key"] / "eval.json").read_text(encoding="utf-8"))
            assertions = [a["text"] if isinstance(a, dict) else a for a in meta.get("assertions", [])]
            (eval_dir / "eval_metadata.json").write_text(json.dumps(
                {"eval_id": int(eval_name.split("-")[1]), "eval_name": eval_name, "prompt": meta["prompt"],
                 "expected_output": meta.get("expected_output", ""), "assertions": assertions},
                indent=2, ensure_ascii=True), encoding="utf-8")
            for arm in arm_names:
                for idx in range(1, args.runs + 1):
                    run_dir = build_run(eval_name, arm, idx, args.iteration, now, plugins)
                    print(f"built {run_dir}")
    elif args.cmd == "collect":
        sys.path.insert(0, str(ROOT))
        from events import Events
        events = Events(resolve_session_dir(args.session_dir))
        for run_dir in args.run_dirs:
            collect(find_run(run_dir), events)
            print(f"collected {run_dir}")
    elif args.cmd == "collect-all":
        sys.path.insert(0, str(ROOT))
        from events import Events
        events = Events(resolve_session_dir(args.session_dir))
        for setup in sorted((WORKSPACE / f"iteration-{args.iteration}").glob("eval-*/*/run-*/setup.json")):
            collect(setup.parent, events)
            print(f"collected {setup.parent}")
    elif args.cmd == "turn":
        print(record_turn(find_run(args.run), args.n, args.kind))
    elif args.cmd == "cleanup":
        iteration_dir = WORKSPACE / f"iteration-{args.iteration}"
        roots = []
        for setup_path in iteration_dir.glob("eval-*/*/run-*/setup.json"):
            setup = json.loads(setup_path.read_text(encoding="utf-8"))
            if setup.get("fixture") == "web":
                stop_dev_servers(setup)
            release_dev_ports(WORKSPACE, [setup["agent_root"]])
            roots.append(Path(setup["agent_root"]))
        index = iteration_dir / "plugins.json"
        if index.exists():
            for value in json.loads(index.read_text(encoding="utf-8")).values():
                path = Path(value)
                roots.append(path.parent.parent if path.parent.name == "plugins" else path.parent)
            index.unlink()
        for root in dict.fromkeys(roots):
            if root.parent == AGENT_TMP and re.fullmatch(r"(tl|rp)-[0-9a-f]{6}", root.name):
                force_rmtree(root)
                print(f"removed {root}" if not root.exists() else f"FAILED to remove {root}")
    elif args.cmd == "round":
        if args.show:
            show_round(args.show)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
