"""Read this Copilot session's events.jsonl: the agent tree, prompts and tool calls behind each eval run.

Every subagent - the run's own agent and anything it starts - logs its events here with its agentId, and nested agents
carry a parentId, so one run's whole tree can be rebuilt from the run agent's name.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from config import resolve_session_dir  # noqa: E402

SESSION_DIR = resolve_session_dir(None)


def events_file(path: Path | str | None) -> Path | None:
    """The session's events.jsonl, given the session dir or the file itself."""
    if path is None:
        return None
    path = Path(path)
    return path / "events.jsonl" if path.is_dir() else path


EVENTS = events_file(SESSION_DIR)
INTERESTING = (b'"subagent.started"', b'"subagent.completed"', b'"subagent.failed"', b'"tool.execution_start"')
SKILL_RE = re.compile(r"skills[\\/]+([a-z][a-z0-9-]*)[\\/]+SKILL\.md", re.I)

ROLE_PATTERNS = [
    ("pr-review", r"\bpr-review\b"),
    ("verify-task", r"\bverify-task\b"),
    ("execute-task", r"\bexecute-task\b"),
    ("requirement-analysis", r"\brequirement-analysis\b"),
    ("task-generation", r"\btask-generation\b"),
    ("analysis", r"analysis-brief|\banalysis\b"),
]


def role_of(prompt: str, name: str) -> str:
    """Classify a subagent by the skill its brief names; the first skill named decides ties."""
    text = f"{name}\n{prompt}"
    hits = []
    for role, pattern in ROLE_PATTERNS:
        match = re.search(pattern, text, re.I)
        if match:
            hits.append((match.start(), role))
    return min(hits)[1] if hits else "other"


class Events:
    def __init__(self, path: Path | None = None):
        global EVENTS
        path = events_file(path) or EVENTS
        if path is None:
            raise RuntimeError("pass --session-dir or set RITUS_EVAL_SESSION_DIR for events.jsonl")
        # replies() and active_seconds() fall back to the file the caller's --session-dir named.
        EVENTS = EVENTS or path
        self.path = path
        self.agents: dict[str, dict] = {}
        self.calls: dict[str, dict] = {}
        self.tools: dict[str, list[dict]] = {}
        with open(path, "rb") as handle:
            for raw in handle:
                if not any(key in raw for key in INTERESTING):
                    continue
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                kind = event.get("type")
                data = event.get("data") or {}
                agent = event.get("agentId") or data.get("agentId")
                stamp = event.get("timestamp")
                if kind == "subagent.started" and agent:
                    self.agents[agent] = {"id": agent, "parent": data.get("parentId"),
                                          "name": data.get("agentDisplayName"), "type": data.get("agentType"),
                                          "description": data.get("agentDescription"), "model": data.get("model"),
                                          "mode": data.get("executionMode"), "tool_call_id": data.get("toolCallId"),
                                          "started_at": stamp}
                elif kind in ("subagent.completed", "subagent.failed") and agent in self.agents:
                    self.agents[agent].update(ended=kind.split(".")[1], ended_at=stamp,
                                              total_tokens=data.get("totalTokens"),
                                              tool_calls=data.get("totalToolCalls"),
                                              duration_ms=data.get("durationMs"))
                elif kind == "tool.execution_start":
                    entry = {"tool": data.get("toolName"), "args": data.get("arguments") or {},
                             "call_id": data.get("toolCallId"), "at": stamp}
                    self.calls[entry["call_id"]] = {"agent": agent, **entry}
                    self.tools.setdefault(agent or "main", []).append(entry)

    def by_name(self, name: str) -> dict | None:
        """The last top-level agent started with this display name."""
        found = [a for a in self.agents.values() if a["name"] == name and not a["parent"]]
        return found[-1] if found else None

    def children(self, agent_id: str) -> list[dict]:
        return sorted((a for a in self.agents.values() if a["parent"] == agent_id), key=lambda a: a["started_at"] or "")

    def tree(self, agent_id: str) -> list[dict]:
        """The agent and all its descendants, depth first, each with its brief and role."""
        out = []

        def walk(node: dict, depth: int):
            call = self.calls.get(node["tool_call_id"]) or {}
            args = call.get("args") if isinstance(call.get("args"), dict) else {}
            prompt = args.get("prompt", "")
            out.append({**node, "depth": depth, "prompt": prompt,
                        "requested_mode": args.get("mode"),
                        "requested_model": args.get("model"), "requested_effort": args.get("reasoning_effort"),
                        "role": "run" if depth == 0 else role_of(prompt, node["name"] or "")})
            for child in self.children(node["id"]):
                walk(child, depth + 1)

        walk(self.agents[agent_id], 0)
        return out

    def commands(self, agent_id: str) -> list[str]:
        """Shell commands and file reads of one agent, in order, as short strings."""
        out = []
        for entry in self.tools.get(agent_id, []):
            args = entry["args"] if isinstance(entry["args"], dict) else {"input": entry["args"]}
            if entry["tool"] == "powershell":
                out.append("$ " + str(args.get("command", "")))
            elif entry["tool"] in ("view", "read"):
                out.append("view " + str(args.get("path", "")))
            elif entry["tool"] == "task":
                out.append(f"task {args.get('name')} ({args.get('agent_type')}, mode={args.get('mode')})")
            elif entry["tool"] in ("write_agent", "read_agent"):
                out.append(f"{entry['tool']} {args.get('agent_id')}")
            elif entry["tool"] in ("apply_patch", "edit", "create"):
                target = args.get("path") or re.findall(r"\*\*\* (?:Update|Add|Delete) File: (.+)", str(args.get("input", "")))
                out.append(f"{entry['tool']} {target}")
            else:
                out.append(f"{entry['tool']} {json.dumps(args, ensure_ascii=False)[:160]}")
        return out

    def skills_read(self, agent_id: str, plugin_root: str) -> list[str]:
        """Ritus skills this agent opened from the arm's plugin copy, in first-read order."""
        root = plugin_root.lower().replace("/", "\\")
        seen = []
        for entry in self.tools.get(agent_id, []):
            text = json.dumps(entry["args"], ensure_ascii=False).replace("\\\\", "\\").lower()
            if root not in text and "skills" not in text:
                continue
            for name in SKILL_RE.findall(text):
                if name not in seen:
                    seen.append(name)
        return seen


def replies(agent_ids: set[str], path: Path | None = None) -> dict[str, list[str]]:
    """Per agent, the final assistant message of each user turn (what read_agent shows as the response)."""
    path = events_file(path) or EVENTS
    if path is None:
        raise RuntimeError("pass --session-dir or set RITUS_EVAL_SESSION_DIR for events.jsonl")
    out: dict[str, list[str]] = {a: [] for a in agent_ids}
    last: dict[str, str | None] = {a: None for a in agent_ids}
    keys = [a.encode() for a in agent_ids]
    with open(path, "rb") as handle:
        for raw in handle:
            if b'"user.message"' not in raw and b'"assistant.message"' not in raw:
                continue
            if not any(k in raw for k in keys):
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            data = event.get("data") or {}
            agent = event.get("agentId") or data.get("agentId")
            if agent not in out:
                continue
            if event.get("type") == "user.message":
                if last[agent] is not None or out[agent]:
                    out[agent].append(last[agent] or "")
                last[agent] = ""
            elif event.get("type") == "assistant.message":
                content = data.get("content")
                if isinstance(content, list):
                    content = "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
                if content and str(content).strip():
                    last[agent] = str(content)
    for agent in out:
        if last[agent] is not None:
            out[agent].append(last[agent])
    return out


def active_seconds(agent_id: str, path: Path | None = None) -> float:
    """Sum over the agent's turns of (last turn_end - the user message that started the turn)."""
    path = events_file(path) or EVENTS
    if path is None:
        raise RuntimeError("pass --session-dir or set RITUS_EVAL_SESSION_DIR for events.jsonl")
    from datetime import datetime

    def ts(value: str) -> float:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()

    key = agent_id.encode()
    total, start, end = 0.0, None, None
    with open(path, "rb") as handle:
        for raw in handle:
            if key not in raw or (b'"user.message"' not in raw and b'"assistant.turn_end"' not in raw):
                continue
            event = json.loads(raw)
            data = event.get("data") or {}
            if (event.get("agentId") or data.get("agentId")) != agent_id or not event.get("timestamp"):
                continue
            if event["type"] == "user.message":
                if start is not None and end is not None:
                    total += max(0.0, end - start)
                start, end = ts(event["timestamp"]), None
            elif event["type"] == "assistant.turn_end":
                end = ts(event["timestamp"])
    if start is not None and end is not None:
        total += max(0.0, end - start)
    return round(total, 1)
