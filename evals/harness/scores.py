"""Score a built Ritus evaluation iteration by assertion kind.

  python scores.py --iteration 26 [--workspace evals\\workspace]

Reads each run's grading.json and timing.json, maps assertion ids to ``kind`` from the scenario eval.json files, and
writes scores.json and scores.md in the iteration directory. When the iteration holds a contamination.json (from
contamination.py), every table comes twice: all runs, then the clean runs - the flagged runs left out.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from build import ROUNDS, SCENARIOS  # noqa: E402
from config import FIXTURE_DIR, add_common_options, resolve_workspace  # noqa: E402


def scenario_by_eval() -> dict[str, str]:
    return {name: spec["key"] for name, spec in SCENARIOS.items()}


def assertion_kinds() -> dict[str, dict[str, str]]:
    out = {}
    for path in sorted((FIXTURE_DIR / "scenarios").glob("*/eval.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        out[path.parent.name] = {a["id"]: a.get("kind", "") for a in data.get("assertions", [])}
    return out


def fully_marked(kinds: dict[str, dict[str, str]], key: str) -> bool:
    values = kinds.get(key, {}).values()
    return bool(values) and all(kind in ("outcome", "process") for kind in values)


def group_map(round_name: str | None) -> dict[str, str]:
    groups = ROUNDS.get(round_name or "", {}).get("groups", [])
    return {key: group for group, keys in groups for key in keys}


def known_group_map() -> dict[str, str]:
    out = {}
    for definition in ROUNDS.values():
        for group, keys in definition.get("groups", []):
            for key in keys:
                out.setdefault(key, group)
    return out


def observed_scenarios(iteration_dir: Path, eval_to_key: dict[str, str]) -> list[str]:
    keys = []
    for setup_path in sorted(iteration_dir.glob("eval-*/*/run-*/setup.json")):
        setup = json.loads(setup_path.read_text(encoding="utf-8"))
        key = eval_to_key[setup["eval"]]
        if key not in keys:
            keys.append(key)
    return keys


def infer_round(observed_keys: list[str]) -> str | None:
    observed = set(observed_keys)
    for name, definition in ROUNDS.items():
        if observed == set(definition.get("scenarios", [])):
            return name
    return None


def known_round_positions() -> dict[str, int]:
    positions = {}
    for definition in ROUNDS.values():
        for index, key in enumerate(definition.get("scenarios", [])):
            positions.setdefault(key, index)
    return positions


def scenario_order(round_name: str | None, observed_keys: list[str]) -> list[str]:
    observed = set(observed_keys)
    if round_name:
        ordered = [key for key in ROUNDS[round_name]["scenarios"] if key in observed]
        return ordered + sorted(observed - set(ordered))
    positions = known_round_positions()
    return sorted(observed, key=lambda key: (positions.get(key, 1_000_000), key))


def group_order(round_name: str | None, observed_keys: list[str], groups: dict[str, str]) -> list[str]:
    present = {groups.get(key, "ungrouped") for key in observed_keys}
    if round_name:
        ordered = [group for group, _ in ROUNDS[round_name]["groups"] if group in present]
        return ordered + sorted(present - set(ordered))
    first_seen = {}
    for key in scenario_order(None, observed_keys):
        first_seen.setdefault(groups.get(key, "ungrouped"), len(first_seen))
    return sorted(present, key=lambda group: (first_seen.get(group, 1_000_000), group))


def empty_counter() -> dict[str, int]:
    return {"passed": 0, "total": 0}


def empty_slot() -> dict:
    return {"runs": 0, "outcome": empty_counter(), "process": empty_counter(), "tokens": [], "seconds": []}


def add_expectation(target: dict, kind: str, passed: bool):
    slot = target[kind]
    slot["passed"] += int(passed)
    slot["total"] += 1


def rate(slot: dict) -> float | None:
    return None if slot["total"] == 0 else round(slot["passed"] / slot["total"], 4)


def summarize_counter(slot: dict) -> dict:
    return {**slot, "pass_rate": rate(slot)}


def summarize_slot(slot: dict) -> dict:
    return {"runs": slot["runs"], **{kind: summarize_counter(slot[kind]) for kind in ("outcome", "process")},
            "mean_tokens_per_run": mean(slot["tokens"]), "mean_seconds_per_run": mean(slot["seconds"])}


def mean(values: list[float]) -> float | None:
    return None if not values else round(sum(values) / len(values), 2)


def excluded_runs(iteration_dir: Path) -> dict[str, list[str]]:
    """Runs contamination.py flagged, with what each one loaded or read."""
    path = iteration_dir / "contamination.json"
    if not path.exists():
        return {}
    flagged = json.loads(path.read_text(encoding="utf-8")).get("contaminated", {})
    return {run_rel: sorted({s["skill"] for s in info.get("skills", []) if s.get("loaded") is not False}
                            | ({"outside paths"} if info.get("outside") else set())
                            | ({"unscoped search"} if info.get("unscoped_search") else set()))
            for run_rel, info in flagged.items()}


def tally(iteration_dir: Path, eval_to_key: dict[str, str], kinds: dict, groups: dict[str, str],
          included_keys: set[str], exclude: set[str]) -> dict:
    arms = defaultdict(empty_slot)
    by_group = defaultdict(lambda: defaultdict(empty_slot))
    by_scenario = defaultdict(lambda: defaultdict(empty_slot))
    missing_kind = []
    for grading_path in sorted(iteration_dir.glob("eval-*/*/run-*/grading.json")):
        run_dir = grading_path.parent
        if run_dir.relative_to(iteration_dir).as_posix() in exclude:
            continue
        setup = json.loads((run_dir / "setup.json").read_text(encoding="utf-8"))
        key = eval_to_key[setup["eval"]]
        if key not in included_keys:
            continue
        arm = setup["arm"]
        slots = (arms[arm], by_group[groups.get(key, "ungrouped")][arm], by_scenario[key][arm])
        for slot in slots:
            slot["runs"] += 1
        grading = json.loads(grading_path.read_text(encoding="utf-8"))
        for expectation in grading.get("expectations", []):
            aid = expectation["id"]
            kind = kinds.get(key, {}).get(aid)
            if kind not in ("outcome", "process"):
                missing_kind.append(f"{key}:{aid}")
                continue
            for slot in slots:
                add_expectation(slot, kind, bool(expectation.get("passed")))
        timing_path = run_dir / "timing.json"
        if timing_path.exists():
            info = json.loads(timing_path.read_text(encoding="utf-8"))
            seconds = info.get("total_duration_seconds")
            if seconds is None and info.get("duration_ms") is not None:
                seconds = float(info["duration_ms"]) / 1000
            for slot in slots:
                if info.get("total_tokens") is not None:
                    slot["tokens"].append(float(info["total_tokens"]))
                if seconds is not None:
                    slot["seconds"].append(float(seconds))
    return {"arms": arms, "groups": by_group, "scenarios": by_scenario, "missing_kind": missing_kind}


def summarize(tallied: dict, arm_names: list[str], group_names: list[str], scenario_keys: list[str]) -> dict:
    # Every arm gets a row, even one the clean subset left with no runs in a group.
    section = {"arms": {arm: summarize_slot(tallied["arms"].get(arm) or empty_slot()) for arm in arm_names},
               "groups": {}, "scenarios": {}}
    for name, keys in (("groups", group_names), ("scenarios", scenario_keys)):
        for key in keys:
            by_arm = tallied[name].get(key, {})
            section[name][key] = {arm: summarize_slot(by_arm.get(arm) or empty_slot()) for arm in arm_names}
    return section


def fmt(counter: dict) -> str:
    shown = "n/a" if counter["pass_rate"] is None else counter["pass_rate"]
    return f"{counter['passed']}/{counter['total']} ({shown})"


def section_lines(section: dict, suffix: str = "") -> list[str]:
    def row(label: str, info: dict) -> str:
        tokens, seconds = info["mean_tokens_per_run"], info["mean_seconds_per_run"]
        return (f"| {label} | {info['runs']} | {fmt(info['outcome'])} | {fmt(info['process'])} | "
                f"{'n/a' if tokens is None else f'{tokens:,.0f}'} | {'n/a' if seconds is None else f'{seconds:.1f}'} |")

    head = "| runs | outcome | process | mean tokens/run | mean seconds/run |"
    lines = [f"## Arms{suffix}", "", f"| arm {head}", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    lines += [row(arm, info) for arm, info in section["arms"].items()]
    for title, name, label in (("Groups", "groups", "group"), ("Scenarios", "scenarios", "scenario")):
        lines += ["", f"## {title}{suffix}", "", f"| {label} | arm {head}",
                  "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
        lines += [row(f"{key} | {arm}", info) for key, by_arm in section[name].items() for arm, info in by_arm.items()]
    return lines


def main() -> int:
    parser = argparse.ArgumentParser()
    add_common_options(parser)
    parser.add_argument("--iteration", type=int, required=True)
    parser.add_argument("--round", dest="round_name", default=None)
    args = parser.parse_args()

    workspace = resolve_workspace(args.workspace)
    iteration_dir = workspace / f"iteration-{args.iteration}"
    if not iteration_dir.is_dir():
        raise SystemExit(f"iteration directory does not exist: {iteration_dir}")

    eval_to_key = scenario_by_eval()
    kinds = assertion_kinds()
    observed_keys = observed_scenarios(iteration_dir, eval_to_key)
    round_name = args.round_name or infer_round(observed_keys)
    if args.round_name and args.round_name not in ROUNDS:
        raise SystemExit(f"unknown round {args.round_name!r}; known rounds: {', '.join(sorted(ROUNDS))}")
    groups = group_map(round_name) if round_name else known_group_map()
    included_keys = set(ROUNDS[args.round_name]["scenarios"]) if args.round_name else {
        key for key in observed_keys if round_name or fully_marked(kinds, key)
    }
    excluded = excluded_runs(iteration_dir)
    every = tally(iteration_dir, eval_to_key, kinds, groups, included_keys, set())
    if every["missing_kind"]:
        missing = ", ".join(sorted(set(every["missing_kind"])))
        raise SystemExit(f"assertions without kind in current fixtures: {missing}")

    included_order = [key for key in observed_keys if key in included_keys]
    arm_names = sorted(every["arms"])
    group_names = [group for group in group_order(round_name, included_order, groups) if group in every["groups"]]
    scenario_keys = [key for key in scenario_order(round_name, included_order) if key in every["scenarios"]]
    data = {
        "iteration": args.iteration,
        "round": round_name,
        "skipped_unmarked_scenarios": [key for key in observed_keys if key not in included_keys],
        **summarize(every, arm_names, group_names, scenario_keys),
    }
    lines = [f"# Scores for iteration {args.iteration}", ""]
    if excluded:
        clean = tally(iteration_dir, eval_to_key, kinds, groups, included_keys, set(excluded))
        data["excluded_runs"] = excluded
        data["clean"] = summarize(clean, arm_names, group_names, scenario_keys)
        per_arm = {arm: every["arms"][arm]["runs"] - (clean["arms"].get(arm) or empty_slot())["runs"]
                   for arm in arm_names}
        lines += [f"All runs first, then the clean runs: {len(excluded)} runs that contamination.py flagged are left "
                  f"out of the clean tables ({', '.join(f'{arm} {n}' for arm, n in per_arm.items())}).", ""]
    lines += section_lines(data)
    if excluded:
        lines += [""] + section_lines(data["clean"], " (clean runs)")
    (iteration_dir / "scores.json").write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")
    (iteration_dir / "scores.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
