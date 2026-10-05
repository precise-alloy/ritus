"""Smoke test for the ported Ritus eval harness."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import build  # noqa: E402
from config import FIXTURE_DIR, REPO_ROOT, add_common_options, resolve_workspace  # noqa: E402


def parse_scenarios() -> int:
    count = 0
    for path in sorted((FIXTURE_DIR / "scenarios").glob("*/eval.json")):
        json.loads(path.read_text(encoding="utf-8"))
        count += 1
    missing = sorted({spec["key"] for spec in build.SCENARIOS.values()}
                     - {p.parent.name for p in (FIXTURE_DIR / "scenarios").glob("*/eval.json")})
    if missing:
        raise RuntimeError(f"SCENARIOS entries without eval.json: {missing}")
    return count


def check_ui_verdicts() -> None:
    import grade  # noqa: PLC0415

    produced = set(build.ui_verdicts({}, None, None))
    by_key = {spec["key"]: spec for spec in build.SCENARIOS.values()}
    problems = []
    for key in sorted(k for k in by_key if k.startswith("u")):
        declared = by_key[key].get("ui_verdicts")
        if declared is None:
            problems.append(f"{key}: missing ui_verdicts declaration")
            continue
        for name in declared:
            if name not in produced:
                problems.append(f"{key}: declared ui_verdicts verdict {name!r} is not produced by ui_verdicts()")
    for key, names in sorted(grade.AUTO_UI_VERDICTS.items()):
        declared = set(by_key.get(key, {}).get("ui_verdicts", ()))
        for name in names:
            if name not in declared:
                problems.append(f"{key}: auto grader reads undeclared UI verdict {name!r}")
    if problems:
        raise RuntimeError("UI verdict declaration mismatch:\n" + "\n".join(problems))


def run_static_check() -> str:
    proc = subprocess.run([sys.executable, str(ROOT / "static_check.py"), "--plugin-root", str(REPO_ROOT / "plugins" / "ritus"),
                           "--repo-root", str(REPO_ROOT)], capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    if proc.returncode != 0 or "PROBLEMS (0)" not in proc.stdout:
        raise RuntimeError("static_check.py failed\n" + proc.stdout + proc.stderr)
    return next(line for line in proc.stdout.splitlines() if line.startswith("PROBLEMS"))


def assert_provenance(name: str, value: dict | None) -> None:
    if not value:
        raise RuntimeError(f"setup.json missing {name} provenance")
    missing = [key for key in ("spec", "commit", "version", "tree_sha256") if key not in value]
    if missing:
        raise RuntimeError(f"setup.json {name} provenance missing keys: {missing}")


def check_web_run(run_dir: Path, *, expect_registry: bool = False) -> None:
    setup = json.loads((run_dir / "setup.json").read_text(encoding="utf-8"))
    repo = Path(setup["repo"])
    playwright_package = repo / "node_modules" / "playwright" / "package.json"
    if not playwright_package.is_file():
        raise RuntimeError(f"web world node_modules junction does not resolve {playwright_package}")
    assert_provenance("ritus", setup.get("ritus"))
    assert_provenance("companion", setup.get("companion"))
    if expect_registry:
        prompt = (run_dir / "prompt.md").read_text(encoding="utf-8")
        manifest = str(Path(setup["companion"]["path"]) / "ritus-companion.json")
        if manifest not in prompt:
            raise RuntimeError("main brief does not name the arm's own companion manifest")


def build_frontend_worlds() -> None:
    original = dict(build.ARM_SPECS)
    try:
        build.ARM_SPECS["old_skill"] = f"git:6c03d3a+dir:{REPO_ROOT / 'plugins' / 'ritus-frontend'}"
        plugins = build.plugin_copies(901, ["old_skill"])
        worker = build.build_run("eval-72-ui-verify-gap", "old_skill", 1, 901, datetime.now(), plugins)
        main = build.build_run("eval-79-ui-simple-empty", "old_skill", 1, 901, datetime.now(), plugins)
        check_web_run(worker)
        check_web_run(main, expect_registry=True)
    finally:
        build.ARM_SPECS = original


def main() -> int:
    parser = argparse.ArgumentParser()
    add_common_options(parser, arms=True)
    args = parser.parse_args()
    workspace = resolve_workspace(args.workspace) / "smoke"
    if workspace.exists():
        build.force_rmtree(workspace)
    try:
        build.configure_paths(workspace, build.parse_arm_specs(args.arm), web_modules=args.web_modules)
        scenario_count = parse_scenarios()
        check_ui_verdicts()
        static_line = run_static_check()
        plugins = build.plugin_copies(900, ["old_skill", "new_skill"])
        for arm, plugin in plugins.items():
            expected = plugin / "skills" / "verify-task" / "SKILL.md"
            if not expected.is_file():
                raise RuntimeError(f"{arm} did not build {expected}")
        build.build_run("eval-1-stale-helper", "old_skill", 1, 900, datetime.now(), plugins)
        build.build_run("eval-69-simple-oldrouting", "new_skill", 1, 900, datetime.now(), plugins)
        build_frontend_worlds()
        print(f"parsed {scenario_count} scenario files")
        print(static_line)
        print("built worker and main-thread worlds")
        print("built git:fcbd5d5 and dir:<repo>\\plugins\\ritus arms")
        print("built frontend composite web worker and main-thread worlds")
        return 0
    finally:
        if workspace.exists():
            build.force_rmtree(workspace)
        parent = workspace.parent
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()


if __name__ == "__main__":
    sys.exit(main())
