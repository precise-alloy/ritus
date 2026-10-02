"""Trigger eval in the real harness: which skill does Claude Code invoke first for a message, per arm.

  python trigger.py project                                   # build the shared tinyledger project dir (once)
  python trigger.py run --target-arm new_skill --runs 3 [--ids T1,D2] [--workers 6]
  Use --arm <name>=<spec> to configure arm sources, as in build.py.
  python trigger.py summary

Each call is `claude -p <query>` with only that arm's plugin loaded (--plugin-dir, --setting-sources project,local, so
the globally installed Ritus and other user-level plugins stay out). The Vertex auth variables from the user's
settings are passed through the environment because user settings are not loaded. A call stops at the first Skill
tool use, after MAX_TOOLS other tool uses, or at the final answer - whichever comes first.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import build  # noqa: E402
from config import FIXTURE_DIR, add_common_options, default_arms, resolve_workspace  # noqa: E402

EVAL_DIR = ROOT.parent
OUT = build.WORKSPACE / "iteration-4" / "trigger"
ARMS = default_arms()
AUTH_ENV = {k: v for k, v in os.environ.items() if k.startswith(("CLAUDE_", "ANTHROPIC_", "CLOUD_ML_"))}
EFFORT = os.environ.get("RITUS_EVAL_TRIGGER_EFFORT", "")
MODEL = os.environ.get("RITUS_EVAL_TRIGGER_MODEL", "")
MAX_TOOLS = 6
TIMEOUT = 240
lock = threading.Lock()


def project_paths() -> dict:
    return json.loads((OUT / "paths.json").read_text(encoding="utf-8"))


def make_project():
    """One tinyledger checkout with Ritus set up, plus a private copy of each arm's plugin."""
    OUT.mkdir(parents=True, exist_ok=True)
    root = build.AGENT_TMP / f"tt-{secrets.token_hex(3)}"
    repo = root / "tinyledger"
    repo.mkdir(parents=True)
    now = datetime.now()
    build.git(repo, "init", "-q", "-b", "main")
    for key, value in (("core.autocrlf", "false"), ("user.name", "Dev"), ("user.email", "dev@example.com"),
                       ("commit.gpgsign", "false")):
        build.git(repo, "config", key, value)
    for commit_id in build.FULL_HISTORY:
        commit = build.COMMITS[commit_id]
        build.materialize(repo, commit["layers"])
        build.git(repo, "add", "-A")
        build.git(repo, "commit", "-q", "-m", commit["msg"], env=build.commit_env(commit["days"], commit["author"], now))
    plugins = {}
    arm_names = list(ARMS)
    build.configure_paths(build.WORKSPACE, ARMS)
    copies = build.plugin_copies(4, arm_names)
    for arm, source in copies.items():
        dest = root / f"plugin-{arm}" / "ritus"
        shutil.copytree(source, dest)
        plugins[arm] = str(dest)
    (OUT / "paths.json").write_text(json.dumps({"root": str(root), "repo": str(repo), "plugins": plugins}, indent=2),
                                    encoding="utf-8")
    print(f"project {repo}")


ROUTING_NOTE = """\
## Ritus

This project uses the Ritus workflow plugin. Before changing code for a ticket, feature or change request, invoke the
`ritus:ticket-review` skill; for a bug, error, crash or failing test, invoke `ritus:debug` first; to review a branch or
PR, `ritus:pr-review`. Questions and explanations need no skill.
"""


ROUTING_NOTE_FIRM = """\
## Ritus workflow (this repository)

Work in this repository goes through the Ritus skills. For a request that matches one, invoke that skill as your
first action, before reading or searching any file:

- implementing or changing anything - a ticket, an issue link, a feature, a flag, a fee or config change:
  `ritus:ticket-review`
- a bug, error, crash, or failing or flaky test: `ritus:debug`
- reviewing a branch or PR: `ritus:pr-review`; review comments on a PR to fix: `ritus:address-feedback`
- comparing options before deciding: `ritus:brainstorm`

Questions, explanations and lookups need no skill.
"""
NOTES = {"routing": ROUTING_NOTE, "routing2": ROUTING_NOTE_FIRM}


def note_for_variant(name: str, paths: dict) -> str:
    if name in NOTES:
        return NOTES[name]
    if name in {"setupblock", "setupblock2"}:
        template = Path(paths["plugins"]["new_skill"]) / "skills" / "setup" / "templates" / "agent-routing.md"
        if not template.is_file():
            raise RuntimeError(f"setup routing template not found: {template}")
        return template.read_text(encoding="utf-8").replace("\r\n", "\n")
    raise RuntimeError(f"unknown variant {name!r}")


def make_variant(name: str):
    """Copy the shared project and add the routing note as CLAUDE.md (committed, like a team file)."""
    paths = project_paths()
    src = Path(paths["repo"])
    dest = src.parent / f"tinyledger-{name}"
    if not dest.exists():
        shutil.copytree(src, dest)
        (dest / "CLAUDE.md").write_text(note_for_variant(name, paths), encoding="utf-8", newline="\n")
        build.git(dest, "add", "CLAUDE.md")
        build.git(dest, "commit", "-q", "-m", "docs: Ritus routing note")
    paths.setdefault("variants", {})[name] = str(dest)
    (OUT / "paths.json").write_text(json.dumps(paths, indent=2), encoding="utf-8")
    print(f"variant {name}: {dest}")


def run_query(item: dict, arm: str, run_idx: int, paths: dict, variant: str | None = None) -> dict:
    cmd = ["claude", "-p", item["query"], "--plugin-dir", paths["plugins"][arm], "--setting-sources", "project,local",
           "--output-format", "stream-json", "--verbose", "--no-session-persistence"]
    if EFFORT:
        cmd.extend(["--effort", EFFORT])
    if MODEL:
        cmd.extend(["--model", MODEL])
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    env.update(AUTH_ENV)
    started = time.time()
    cwd = paths["variants"][variant] if variant else paths["repo"]
    proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            stdin=subprocess.DEVNULL)
    timer = threading.Timer(TIMEOUT, proc.kill)
    timer.start()
    result = {"id": item["id"], "arm": arm, "run": run_idx, "variant": variant, "expect": item["expect"], "tools": [],
              "skill": None,
              "stop": None, "model": None, "loaded_skills": None, "usage": []}
    try:
        for raw in proc.stdout:
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            kind = event.get("type")
            if kind == "system" and event.get("subtype") == "init":
                result["model"] = event.get("model")
                result["loaded_skills"] = event.get("skills") or event.get("slash_commands")
                result["plugins"] = event.get("plugins")
            elif kind == "assistant":
                message = event.get("message") or {}
                if message.get("usage"):
                    result["usage"].append(message["usage"])
                for block in message.get("content", []):
                    if block.get("type") != "tool_use":
                        continue
                    tool_input = block.get("input") or {}
                    result["tools"].append({"name": block.get("name"),
                                            "input": json.dumps(tool_input, ensure_ascii=False)[:300]})
                    if block.get("name") == "Skill" and not result["skill"]:
                        result["skill"] = tool_input.get("skill") or tool_input.get("command")
                if result["skill"]:
                    result["stop"] = "skill"
                    break
                if len(result["tools"]) >= MAX_TOOLS:
                    result["stop"] = "max_tools"
                    break
            elif kind == "result":
                result["final"] = str(event.get("result", ""))[:600]
                result["stop"] = "quota" if "429" in result["final"] or "Quota exceeded" in result["final"] else "final"
                result["cost_usd"] = event.get("total_cost_usd")
                break
    finally:
        timer.cancel()
        if proc.poll() is None:
            proc.kill()
        try:
            _, err = proc.communicate(timeout=20)
        except Exception:  # noqa: BLE001
            err = b""
        if not result["stop"]:
            result["stop"] = "timeout_or_exit"
            result["stderr"] = (err or b"").decode("utf-8", errors="replace")[-800:]
    result["seconds"] = round(time.time() - started, 1)
    with lock:
        with open(OUT / f"results-{arm}{'-' + variant if variant else ''}.jsonl", "a", encoding="utf-8") as handle:
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
    print(f"{arm} {item['id']} run {run_idx}: skill={result['skill']} stop={result['stop']} "
          f"tools={[t['name'] for t in result['tools']]} {result['seconds']}s", flush=True)
    return result


def run(arm: str, runs: int, ids: list[str], workers: int, variant: str | None = None):
    paths = project_paths()
    items = json.loads((FIXTURE_DIR / "trigger-queries.json").read_text(encoding="utf-8"))
    if ids:
        items = [i for i in items if i["id"] in ids]
    jobs = [(item, run_idx) for run_idx in range(1, runs + 1) for item in items]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(lambda job: run_query(job[0], arm, job[1], paths, variant), jobs))


def bare(skill: str | None) -> str | None:
    return skill.split(":")[-1] if skill else None


def judge(r: dict) -> dict:
    """direct: the specialist skill came first. engaged: a Ritus entry point for this path came first."""
    first = bare(r["skill"])
    ritus = r["skill"] is not None and (r["skill"].startswith("ritus:") or first in RITUS_NAMES)
    if r["expect"] is None:
        return {"pass": not ritus, "direct": not ritus, "engaged": not ritus}
    entry = {r["expect"], "start-ritus"}
    if r["arm"] == "old_skill" and r["expect"] == "ticket-review":
        entry.add("triage")
    return {"pass": ritus and first in entry, "direct": ritus and first == r["expect"],
            "engaged": ritus and first in entry}


RITUS_NAMES = {"address-feedback", "brainstorm", "comprehension", "debug", "execute-task", "migrate-docs", "pr-review",
               "repo-scan", "requirement-analysis", "setup", "start-ritus", "sync", "task-generation", "ticket-review",
               "triage", "verify-task", "wrap-up"}


def summary(variant: str | None = None):
    items = {i["id"]: i for i in json.loads((FIXTURE_DIR / "trigger-queries.json").read_text(encoding="utf-8"))}
    table = {}
    for arm in ARMS:
        path = OUT / f"results-{arm}{'-' + variant if variant else ''}.jsonl"
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r["stop"] in ("quota", "timeout_or_exit"):
                continue
            table.setdefault(r["id"], {}).setdefault(arm, []).append({**r, **judge(r)})
    print(f"{'id':4} {'expect':17} {'new: first skills':44} {'old: first skills':44}")
    totals = {arm: {"direct": 0, "engaged": 0, "n": 0, "neg_ok": 0, "neg_n": 0} for arm in ARMS}
    for qid in items:
        row = table.get(qid, {})
        cells = []
        for arm in ARMS:
            runs = row.get(arm, [])
            cells.append(",".join(bare(r["skill"]) or f"-({r['stop']})" for r in runs))
            for r in runs:
                t = totals[arm]
                if r["expect"] is None:
                    t["neg_n"] += 1
                    t["neg_ok"] += r["pass"]
                else:
                    t["n"] += 1
                    t["direct"] += r["direct"]
                    t["engaged"] += r["engaged"]
        print(f"{qid:4} {str(items[qid]['expect']):17} {cells[0]:44} {cells[1]:44}")
    for arm, t in totals.items():
        print(f"{arm}: should-trigger direct {t['direct']}/{t['n']}, engaged {t['engaged']}/{t['n']}; "
              f"should-not-trigger clean {t['neg_ok']}/{t['neg_n']}")


def main():
    global OUT, ARMS
    common = argparse.ArgumentParser(add_help=False)
    add_common_options(common, arms=True)
    parser = argparse.ArgumentParser(parents=[common])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("project", parents=[common])
    r = sub.add_parser("run", parents=[common])
    r.add_argument("--target-arm", required=True, help="Arm name to run")
    r.add_argument("--runs", type=int, default=3)
    r.add_argument("--ids", default="")
    r.add_argument("--workers", type=int, default=6)
    r.add_argument("--variant", default=None)
    v = sub.add_parser("variant", parents=[common])
    v.add_argument("name")
    sm = sub.add_parser("summary", parents=[common])
    sm.add_argument("--variant", default=None)
    args = parser.parse_args()
    build.configure_paths(resolve_workspace(args.workspace), build.parse_arm_specs(args.arm))
    OUT = build.WORKSPACE / "iteration-4" / "trigger"
    ARMS = build.ARM_SPECS
    if args.cmd == "project":
        make_project()
    elif args.cmd == "run":
        run(args.target_arm, args.runs, [i for i in args.ids.split(",") if i], args.workers, args.variant)
    elif args.cmd == "variant":
        make_variant(args.name)
    else:
        summary(args.variant)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
