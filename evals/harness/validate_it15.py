"""Validate the iteration 15 worlds: green build/test/lint, the planted bugs, and the diff size against main."""
import difflib
import subprocess
import sys
from pathlib import Path

import build

T = [f"l-t{i}" for i in range(1, 9)]
WORLDS = {
    **{f"stage-{i}": T[:i] for i in range(1, 9)},
    "lv1 (B1 after 001)": ["l-b1-t1"],
    "lv2 (B2 after 006)": T[:6] + ["l-b2-t6"],
    "lv3 (clean after 007)": T[:7],
    "full clean": T,
    "full B1": T + ["l-b1-full"],
    "full B2": T + ["l-b2-t6"],
}
PROBE_FEE = """
import { mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { Ledger } from './src/ledger.js';
import { refund } from './src/refund.js';
const ledger = await Ledger.create(join(await mkdtemp(join(tmpdir(), 'probe-')), 'l.json'), { alice: 10000, bob: 5000 });
console.log('fee(1050) =', (await refund(ledger, 'alice', 'bob', 1050, { refundFee: true })).feeCents);
"""
PROBE_LIST = """
import { mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { Ledger } from './src/ledger.js';
import { refund } from './src/refund.js';
import { listRefunds } from './src/refunds.js';
const ledger = await Ledger.create(join(await mkdtemp(join(tmpdir(), 'probe-')), 'l.json'),
  { alice: 10000, bob: 5000, carol: 5000 });
await refund(ledger, 'alice', 'bob', 1050, { refundFee: true });
await refund(ledger, 'carol', 'alice', 500);
for (const accountId of ['alice', 'bob', 'carol']) {
  console.log(accountId, JSON.stringify((await listRefunds(ledger, { accountId })).map((r) => r.id)));
}
"""


def tree(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8") for p in root.rglob("*")
            if p.is_file() and ".git" not in p.parts}


def diff_size(before: dict, after: dict) -> tuple[int, int, list]:
    added = removed = 0
    files = []
    for rel in sorted(set(before) | set(after)):
        if before.get(rel) == after.get(rel):
            continue
        files.append(rel)
        for line in difflib.unified_diff((before.get(rel) or "").splitlines(), (after.get(rel) or "").splitlines(),
                                         lineterm="", n=0):
            if line.startswith("+") and not line.startswith("+++"):
                added += 1
            elif line.startswith("-") and not line.startswith("---"):
                removed += 1
    return added, removed, files


def main() -> int:
    ok = True
    with build.tempdir("it15-main-") as tmp:
        main_repo = Path(tmp)
        build.materialize(main_repo, build.TL27_LAYERS)
        main_tree = tree(main_repo)
    for name, layers in WORLDS.items():
        with build.tempdir("it15-") as tmp:
            repo = Path(tmp)
            build.materialize(repo, build.TL27_LAYERS + layers)
            checks = build.run_checks(repo)
            codes = {k: v["code"] for k, v in checks.items()}
            green = all(c == 0 for c in codes.values())
            ok &= green
            line = f"{name:24s} build={codes['build']} test={codes['test']} ({checks['test'].get('pass')} pass, " \
                   f"{checks['test'].get('fail')} fail) lint={codes['lint']}"
            if not green:
                line += "\n" + "\n".join(v["tail"][-600:] for v in checks.values() if v["code"] != 0)
            for probe, needs in ((PROBE_FEE, "src/refund.js"), (PROBE_LIST, "src/refunds.js")):
                if (repo / needs).exists():
                    (repo / "probe.mjs").write_text(probe, encoding="utf-8")
                    proc = subprocess.run(["node", "probe.mjs"], cwd=repo, capture_output=True, text=True)
                    line += "\n    " + (proc.stdout.strip() or proc.stderr.strip()[-300:]).replace("\n", "\n    ")
                    (repo / "probe.mjs").unlink()
            if name.startswith("full") or name.startswith("lv"):
                added, removed, files = diff_size(main_tree, tree(repo))
                code = [f for f in files if f.startswith(("src/", "test/"))]
                line += f"\n    diff vs main: {len(files)} files ({len(code)} src/test), +{added} -{removed}"
            print(line)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
