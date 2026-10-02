"""Copy a finished iteration's summary into evals/results/<name>/, scrubbed of machine data.

  python publish.py --iteration 26 --name v2-vs-v3 [--workspace evals\\workspace]

Copies benchmark.json, benchmark.md, analyst.json and scores.md, whichever exist. Paths under the repository become
<repo>, the temp and AppData folders <temp> and <appdata>, other paths under the user's home <home>; the user name
becomes <user>; temporary world and arm-copy names (tl- or rp- plus 6 hex digits) become <world> and <arm-copy>; agent
and session ids become <id>. Ticket keys such as TL-44 stay as they are. Stops without writing if anything that looks
like machine data is left.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from config import EVALS_DIR, REPO_ROOT, add_common_options, resolve_workspace  # noqa: E402

FILES = ("benchmark.json", "benchmark.md", "analyst.json", "scores.md")
UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)


def path_pattern(path: Path) -> re.Pattern:
    drive, *rest = path.parts
    drive = drive.rstrip("\\/").rstrip(":")
    return re.compile(re.escape(drive) + r":[\\/]+" + r"[\\/]+".join(re.escape(p) for p in rest), re.I)


def rules() -> list[tuple[re.Pattern, str]]:
    user = Path.home().name
    return [
        (path_pattern(REPO_ROOT), "<repo>"),
        (path_pattern(Path.home() / "AppData" / "Local" / "Temp"), "<temp>"),
        (path_pattern(Path.home() / "AppData"), "<appdata>"),
        (path_pattern(Path.home()), "<home>"),
        (re.compile(rf"\b{re.escape(user)}\b", re.I), "<user>"),
        (re.compile(r"\btl-[0-9a-f]{6}(?:-r\d*)?\b"), "<world>"),
        (re.compile(r"\brp-[0-9a-f]{6}\b"), "<arm-copy>"),
        (UUID, "<id>"),
    ]


def leftovers(text: str) -> list[str]:
    checks = [re.compile(r"[A-Za-z]:[\\/]+Users[\\/]", re.I), re.compile(r"AppData[\\/]", re.I),
              re.compile(rf"\b{re.escape(Path.home().name)}\b", re.I), UUID]
    return sorted({m.group(0) for check in checks for m in check.finditer(text)})


def scrub_text(text: str, table: list[tuple[re.Pattern, str]]) -> str:
    for pattern, replacement in table:
        text = pattern.sub(replacement, text)
    return text


def scrub_json(value, table):
    if isinstance(value, str):
        return scrub_text(value, table)
    if isinstance(value, list):
        return [scrub_json(v, table) for v in value]
    if isinstance(value, dict):
        return {scrub_text(k, table): scrub_json(v, table) for k, v in value.items()}
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    add_common_options(parser)
    parser.add_argument("--iteration", type=int, required=True)
    parser.add_argument("--name", required=True, help="folder under evals/results, e.g. v2-vs-v3")
    args = parser.parse_args()
    source = resolve_workspace(args.workspace) / f"iteration-{args.iteration}"
    target = EVALS_DIR / "results" / args.name
    table = rules()
    out, problems = {}, []
    for name in FILES:
        path = source / name
        if not path.exists():
            continue
        raw = path.read_text(encoding="utf-8")
        if name.endswith(".json"):
            text = json.dumps(scrub_json(json.loads(raw), table), indent=2, ensure_ascii=False) + "\n"
        else:
            text = scrub_text(raw, table)
        left = leftovers(text)
        if left:
            problems.append(f"{name}: {', '.join(left[:5])}")
        out[name] = text
    if not out:
        raise SystemExit(f"nothing to publish in {source}")
    if problems:
        raise SystemExit("machine data left after scrubbing, nothing written:\n" + "\n".join(problems))
    target.mkdir(parents=True, exist_ok=True)
    for name, text in out.items():
        (target / name).write_text(text, encoding="utf-8", newline="\n")
        print(f"{target / name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
