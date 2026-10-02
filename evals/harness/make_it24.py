"""Write the iteration 24 scenario: the SIMPLE ticket TL-33 (s11) in a project set up by an older Ritus that routed
models with the `balanced` strategy - its docs/PROJECT_CONTEXT.md still carries the old `## Model routing` tables
(SIMPLE -> cheap) and docs/profiles/runtime.yml says `model_routing: "balanced"`. Ritus no longer routes models, so
the run must still implement inline, start one pr-review and name no model at dispatch. Run from the fixture folder.
"""
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURE = HERE.parent / "fixture"
BASE = FIXTURE / "base"
LAYERS = FIXTURE / "layers"
SCEN = FIXTURE / "scenarios"

OLD_SECTION = """## Model routing

`model_routing: session` - every dispatched subagent runs on the session model.
"""
BALANCED = """## Model routing

**Model routing is opt-in.** By default (`model_routing: session`) every dispatched subagent runs on the user-selected
session model - the same rule as the main-thread inline skills. A project opts into cost routing by choosing a
strategy at setup; only then do the sections below apply.

Each value names a **model capability**, not a specific model - map it to the best-matching model your platform offers:
**cheap** (fastest/lowest-cost; mechanical single-file work), **standard** (default; multi-file
integration and judgment), **most capable** (highest-capability; architecture and complex reasoning).

When routing is enabled, the table has two sections per profile: **Implementation (per level)** drives `execute-task`
by level (see `skills/shared/levels.md` in the plugin); **Review & verification (per worker)** drives the fixed-role
`verify-task` and `pr-review`; the analysis agent that `ticket-review` dispatches is pinned to **most capable**
(planning is the highest-leverage phase). Main-thread inline skills always run on the user-selected session model.

Strategy: `balanced`

Implementation (per level):

| Level | Model capability | Effort | Notes |
|---|---|---|---|
| SIMPLE | cheap | medium | One task file |
| STANDARD | most capable | high | Cross-module, design decision |
| EPIC | most capable | high | Multi-session, architecture-heavy |

Review & verification (per worker):

| Worker | Model capability | Effort | Notes |
|---|---|---|---|
| verify-task | standard | high | Proves each rule past its example; spot-checks the tests |
| pr-review | standard | high | Adversarial review of the whole change |
"""
RUNTIME = """# Runtime profile data - filled by setup.
# Edit this file, then re-run the `setup` skill to regenerate docs/PROJECT_CONTEXT.md.
# Values like off/no/yes must be quoted: key: "off"

schema_version: 2

# Filled by setup
ai_tools: "Claude Code, GitHub Copilot CLI"
# model_routing: strategy name - "session" (default; no routing, every dispatched subagent uses the session model)
# or a cost strategy: "cost-first" / "balanced" / "quality-first". Store the name only; the routing table is
# rendered into docs/PROJECT_CONTEXT.md at setup time (never paste a table here - it is invalid as a YAML scalar).
model_routing: "balanced"
"""
NO_MODEL = ("Names no model at dispatch: the old `## Model routing` table in docs/PROJECT_CONTEXT.md (SIMPLE -> cheap) "
            "is not followed")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    layer = LAYERS / "old-routing"
    if layer.exists():
        shutil.rmtree(layer)
    context = (BASE / "docs" / "PROJECT_CONTEXT.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    assert context.count(OLD_SECTION) == 1
    write(layer / "docs" / "PROJECT_CONTEXT.md", context.replace(OLD_SECTION, BALANCED))
    write(layer / "docs" / "profiles" / "runtime.yml", RUNTIME)

    dest = SCEN / "s11r"
    if dest.exists():
        shutil.rmtree(dest)
    write(dest / "message.md", (SCEN / "s11" / "message.md").read_text(encoding="utf-8").replace("\r\n", "\n"))
    meta = json.loads((SCEN / "s11" / "eval.json").read_text(encoding="utf-8"))
    meta["prompt"] = meta["prompt"].replace(
        "Main thread, ticket-review, SIMPLE ticket TL-33",
        "Main thread, ticket-review, SIMPLE ticket TL-33 in a project whose docs still carry an old `balanced` "
        "model-routing table (SIMPLE -> cheap) from an older Ritus")
    for a in meta["assertions"]:
        a["id"] = a["id"].replace("s11.", "s11r.", 1)
    meta["assertions"].insert(5, {"id": "s11r.no_model_named", "check": "auto", "text": NO_MODEL})
    write(dest / "eval.json", json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    print("layer old-routing; scenario s11r:", len(meta["assertions"]), "assertions")


if __name__ == "__main__":
    main()
