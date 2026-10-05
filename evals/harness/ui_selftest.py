from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import build

VERDICTS = [
    "routes_ok",
    "no_overflow",
    "axe_clean",
    "console_clean",
    "card_geometry",
    "card_colors",
    "card_type",
    "card_total",
    "card_full_width",
    "card_reuses_component",
    "tokens_only",
    "empty_state",
    "transfer_layout",
]

TREES = [
    ("base", []),
    ("card-good", ["card-good"]),
    ("card-gap", ["card-good", "card-gap"]),
    ("card-hex-console", ["card-good", "card-hex-console"]),
    ("transfer-good", ["transfer-good"]),
    ("transfer-overflow", ["transfer-good", "transfer-overflow"]),
    ("transfer-nolabel", ["transfer-good", "transfer-nolabel"]),
    ("txn-good", ["txn-good"]),
    ("txn-noempty", ["txn-good", "txn-noempty"]),
    ("st-card-wrapper-alias", ["card-good", "selftest:st-card-wrapper-alias"]),
    ("st-card-narrow-mobile", ["card-good", "selftest:st-card-narrow-mobile"]),
    ("st-card-decoy", ["card-good", "selftest:st-card-decoy"]),
    ("st-card-mimic", ["card-good", "selftest:st-card-mimic"]),
    ("st-card-strong-value", ["card-good", "selftest:st-card-strong-value"]),
    ("st-card-export-comment", ["card-good", "selftest:st-card-export-comment"]),
    ("st-broken-module", ["selftest:st-broken-module"]),
    ("st-transfer-grid", ["transfer-good", "selftest:st-transfer-grid"]),
    ("st-transfer-overlap", ["transfer-good", "selftest:st-transfer-overlap"]),
    ("st-txn-hidden-table", ["txn-good", "selftest:st-txn-hidden-table"]),
    ("st-txn-visible-table", ["txn-good", "selftest:st-txn-visible-table"]),
]

ALL = {name for name, _ in TREES}
CARD_TREES = {"card-good", "card-gap", "card-hex-console", "st-card-wrapper-alias", "st-card-narrow-mobile", "st-card-decoy", "st-card-mimic", "st-card-strong-value", "st-card-export-comment"}
EXPECTED = {
    "routes_ok": ALL - {"st-broken-module"},
    "no_overflow": ALL - {"transfer-overflow"},
    "axe_clean": ALL - {"transfer-nolabel"},
    "console_clean": ALL - {"card-hex-console", "st-broken-module"},
    "card_geometry": {"card-good", "card-hex-console", "st-card-wrapper-alias", "st-card-narrow-mobile", "st-card-decoy", "st-card-mimic", "st-card-strong-value", "st-card-export-comment"},
    "card_colors": CARD_TREES,
    "card_type": CARD_TREES,
    "card_total": CARD_TREES,
    "card_full_width": CARD_TREES - {"st-card-narrow-mobile"},
    "card_reuses_component": {"card-good", "card-gap", "card-hex-console", "st-card-wrapper-alias", "st-card-narrow-mobile", "st-card-strong-value", "st-card-export-comment"},
    "tokens_only": ALL - {"card-hex-console"},
    "empty_state": {"txn-good", "st-txn-hidden-table"},
    "transfer_layout": {"transfer-good", "transfer-overflow", "transfer-nolabel", "st-transfer-grid"},
}


def apply_tree(dest: Path, layers: list[str]) -> None:
    shutil.copytree(build.WEB_BASE, dest, ignore=shutil.ignore_patterns(*build.SKIP_SNAPSHOT))
    for layer in layers:
        if layer.startswith("selftest:"):
            source = build.WEB_SELFTEST / layer.split(":", 1)[1]
        else:
            source = build.WEB_LAYERS / layer
        build.copy_tree_lf(source, dest)


def render_design(args) -> int:
    build.configure_paths(args.workspace, None, None, args.web_modules)
    web_modules = build.web_modules_dir()
    out_dir = build.FIXTURE_DIR / "web" / "design"
    out_dir.mkdir(parents=True, exist_ok=True)
    with build.tempdir("tl-design-render-") as tmp:
        tmp_root = Path(tmp)
        tree = tmp_root / "card-good"
        apply_tree(tree, ["card-good"])
        port = build.free_ui_port()
        log_path = tmp_root / "ui-server.log"
        log_file = log_path.open("w", encoding="utf-8", errors="replace")
        proc = subprocess.Popen(
            ["node", "scripts/serve.mjs", "--port", str(port)],
            cwd=tree,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        try:
            if not build.wait_http_ok(f"http://localhost:{port}/accounts", 20):
                log_file.flush()
                print(log_path.read_text(encoding="utf-8", errors="replace")[-1500:], file=sys.stderr)
                return 1
            script = tmp_root / "render-design.mjs"
            script.write_text(
                """
import { createRequire } from 'node:module';
import { join } from 'node:path';
const modules = process.env.UI_MODULES;
if (!modules) throw new Error('UI_MODULES is required');
const require = createRequire(join(modules, 'package.json'));
const { chromium } = require('playwright');
const [cardPath, pagePath, baseUrl] = process.argv.slice(2);
const browser = await chromium.launch({ headless: true });
try {
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  await page.goto(new URL('/accounts', baseUrl).toString(), { waitUntil: 'networkidle' });
  await page.screenshot({ path: pagePath });
  await page.locator('.summary-card').first().screenshot({ path: cardPath });
  await context.close();
} finally {
  await browser.close();
}
""".strip() + "\n",
                encoding="utf-8",
                newline="\n",
            )
            modules = web_modules / "node_modules" if (web_modules / "node_modules").is_dir() else web_modules
            env = dict(os.environ, UI_MODULES=str(modules))
            proc_render = build.run(
                ["node", str(script), str(out_dir / "12-34.png"), str(out_dir / "12-30.png"), f"http://localhost:{port}"],
                cwd=tree,
                env=env,
                check=False,
                timeout=90,
            )
            if proc_render.returncode != 0:
                print((proc_render.stdout + proc_render.stderr)[-1500:], file=sys.stderr)
                return proc_render.returncode or 1
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=10)
            try:
                log_file.close()
            except OSError:
                pass
    print(f"rendered {out_dir / '12-34.png'}")
    print(f"rendered {out_dir / '12-30.png'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace")
    parser.add_argument("--web-modules")
    parser.add_argument("--render-design", action="store_true")
    args = parser.parse_args()
    if args.render_design:
        return render_design(args)
    build.configure_paths(args.workspace, None, None, args.web_modules)
    web_modules = build.web_modules_dir()
    started = time.time()
    mismatches = []
    results = {verdict: {} for verdict in VERDICTS}
    evidence = {verdict: {} for verdict in VERDICTS}
    with build.tempdir("tl-ui-selftest-") as tmp:
        tmp_root = Path(tmp)
        base_tree = tmp_root / "base-files"
        apply_tree(base_tree, [])
        setup_files = build.tree_text(base_tree)
        for name, layer_names in TREES:
            tree = tmp_root / name
            apply_tree(tree, layer_names)
            measurements = build.ui_eval(tree, web_modules, VERDICTS)
            if "error" in measurements:
                for verdict in VERDICTS:
                    results[verdict][name] = False
                    evidence[verdict][name] = measurements.get("output") or measurements["error"]
            else:
                verdicts = build.ui_verdicts(measurements, setup_files, build.tree_text(tree))
                for verdict in VERDICTS:
                    passed, why = verdicts[verdict]
                    results[verdict][name] = passed
                    evidence[verdict][name] = why
    header = ["Verdict", *[name for name, _ in TREES]]
    print(" | ".join(header))
    print(" | ".join(["---", *["---" for _ in TREES]]))
    for verdict in VERDICTS:
        row = [verdict]
        for name, _layers in TREES:
            cell = "PASS" if results[verdict][name] else "FAIL"
            row.append(cell)
            expected = name in EXPECTED[verdict]
            if results[verdict][name] != expected:
                mismatches.append((verdict, name, "PASS" if expected else "FAIL", cell, evidence[verdict][name]))
        print(" | ".join(row))
    elapsed = time.time() - started
    print(f"runtime: {elapsed:.1f}s")
    if mismatches:
        print("mismatches:")
        for verdict, name, expected, observed, why in mismatches:
            print(f"- {verdict}/{name}: expected {expected}, observed {observed}: {why}")
        return 1
    print("matrix matches expected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
