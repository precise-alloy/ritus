"""Show the latest reply file (turn-N.md) of one or more runs, to classify the turn.

  python peek.py tl-xxxxxx [tl-yyyyyy ...] [--lines 60]
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import build  # noqa: E402
from config import add_common_options, resolve_workspace  # noqa: E402

parser = argparse.ArgumentParser()
add_common_options(parser)
parser.add_argument("names", nargs="+")
parser.add_argument("--lines", type=int, default=60)
args = parser.parse_args()
build.configure_paths(resolve_workspace(args.workspace))

for name in args.names:
    out = build.AGENT_TMP / name / "out"
    files = sorted(out.glob("turn-*.md"), key=lambda p: int(re.search(r"(\d+)", p.stem).group(1)))
    if not files:
        print(f"== {name}: NO TURN FILES ({sorted(p.name for p in out.iterdir()) if out.is_dir() else 'no out dir'})")
        continue
    latest = files[-1]
    lines = latest.read_text(encoding="utf-8", errors="replace").splitlines()
    print(f"== {name} {latest.name} ({len(lines)} lines; files: {[p.name for p in files]})")
    keep = args.lines
    body = lines if len(lines) <= keep else lines[:12] + [f"... ({len(lines) - keep} lines skipped) ..."] + lines[-(keep - 12):]
    print("\n".join(body))
    print()
