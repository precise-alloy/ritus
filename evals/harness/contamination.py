"""Flag runs that may have measured something other than their arm.

  python contamination.py --iteration 26 --session-dir <session-state dir> [--workspace evals\\workspace]

A run should read workflow skills only from its arm's plugin copy, and files only from its own world. Three things
break that, in the run agent or any subagent it started:

- a `skill` tool call that loaded a skill: the tool loads the installed plugin's copy, not the arm's (a name the
  installed plugin lacks fails and loads nothing, so it is listed but doesn't count);
- a path outside the run's world and its arm's plugin copy: another world, the repository, the workspace, or the
  installed plugins;
- a search (grep, glob, rg) with no path, which searches from the session's working directory.

Writes iteration-N/contamination.json. scores.py then reports every run and the clean runs. Launches the runtime
refused for its concurrent-agent limit are listed too; they change how a run went but do not mix in another version,
so they don't exclude a run.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from config import REPO_ROOT, add_common_options, resolve_session_dir, resolve_workspace  # noqa: E402
from events import Events  # noqa: E402

INSTALLED = Path.home() / ".copilot" / "installed-plugins"
PATH_RE = re.compile(r"[A-Za-z]:[\\/][^\s'\"`|;,)*?<>]+")
SEARCH_TOOLS = ("grep", "glob", "rg")
REFUSED = b"Maximum concurrent agent limit"
COMPLETE = b'"tool.execution_complete"'
CALL_ID_RE = re.compile(rb'"toolCallId"\s*:\s*"([^"]+)"')


def norm(path: str | Path) -> str:
    return str(path).replace("/", "\\").lower().rstrip("\\.")


def strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in strings(v)]
    return []


def run_agent(events: Events, name: str) -> dict | None:
    """The run's agent; a relaunch (`<name>-r`, `<name>-r2`...) replaces the first launch, as in collect."""
    agent = None
    for attempt in [name, f"{name}-r", *(f"{name}-r{i}" for i in range(2, 10))]:
        agent = events.by_name(attempt) or agent
    return agent


def outside_paths(text: str, allowed: list[str], watched: list[str], listing: set[str]) -> list[str]:
    hits = []
    for path in PATH_RE.findall(text):
        low = norm(path)
        if low in listing or any(low == a or low.startswith(a + "\\") for a in allowed):
            continue
        if any(low == w or low.startswith(w + "\\") for w in watched):
            hits.append(path)
    return hits


def check(iteration: int, workspace: Path, session_dir: Path | None) -> dict:
    iteration_dir = workspace / f"iteration-{iteration}"
    events = Events(session_dir)
    watched = [norm(REPO_ROOT), norm(workspace), norm(INSTALLED)]
    listing = {norm(REPO_ROOT), norm(workspace), norm(workspace / ".agents")}
    found, missing, owner, skill_calls = {}, [], {}, {}
    setups = sorted(iteration_dir.glob("eval-*/*/run-*/setup.json"))
    for setup_path in setups:
        setup = json.loads(setup_path.read_text(encoding="utf-8"))
        run_rel = setup_path.parent.relative_to(iteration_dir).as_posix()
        name = Path(setup["agent_root"]).name
        agent = run_agent(events, name)
        if not agent:
            missing.append(run_rel)
            continue
        allowed = [norm(setup["agent_root"]), norm(Path(setup["plugin"]).parent)]
        info = {"agent_root": name, "skills": [], "outside": [], "unscoped_search": []}
        for node in events.tree(agent["id"]):
            owner[node["id"]] = run_rel
            for call in events.tools.get(node["id"], []):
                args = call["args"] if isinstance(call["args"], dict) else {"input": call["args"]}
                if call["tool"] == "skill":
                    entry = {"depth": node["depth"], "skill": args.get("skill"), "loaded": None}
                    skill_calls[call["call_id"]] = entry
                    info["skills"].append(entry)
                if call["tool"] in SEARCH_TOOLS and not (args.get("paths") or args.get("path")):
                    info["unscoped_search"].append({"depth": node["depth"], "tool": call["tool"],
                                                    "pattern": str(args.get("pattern", ""))[:80]})
                text = "\n".join(strings(args))
                for path in outside_paths(text, allowed, watched, listing):
                    info["outside"].append({"depth": node["depth"], "tool": call["tool"], "path": path[:200]})
        found[run_rel] = info
    refused = {}
    with open(events.path, "rb") as handle:
        for raw in handle:
            if COMPLETE in raw and any(cid.decode() in skill_calls for cid in CALL_ID_RE.findall(raw)):
                data = json.loads(raw).get("data") or {}
                if data.get("toolCallId") in skill_calls:
                    skill_calls[data["toolCallId"]]["loaded"] = data.get("success") is True
            if REFUSED in raw:
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                agent_id = event.get("agentId") or (event.get("data") or {}).get("agentId")
                if agent_id in owner:
                    refused[owner[agent_id]] = refused.get(owner[agent_id], 0) + 1
    flagged, failed_skill_calls = {}, {}
    for run_rel, info in found.items():
        # A call with no completion recorded counts as a load: unknown is not clean.
        if any(s["loaded"] is not False for s in info["skills"]) or info["outside"] or info["unscoped_search"]:
            flagged[run_rel] = {**info, "outside": info["outside"][:20],
                                "unscoped_search": info["unscoped_search"][:20]}
        elif info["skills"]:
            failed_skill_calls[run_rel] = [s["skill"] for s in info["skills"]]
    return {"iteration": iteration, "runs": len(setups), "contaminated": flagged,
            "failed_skill_calls": failed_skill_calls, "refused_launches": dict(sorted(refused.items())),
            "agent_not_found": missing}


def main() -> int:
    parser = argparse.ArgumentParser()
    add_common_options(parser)
    parser.add_argument("--iteration", type=int, required=True)
    args = parser.parse_args()
    workspace = resolve_workspace(args.workspace)
    result = check(args.iteration, workspace, resolve_session_dir(args.session_dir))
    out = workspace / f"iteration-{args.iteration}" / "contamination.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=True), encoding="utf-8")
    flagged = result["contaminated"]
    loads = sum(1 for info in flagged.values() if any(s["loaded"] is not False for s in info["skills"]))
    outside = sum(1 for info in flagged.values() if info["outside"])
    unscoped = sum(1 for info in flagged.values() if info["unscoped_search"])
    print(f"{out}: {len(flagged)}/{result['runs']} runs contaminated (skill loads {loads}, outside paths "
          f"{outside}, unscoped searches {unscoped}); failed skill calls only in "
          f"{len(result['failed_skill_calls'])} runs; refused launches in {len(result['refused_launches'])} runs; "
          f"agent not found for {len(result['agent_not_found'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
