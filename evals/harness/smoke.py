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


def run_static_check() -> str:
    proc = subprocess.run([sys.executable, str(ROOT / "static_check.py"), "--plugin-root", str(REPO_ROOT / "plugin"),
                           "--repo-root", str(REPO_ROOT)], capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    if proc.returncode != 0 or "PROBLEMS (0)" not in proc.stdout:
        raise RuntimeError("static_check.py failed\n" + proc.stdout + proc.stderr)
    return next(line for line in proc.stdout.splitlines() if line.startswith("PROBLEMS"))


def main() -> int:
    parser = argparse.ArgumentParser()
    add_common_options(parser, arms=True)
    args = parser.parse_args()
    workspace = resolve_workspace(args.workspace) / "smoke"
    if workspace.exists():
        build.force_rmtree(workspace)
    try:
        build.configure_paths(workspace, build.parse_arm_specs(args.arm))
        scenario_count = parse_scenarios()
        static_line = run_static_check()
        plugins = build.plugin_copies(900, ["old_skill", "new_skill"])
        for arm, plugin in plugins.items():
            expected = plugin / "skills" / "verify-task" / "SKILL.md"
            if not expected.is_file():
                raise RuntimeError(f"{arm} did not build {expected}")
        build.build_run("eval-1-stale-helper", "old_skill", 1, 900, datetime.now(), plugins)
        build.build_run("eval-69-simple-oldrouting", "new_skill", 1, 900, datetime.now(), plugins)
        print(f"parsed {scenario_count} scenario files")
        print(static_line)
        print("built worker and main-thread worlds")
        print("built git:fcbd5d5 and dir:plugin arms")
        return 0
    finally:
        if workspace.exists():
            build.force_rmtree(workspace)
        parent = workspace.parent
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()


if __name__ == "__main__":
    sys.exit(main())
