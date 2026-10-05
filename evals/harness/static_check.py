"""Static checks for the Ritus Phase 1-4 rewrite. Run from the repo root."""
import argparse
import json
import pathlib
import re
import sys

import yaml

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from config import REPO_ROOT as DEFAULT_REPO_ROOT  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("legacy_plugin_root", nargs="?", help="Plugin root (legacy positional form)")
parser.add_argument("--plugin-root", default=None, help="Plugin root; default <repo>\\plugins\\ritus")
parser.add_argument("--repo-root", default=None, help="Repository root; default harness repository")
args = parser.parse_args()
REPO_ROOT = pathlib.Path(args.repo_root).resolve() if args.repo_root else DEFAULT_REPO_ROOT
ROOT = pathlib.Path(args.plugin_root or args.legacy_plugin_root or (REPO_ROOT / "plugins" / "ritus")).resolve()
SKILLS = ROOT / "skills"
problems: list[str] = []
notes: list[str] = []

# 1. Frontmatter: name matches folder, description present and within limits.
for skill_md in sorted(SKILLS.glob("*/SKILL.md")):
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not m:
        problems.append(f"{skill_md}: no frontmatter")
        continue
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    folder = skill_md.parent.name
    if fm.get("name") != folder:
        problems.append(f"{skill_md}: name {fm.get('name')!r} != folder {folder!r}")
    desc = fm.get("description", "")
    if not desc:
        problems.append(f"{skill_md}: missing description")
    elif len(desc) > 1024:
        problems.append(f"{skill_md}: description {len(desc)} chars > 1024")
    if not re.fullmatch(r"[a-z0-9-]{1,64}", fm.get("name", "")):
        problems.append(f"{skill_md}: invalid name {fm.get('name')!r}")
    try:
        parsed = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        problems.append(f"{skill_md}: frontmatter is not valid YAML: {str(e).splitlines()[0]}")
        parsed = None
    if isinstance(parsed, dict):
        for key in ("name", "description", "argument-hint"):
            if key in parsed and not isinstance(parsed[key], str):
                problems.append(f"{skill_md}: {key} parses as {type(parsed[key]).__name__}, not a string")
        if isinstance(parsed.get("description"), str) and parsed["description"].strip() != desc.strip().strip('"').strip("'"):
            problems.append(f"{skill_md}: description parses differently than written (quoting or ': ' issue)")

skill_names = sorted(p.parent.name for p in SKILLS.glob("*/SKILL.md"))
notes.append(f"{len(skill_names)} skills: {', '.join(skill_names)}")

# 2. Every `skills/...` path referenced in repo markdown exists.
md_files = [p for p in ROOT.rglob("*.md") if ".git" not in p.parts]
readme = REPO_ROOT / "README.md"
if readme.is_file():
    md_files.append(readme)

def rel_to_base(path: pathlib.Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.relative_to(REPO_ROOT).as_posix()

# The README's 2.x -> 3.0.0 migration section names the removed skills on purpose.
def migration_lines() -> set[int]:
    readme = REPO_ROOT / "README.md"
    if not readme.is_file():
        return set()
    lines = readme.read_text(encoding="utf-8").splitlines()
    inside, out = False, set()
    for n, line in enumerate(lines, 1):
        if line.startswith("### Upgrading from 2.x"):
            inside = True
        elif inside and (line.startswith("## ") or (line.startswith("### ") and not line.startswith("### Upgrading from"))):
            inside = False
        if inside:
            out.add(n)
    return out

MIGRATION = migration_lines()

def exempt(rel: str, n: int) -> bool:
    return rel == "README.md" and n in MIGRATION
ref_re = re.compile(r"`(skills/[^`\s]+)`")
for md in md_files:
    for n, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
        for ref in ref_re.findall(line):
            if any(c in ref for c in "<{*"):
                continue
            target = ROOT / ref.rstrip("/.,;:)")
            if not target.exists():
                problems.append(f"{rel_to_base(md)}:{n}: missing path {ref}")

# 3. Relative template references inside a skill resolve against the skill dir.
rel_re = re.compile(r"`((?:templates|references)/[^`\s]+\.md)`")
for skill_md in SKILLS.glob("*/SKILL.md"):
    for n, line in enumerate(skill_md.read_text(encoding="utf-8").splitlines(), 1):
        for ref in rel_re.findall(line):
            if any(c in ref for c in "<{*"):
                continue
            if not (skill_md.parent / ref).exists() and not (ROOT / ref).exists():
                problems.append(f"{skill_md.relative_to(ROOT)}:{n}: missing relative {ref}")

# 4. No references to the removed standards skills.
removed = ["code-conventions", "definition-of-done", "testing-policy"]
removed_re = re.compile(r"\b(" + "|".join(map(re.escape, removed)) + r")\b|`tdd`|\btdd\b|`security` skill|security skill|skills/security\b")
for p in ROOT.rglob("*"):
    if ".git" in p.parts or not p.is_file() or p.suffix not in {".md", ".ts", ".json", ".yml", ".yaml"}:
        continue
    for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if removed_re.search(line) and not exempt(rel_to_base(p), n):
            problems.append(f"{rel_to_base(p)}:{n}: removed-skill reference: {line.strip()[:120]}")

# 5. Style checks on the files this phase rewrote.
rewritten = [
    "skills/execute-task/SKILL.md",
    "skills/verify-task/SKILL.md",
    "skills/shared/dispatch.md",
    "skills/shared/standards/engineering.md",
    "skills/shared/standards/testing.md",
    "skills/shared/standards/security.md",
    "skills/ticket-review/templates/task.md",
    # Phase 2
    "skills/shared/levels.md",
    "skills/ticket-review/SKILL.md",
    "skills/ticket-review/references/analysis-brief.md",
    "skills/ticket-review/references/task-generation.md",
    "skills/ticket-review/templates/plan.md",
    "skills/ticket-review/templates/exploration.md",
    "skills/start-ritus/SKILL.md",
    # Phase 3
    "skills/pr-review/SKILL.md",
    "skills/pr-review/references/rubric.md",
    "skills/pr-review/references/findings.md",
    "skills/address-feedback/SKILL.md",
    "skills/debug/SKILL.md",
    "skills/debug/templates/case-file.md",
    "skills/shared/remote-api-access.md",
    "skills/shared/standards/writing.md",
    "skills/setup/templates/agent-routing.md",
    # Phase 4
    "skills/wrap-up/SKILL.md",
    "skills/comprehension/SKILL.md",
    "skills/brainstorm/SKILL.md",
    "skills/migrate-docs/SKILL.md",
    "skills/repo-scan/SKILL.md",
    "skills/setup/SKILL.md",
    "skills/setup/references/settings.md",
    "skills/setup/references/derived-values.md",
    "skills/setup/references/project-context.md",
]
for rel in rewritten:
    p = ROOT / rel
    text = p.read_text(encoding="utf-8")
    for n, line in enumerate(text.splitlines(), 1):
        if "\u2014" in line:
            problems.append(f"{rel}:{n}: em dash")
        if "<branch>" in line or "<branch-slug>" in line:
            problems.append(f"{rel}:{n}: <branch>/<branch-slug> placeholder (use {{branch-slug}})")
        if re.search(r"SendMessage|write_agent|send_session_message", line):
            problems.append(f"{rel}:{n}: harness-specific tool name")
    words = len(re.findall(r"\S+", text))
    if rel.endswith("SKILL.md") and (len(text.splitlines()) > 150 or len(text) / 4 > 2200):
        problems.append(f"{rel}: over the core-skill budget (150 lines / ~2k tokens)")
    notes.append(f"{rel}: {len(text.splitlines())} lines, {len(text)} chars, ~{round(len(text) / 4)} tokens, {words} words")

# 6. No stale references to the skills Phase 2 merged into ticket-review.
json_meta = {"package.json", "marketplace.json", ".claude-plugin/plugin.json", ".claude-plugin/marketplace.json"}
stale_rules = [
    (re.compile(r"skills/(triage|requirement-analysis|task-generation)/|review-document|review doc(ument)?\b", re.I), set(), []),
    (re.compile(r"\btriage\b", re.I), json_meta, [r"older files call it \*per triage\*"]),
    (re.compile(r"requirement-analysis"), {"skills/shared/dispatch.md"}, []),
    (re.compile(r"task-generation"), set(), [r"references/task-generation\.md", r"after task-generation", r"→ task-generation \(task files written\)", r"task-generation rules"]),
]
for p in ROOT.rglob("*"):
    if ".git" in p.parts or not p.is_file() or p.suffix not in {".md", ".ts", ".json", ".yml", ".yaml"}:
        continue
    rel = rel_to_base(p)
    for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if exempt(rel, n):
            continue
        for rx, ok_files, ok_contexts in stale_rules:
            if not rx.search(line) or rel in ok_files:
                continue
            residue = line
            for ctx in ok_contexts:
                residue = re.sub(ctx, "", residue)
            if rx.search(residue):
                problems.append(f"{rel}:{n}: stale Phase 2 reference: {line.strip()[:120]}")

# 6b. No references to what Phase 3 removed or renamed.
phase3_stale = re.compile(r"finding-types|Iron law|4-phase investigation|Phases? 1-5|DECISION-NNN entry to|every item below, verbatim|create this TODO")
for p in ROOT.rglob("*"):
    if ".git" in p.parts or not p.is_file() or p.suffix not in {".md", ".ts", ".json", ".yml", ".yaml"}:
        continue
    for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if phase3_stale.search(line) and not exempt(rel_to_base(p), n):
            problems.append(f"{rel_to_base(p)}:{n}: stale Phase 3 reference: {line.strip()[:120]}")

# 6c. No references to what Phase 4 removed or renamed.
phase4_stale = re.compile(r"11-question|user-invocable|\{\{MODEL_BUDGET\}\}|design note|brainstorm note|\bQ(1[01]|[1-9])\b|sync hook|verify docs\)|tasks/\{author\}|One task, main thread|setup wizard|Derived by CLI")
for p in ROOT.rglob("*"):
    if ".git" in p.parts or not p.is_file() or p.suffix not in {".md", ".ts", ".json", ".yml", ".yaml"}:
        continue
    rel = rel_to_base(p)
    for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if phase4_stale.search(line) and not (rel == "skills/migrate-docs/SKILL.md" and "design notes" in line):
            problems.append(f"{rel}:{n}: stale Phase 4 reference: {line.strip()[:120]}")

# 7. Every `invoke X` / `dispatch X subagent` names a skill that exists.
skill_set = set(skill_names)
call_re = re.compile(r"\binvoke `?([a-z][a-z-]+)`?|\bdispatch `?([a-z][a-z-]+)`? subagent")
for md in md_files:
    rel = rel_to_base(md)
    for n, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
        for a, b in call_re.findall(line):
            name = a or b
            if "-" in name and name not in skill_set:
                problems.append(f"{rel}:{n}: invokes unknown skill {name!r}")
            elif name in {"triage", "setup", "sync", "debug", "brainstorm"} and name not in skill_set:
                problems.append(f"{rel}:{n}: invokes unknown skill {name!r}")

# 8. Every skill template and reference is pointed to from somewhere else.
corpus = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in md_files)
for f in sorted(SKILLS.glob("*/templates/*.md")) + sorted(SKILLS.glob("*/references/*.md")) + sorted((SKILLS / "shared").rglob("*.md")):
    if f.name not in corpus.replace(f.read_text(encoding="utf-8"), ""):
        problems.append(f"{f.relative_to(ROOT).as_posix()}: nothing points to it")

# 9. Marketplace and package manifests stay aligned with the plugin metadata.
def read_json(path: pathlib.Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        problems.append(f"{path}: missing")
    except json.JSONDecodeError as e:
        problems.append(f"{path}: invalid JSON: {e}")
    return None


def stable(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


copilot_marketplace = REPO_ROOT / "marketplace.json"
claude_marketplace = REPO_ROOT / ".claude-plugin" / "marketplace.json"
package_json = REPO_ROOT / "package.json"
copilot_data = read_json(copilot_marketplace)
claude_data = read_json(claude_marketplace)
package_data = read_json(package_json)

copilot_plugins = copilot_data.get("plugins") if isinstance(copilot_data, dict) else None
claude_plugins = claude_data.get("plugins") if isinstance(claude_data, dict) else None
if not isinstance(copilot_plugins, list):
    problems.append(f"{copilot_marketplace}: plugins is not a list")
if not isinstance(claude_plugins, list):
    problems.append(f"{claude_marketplace}: plugins is not a list")

ritus_plugin_meta = None
if isinstance(copilot_plugins, list) and isinstance(claude_plugins, list):
    if len(copilot_plugins) != len(claude_plugins):
        problems.append(f"{copilot_marketplace}: {len(copilot_plugins)} plugins != {claude_marketplace}: {len(claude_plugins)} plugins")
    for i, (copilot_entry, claude_entry) in enumerate(zip(copilot_plugins, claude_plugins)):
        if not isinstance(copilot_entry, dict) or not isinstance(claude_entry, dict):
            problems.append(f"plugins[{i}]: entry is not an object in both marketplaces")
            continue
        for key in ("name", "version", "description", "source"):
            if stable(copilot_entry.get(key)) != stable(claude_entry.get(key)):
                problems.append(
                    f"plugins[{i}].{key}: {copilot_marketplace} has {copilot_entry.get(key)!r}; "
                    f"{claude_marketplace} has {claude_entry.get(key)!r}"
                )
        for manifest, entry in ((copilot_marketplace, copilot_entry), (claude_marketplace, claude_entry)):
            source = entry.get("source")
            if isinstance(source, str) and source.startswith("."):
                plugin_json = (REPO_ROOT / source).resolve() / ".claude-plugin" / "plugin.json"
                meta = read_json(plugin_json)
                if isinstance(meta, dict):
                    if meta.get("name") != entry.get("name"):
                        problems.append(f"{manifest} source {source}: {plugin_json} name {meta.get('name')!r} != entry {entry.get('name')!r}")
                    if meta.get("version") != entry.get("version"):
                        problems.append(f"{manifest} source {source}: {plugin_json} version {meta.get('version')!r} != entry {entry.get('version')!r}")
                    if entry.get("name") == "ritus":
                        ritus_plugin_meta = meta

if isinstance(package_data, dict) and isinstance(ritus_plugin_meta, dict):
    if package_data.get("version") != ritus_plugin_meta.get("version"):
        problems.append(
            f"{package_json} version {package_data.get('version')!r} != "
            f"{ROOT / '.claude-plugin' / 'plugin.json'} version {ritus_plugin_meta.get('version')!r}"
        )

print("NOTES")
for n in notes:
    print("  " + n)
print(f"PROBLEMS ({len(problems)})")
for p in problems:
    print("  " + p)
sys.exit(1 if problems else 0)
