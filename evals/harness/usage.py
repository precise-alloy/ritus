"""Fill each run's timing.json with real token usage and wall time.

Copilot CLI records every model call in the local session store
(~/.copilot/session-store.db, table assistant_usage_events) with the calling
subagent's agent_id. The task-completion notification in this harness carries no
usage data, so this script reads the store instead (read-only).

Usage:
  python usage.py --iteration 1 [--session <copilot-session-id>]

Needs iteration-N/agents.json: {agent_name: agent_id}, taken from list_agents.
A refused launch is rerun as "<name>-r", then "<name>-r2", ...; the last attempt
is the measured run and the refused ones are recorded separately.
"""
import argparse
import json
import sqlite3
import statistics as st
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from config import add_common_options, resolve_session_dir, resolve_session_id, resolve_session_store, resolve_workspace  # noqa: E402

WORKSPACE = resolve_workspace(None)
STORE = resolve_session_store(None)
DEFAULT_SESSION = resolve_session_id(None)


def ts(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def usage_for(conn, session_id: str, agent_id: str) -> dict | None:
    rows = conn.execute(
        """SELECT created_at, duration_ms, input_tokens, output_tokens, cache_read_tokens,
                  reasoning_tokens, model
           FROM assistant_usage_events WHERE session_id = ? AND agent_id = ?""",
        (session_id, agent_id),
    ).fetchall()
    if not rows:
        return None
    start = min(ts(r[0]) - (r[1] or 0) / 1000 for r in rows)
    end = max(ts(r[0]) for r in rows)
    inp = sum(r[2] or 0 for r in rows)
    out = sum(r[3] or 0 for r in rows)
    cached = sum(r[4] or 0 for r in rows)
    return {
        "api_calls": len(rows),
        "input_tokens": inp,
        "output_tokens": out,
        "cache_read_tokens": cached,
        "uncached_input_tokens": inp - cached,
        "reasoning_tokens": sum(r[5] or 0 for r in rows),
        "total_tokens": inp + out,
        "wall_seconds": round(end - start, 1),
        "model_seconds": round(sum(r[1] or 0 for r in rows) / 1000, 1),
        "models": sorted({r[6] for r in rows}),
    }


def tree_timing(conn, session_id: str, run_dir: Path, setup: dict, events) -> dict | None:
    """Main-thread runs: usage summed over the run agent and every agent it started, with a per-role breakdown."""
    name = Path(setup["agent_root"]).name
    attempts = [a for a in [name, f"{name}-r", *(f"{name}-r{n}" for n in range(2, 10))] if events.by_name(a)]
    if not attempts:
        return None
    root = events.by_name(attempts[-1])
    tree = events.tree(root["id"])
    per_role, total = {}, None
    for node in tree:
        u = usage_for(conn, session_id, node["id"])
        if not u:
            continue
        role = node["role"]
        agg = per_role.setdefault(role, {"agents": 0, "total_tokens": 0, "api_calls": 0})
        agg["agents"] += 1
        agg["total_tokens"] += u["total_tokens"]
        agg["api_calls"] += u["api_calls"]
        if total is None:
            total = {k: u[k] for k in ("input_tokens", "output_tokens", "cache_read_tokens", "uncached_input_tokens",
                                       "reasoning_tokens", "total_tokens", "api_calls", "model_seconds")}
            total["models"] = set(u["models"])
        else:
            for k in ("input_tokens", "output_tokens", "cache_read_tokens", "uncached_input_tokens",
                      "reasoning_tokens", "total_tokens", "api_calls", "model_seconds"):
                total[k] += u[k]
            total["models"] |= set(u["models"])
    root_usage = usage_for(conn, session_id, root["id"])
    if not total or not root_usage:
        return None
    turns = json.loads((run_dir / "turns.json").read_text(encoding="utf-8")) if (run_dir / "turns.json").exists() else []
    from events import active_seconds
    active = active_seconds(root["id"], events.path) or root_usage["wall_seconds"]
    return {
        "total_tokens": total["total_tokens"],
        "duration_ms": int(active * 1000),
        "total_duration_seconds": active,
        "wall_first_to_last_call_seconds": root_usage["wall_seconds"],
        **{k: total[k] for k in ("input_tokens", "output_tokens", "cache_read_tokens", "uncached_input_tokens",
                                 "reasoning_tokens", "api_calls")},
        "model_seconds": round(total["model_seconds"], 1),
        "models": sorted(total["models"]),
        "agent": attempts[-1],
        "subagents": len(tree) - 1,
        "per_role": per_role,
        "developer_turns": len(turns),
        "source": "tokens: session-store assistant_usage_events summed over the run agent and its descendants; "
                  "duration: the run agent's active time (each turn from the developer message to its last turn_end, "
                  "so waiting for the simulated developer is excluded; nested agents run inside it)",
        **({"refused_attempts": attempts[:-1]} if len(attempts) > 1 else {}),
    }


def main():
    ap = argparse.ArgumentParser()
    add_common_options(ap)
    ap.add_argument("--iteration", type=int, required=True)
    ap.add_argument("--session", default=None, help="Deprecated alias for --session-id")
    args = ap.parse_args()

    global WORKSPACE, STORE
    WORKSPACE = resolve_workspace(args.workspace)
    STORE = resolve_session_store(args.session_store)
    session_id = args.session or resolve_session_id(args.session_id)
    if not session_id:
        sys.exit("pass --session-id or set RITUS_EVAL_SESSION_ID")
    iteration_dir = WORKSPACE / f"iteration-{args.iteration}"
    conn = sqlite3.connect(f"file:{STORE.as_posix()}?mode=ro", uri=True)
    if args.iteration >= 5:
        sys.path.insert(0, str(HERE))
        from events import Events
        events = Events(resolve_session_dir(args.session_dir))
        rows = defaultdict(lambda: defaultdict(list))
        for setup_file in sorted(iteration_dir.glob("eval-*/*/run-*/setup.json")):
            run_dir = setup_file.parent
            setup = json.loads(setup_file.read_text(encoding="utf-8"))
            timing = tree_timing(conn, session_id, run_dir, setup, events)
            if timing is None:
                print(f"no usage for {run_dir}")
                continue
            (run_dir / "timing.json").write_text(json.dumps(timing, indent=2), encoding="utf-8")
            rows[setup["eval"]][setup["arm"]].append(timing)
        print(f"{'eval':30} {'arm':10} {'tokens(k)':>24} {'subagents':>10} {'turns':>8} {'wall s':>18}")
        for ev in sorted(rows):
            for arm in sorted(rows[ev]):
                rs = rows[ev][arm]
                print(f"{ev:30} {arm:10} {'/'.join(f'{r['total_tokens'] / 1000:.0f}' for r in rs):>24} "
                      f"{'/'.join(str(r['subagents']) for r in rs):>10} {'/'.join(str(r['developer_turns']) for r in rs):>8} "
                      f"{'/'.join(f'{r['total_duration_seconds']:.0f}' for r in rs):>18}")
        return
    agents = json.loads((iteration_dir / "agents.json").read_text(encoding="utf-8"))

    table = defaultdict(lambda: defaultdict(list))
    for setup_file in sorted(iteration_dir.glob("eval-*/*/run-*/setup.json")):
        run_dir = setup_file.parent
        setup = json.loads(setup_file.read_text(encoding="utf-8"))
        name = Path(setup["agent_root"]).name
        attempts = [a for a in [name, f"{name}-r", *(f"{name}-r{n}" for n in range(2, 10))] if a in agents]
        if not attempts:
            sys.exit(f"no agent id for {name} ({run_dir})")
        measured, refused_names = attempts[-1], attempts[:-1]
        usage = usage_for(conn, session_id, agents[measured])
        if usage is None:
            sys.exit(f"no usage rows for {measured} ({run_dir})")

        timing_file = run_dir / "timing.json"
        old = json.loads(timing_file.read_text(encoding="utf-8")) if timing_file.exists() else {}
        timing = {
            "total_tokens": usage["total_tokens"],
            "duration_ms": int(usage["wall_seconds"] * 1000),
            "total_duration_seconds": usage["wall_seconds"],
            **{k: usage[k] for k in ("input_tokens", "output_tokens", "cache_read_tokens",
                                     "uncached_input_tokens", "reasoning_tokens", "api_calls",
                                     "model_seconds", "models")},
            "agent": measured,
            "source": "session-store assistant_usage_events by agent_id; "
                      "total_tokens = input + output summed over calls (input includes cache reads)",
            "read_agent_elapsed_seconds": old.get("read_agent_elapsed_seconds",
                                                  old.get("total_duration_seconds")),
        }
        if refused_names:
            timing["refused_attempts"] = [{"agent": a, **(usage_for(conn, session_id, agents[a]) or {})}
                                          for a in refused_names]
        timing_file.write_text(json.dumps(timing, indent=2), encoding="utf-8")

        cell = table[setup["eval"]][setup["arm"]]
        cell.append(timing)

    print(f"{'eval':34} {'arm':10} {'tokens(k)':>22} {'uncached(k)':>18} {'calls':>12} {'wall s':>16}")
    for ev in sorted(table):
        for arm in sorted(table[ev]):
            runs = table[ev][arm]
            fmt = lambda key, scale=1: "/".join(f"{r[key] / scale:.0f}" for r in runs)
            print(f"{ev:34} {arm:10} {fmt('total_tokens', 1000):>22} {fmt('uncached_input_tokens', 1000):>18} "
                  f"{fmt('api_calls'):>12} {fmt('total_duration_seconds'):>16}")
    for arm in ("new_skill", "old_skill"):
        runs = [r for ev in table.values() for r in ev.get(arm, [])]
        print(f"{arm}: tokens mean {st.mean(r['total_tokens'] for r in runs) / 1000:.0f}k, "
              f"uncached mean {st.mean(r['uncached_input_tokens'] for r in runs) / 1000:.1f}k, "
              f"output mean {st.mean(r['output_tokens'] for r in runs) / 1000:.1f}k, "
              f"calls mean {st.mean(r['api_calls'] for r in runs):.1f}, "
              f"wall mean {st.mean(r['total_duration_seconds'] for r in runs):.0f}s, "
              f"models {sorted({m for r in runs for m in r['models']})}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
