from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STUB = ROOT / "figma_stub.mjs"
DESIGN = ROOT.parent / "fixture" / "web" / "design"
GUIDANCE = DESIGN / "figma-design-to-code" / "SKILL.md"
RESOURCE = "skill://figma/figma-design-to-code/SKILL.md"


def normalize_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Client:
    def __init__(self) -> None:
        self.proc = subprocess.Popen(
            ["node", str(STUB)],
            cwd=ROOT.parent.parent,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.next_id = 1

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=10)

    def request(self, method: str, params: dict | None = None) -> dict:
        request = {"jsonrpc": "2.0", "id": self.next_id, "method": method}
        self.next_id += 1
        if params is not None:
            request["params"] = params
        assert self.proc.stdin is not None
        assert self.proc.stdout is not None
        self.proc.stdin.write(json.dumps(request) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise AssertionError(f"no response for {method}; process exited {self.proc.poll()}")
        return json.loads(line)

    def notify(self, method: str, params: dict | None = None) -> None:
        request = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            request["params"] = params
        assert self.proc.stdin is not None
        self.proc.stdin.write(json.dumps(request) + "\n")
        self.proc.stdin.flush()


def result(response: dict) -> dict:
    if "error" in response:
        raise AssertionError(response["error"])
    return response.get("result") or {}


def text_content(response: dict) -> str:
    content = result(response).get("content") or []
    for item in content:
        if item.get("type") == "text":
            return item.get("text", "")
    raise AssertionError(f"no text content in {response}")


def tool(client: Client, name: str, args: dict) -> dict:
    return result(client.request("tools/call", {"name": name, "arguments": args}))


def pass_fail(name: str, fn) -> bool:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 - check script reports all failures.
        print(f"FAIL {name}: {exc}")
        return False
    print(f"PASS {name}")
    return True


def run_session() -> bool:
    client = Client()
    ok = True
    try:
        ok &= pass_fail("initialize", lambda: _check_initialize(client))
        ok &= pass_fail("notifications/initialized", lambda: client.notify("notifications/initialized"))
        ok &= pass_fail("tools/list", lambda: _check_tools(client))
        for name in ["get_design_context", "get_variable_defs", "get_metadata", "get_screenshot", "get_code_connect_map"]:
            ok &= pass_fail(name, lambda name=name: _check_tool(client, name))
        ok &= pass_fail("get_design_context accepts URL node id", lambda: _check_context_dash(client))
        ok &= pass_fail("unknown node", lambda: _check_unknown_node(client))
        ok &= pass_fail("unknown file key", lambda: _check_unknown_file(client))
        ok &= pass_fail("resources/list", lambda: _check_resources_list(client))
        ok &= pass_fail("resources/read", lambda: _check_resources_read(client))
        ok &= pass_fail("unknown method", lambda: _check_unknown_method(client))
    finally:
        client.close()
    return ok


def _check_initialize(client: Client) -> None:
    value = result(client.request("initialize", {"protocolVersion": "2025-06-18"}))
    assert value["protocolVersion"] == "2025-06-18"
    assert "tools" in value["capabilities"] and "resources" in value["capabilities"]
    assert value["serverInfo"]["name"] == "figma-stand-in"


def _check_tools(client: Client) -> None:
    tools = result(client.request("tools/list"))["tools"]
    names = {item["name"] for item in tools}
    assert names == {"get_design_context", "get_variable_defs", "get_metadata", "get_screenshot", "get_code_connect_map"}
    assert all(item.get("inputSchema", {}).get("required") == ["nodeId"] for item in tools)


def _check_tool(client: Client, name: str) -> None:
    value = tool(client, name, {"fileKey": "TLWEB0001", "nodeId": "12:34", "clientLanguages": ["JavaScript"]})
    assert not value.get("isError"), value
    if name == "get_design_context":
        assert "var(--color-surface, #FFFFFF)" in value["content"][0]["text"]
        assert "Adapt it to the project's existing components" in value["content"][0]["text"]
    elif name == "get_variable_defs":
        data = json.loads(value["content"][0]["text"])
        assert data["color/surface"] == "#FFFFFF" and data["space/4"] == 16
    elif name == "get_metadata":
        text = value["content"][0]["text"]
        assert 'id="12:34"' in text and 'name="Total balance card"' in text
    elif name == "get_screenshot":
        image = value["content"][0]
        assert image["type"] == "image" and image["mimeType"] == "image/png"
        assert base64.b64decode(image["data"]).startswith(b"\x89PNG\r\n\x1a\n")
    elif name == "get_code_connect_map":
        assert value["content"][0]["text"] == "{}"


def _check_context_dash(client: Client) -> None:
    assert "Total balance" in text_content(client.request("tools/call", {"name": "get_design_context", "arguments": {"nodeId": "12-34"}}))


def _check_unknown_node(client: Client) -> None:
    value = tool(client, "get_metadata", {"nodeId": "99:99"})
    assert value.get("isError") is True
    assert value["content"][0]["text"] == "Node 99:99 not found in file TLWEB0001"


def _check_unknown_file(client: Client) -> None:
    value = tool(client, "get_metadata", {"fileKey": "BAD", "nodeId": "12:34"})
    assert value.get("isError") is True
    assert "File BAD not found" in value["content"][0]["text"]


def _check_resources_list(client: Client) -> None:
    resources = result(client.request("resources/list"))["resources"]
    assert resources == [{"uri": RESOURCE, "name": "figma-design-to-code/SKILL.md", "mimeType": "text/markdown"}]


def _check_resources_read(client: Client) -> None:
    contents = result(client.request("resources/read", {"uri": RESOURCE}))["contents"]
    assert contents[0]["uri"] == RESOURCE
    assert contents[0]["text"] == GUIDANCE.read_text(encoding="utf-8")


def _check_unknown_method(client: Client) -> None:
    response = client.request("not/a_method")
    assert response["error"]["code"] == -32601


def check_installed(path: Path) -> bool:
    fixture_text = normalize_text(GUIDANCE)
    installed_text = normalize_text(path)
    fixture_hash = sha256_text(fixture_text)
    installed_hash = sha256_text(installed_text)
    print(f"fixture sha256 {fixture_hash}")
    print(f"installed sha256 {installed_hash}")
    if fixture_hash != installed_hash:
        print(f"FAIL installed-skill: {path} does not match fixture guidance")
        return False
    print("PASS installed-skill")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--installed-skill", type=Path)
    args = parser.parse_args()
    ok = run_session()
    if args.installed_skill is not None:
        ok = check_installed(args.installed_skill) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
