#!/usr/bin/env bun

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";

function findPluginRoot(startDir: string): string | null {
  let dir = startDir;
  while (dir !== dirname(dir)) {
    if (existsSync(join(dir, "templates")) && existsSync(join(dir, "skills"))) return dir;
    dir = dirname(dir);
  }
  return null;
}

const pluginRoot =
  process.env.CLAUDE_PLUGIN_ROOT ||
  process.env.PLUGIN_ROOT ||
  findPluginRoot(import.meta.dirname);

if (!pluginRoot) {
  console.error("ritus: could not locate plugin root (no templates/ + skills/ directory found above " + import.meta.dirname + ")");
  process.exit(1);
}

const projectRoot =
  process.env.CLAUDE_PROJECT_DIR ||
  process.cwd();

const templateDir = join(pluginRoot, "templates");

type Strategy = "user-owned" | "append-only" | "scaffold" | "project-specific";

const STRATEGIES: Record<Strategy, string[]> = {
  "user-owned": [
    "docs/profiles/project.yml",
    "docs/profiles/team.yml",
    "docs/profiles/runtime.yml",
    "docs/CODE_CONVENTIONS.md",
    "docs/TEST_CONVENTIONS.md",
    "docs/ARCHITECTURE.md",
    "docs/DECISIONS.md",
    "docs/LESSONS.md",
    "docs/CUTOFF.md",
    "docs/STAKEHOLDERS.md",
    "docs/PROJECT_CONTEXT.md",
  ],
  "append-only": [
    "docs/CHANGELOG.md",
  ],
  scaffold: [
    "docs/tasks/README.md",
    "docs/memory/README.md",
  ],
  "project-specific": [
    ".ritus/.env.example",
  ],
};

const GITIGNORE_MARKER = "# --- ritus (managed) ---";
const GITIGNORE_ENTRIES = ["/.ritus/.env.local", "/.ritus/attachments/"];
const GITIGNORE_BLOCK = `${GITIGNORE_MARKER}\n${GITIGNORE_ENTRIES.join("\n")}\n`;

function missingGitignoreEntries(content: string): string[] {
  const lines = new Set(content.split(/\r?\n/).map((l) => l.trim()));
  return GITIGNORE_ENTRIES.filter((e) => !lines.has(e));
}

function ensureGitignore(root: string): "created" | "appended" | "updated" | "present" {
  const gitignorePath = join(root, ".gitignore");
  let content: string;
  try {
    content = readFileSync(gitignorePath, "utf-8");
  } catch (err) {
    if ((err as { code?: string }).code === "ENOENT") {
      writeFileSync(gitignorePath, GITIGNORE_BLOCK);
      return "created";
    }
    throw err;
  }
  const missing = missingGitignoreEntries(content);
  if (missing.length === 0) return "present";

  const markerPos = content.indexOf(GITIGNORE_MARKER);
  if (markerPos !== -1) {
    // Insert missing entries directly after the marker line so the managed block stays contiguous.
    const lineEnd = content.indexOf("\n", markerPos);
    const patched =
      lineEnd === -1
        ? `${content}\n${missing.join("\n")}\n`
        : content.slice(0, lineEnd + 1) + missing.join("\n") + "\n" + content.slice(lineEnd + 1);
    writeFileSync(gitignorePath, patched);
    return "updated";
  }

  const separator = content.length === 0 || content.endsWith("\n") ? "" : "\n";
  writeFileSync(gitignorePath, `${content}${separator}${GITIGNORE_MARKER}\n${missing.join("\n")}\n`);
  return "appended";
}

function getPluginVersion(): string {
  const manifestPath = join(pluginRoot!, ".claude-plugin", "plugin.json");
  if (existsSync(manifestPath)) {
    try {
      const manifest = JSON.parse(readFileSync(manifestPath, "utf-8"));
      return manifest.version || "1.0.0";
    } catch {
      return "1.0.0";
    }
  }
  return "1.0.0";
}

function getStrategy(filePath: string): Strategy {
  for (const [strategy, files] of Object.entries(STRATEGIES)) {
    if (files.includes(filePath)) return strategy as Strategy;
  }
  return "user-owned";
}

function getAllTemplateFiles(): string[] {
  const files: string[] = [];
  for (const fileList of Object.values(STRATEGIES)) {
    files.push(...fileList);
  }
  return files;
}

function check(): void {
  if (!existsSync(templateDir)) {
    console.log("ritus: templates directory not found at " + templateDir);
    process.exit(1);
  }

  const pluginVersion = getPluginVersion();
  const files = getAllTemplateFiles();
  const missing: string[] = [];

  for (const file of files) {
    const projectPath = join(projectRoot, file);
    const templatePath = join(templateDir, file);

    if (!existsSync(templatePath)) continue;

    if (!existsSync(projectPath)) {
      missing.push(file);
    }
  }

  const gitignorePath = join(projectRoot, ".gitignore");
  let gitignoreNeedsBlock: boolean;
  try {
    gitignoreNeedsBlock = missingGitignoreEntries(readFileSync(gitignorePath, "utf-8")).length > 0;
  } catch (err) {
    if ((err as { code?: string }).code === "ENOENT") gitignoreNeedsBlock = true;
    else throw err;
  }

  const staleScriptsDir = join(projectRoot, ".ritus", "scripts");
  if (existsSync(staleScriptsDir)) {
    console.log("ritus: WARNING - .ritus/scripts/ is stale and can be safely deleted. Scripts now live in the plugin directory.");
  }

  if (missing.length === 0 && !gitignoreNeedsBlock) {
    console.log("ritus: project files up to date (v" + pluginVersion + ")");
    return;
  }

  const wouldAdd = missing.length + (gitignoreNeedsBlock ? 1 : 0);
  console.log("ritus: " + wouldAdd + " file(s) missing. Re-run this script with --apply to create them.");
  for (const f of missing) console.log("  + " + f);
  if (gitignoreNeedsBlock) console.log("  + .gitignore (ritus managed block)");
}

function apply(): void {
  if (!existsSync(templateDir)) {
    console.log("ritus: templates directory not found at " + templateDir);
    process.exit(1);
  }

  const pluginVersion = getPluginVersion();
  const files = getAllTemplateFiles();
  const created: string[] = [];
  const skipped: { file: string; reason: string }[] = [];

  for (const file of files) {
    const projectPath = join(projectRoot, file);
    const templatePath = join(templateDir, file);

    if (!existsSync(templatePath)) continue;

    if (!existsSync(projectPath)) {
      mkdirSync(dirname(projectPath), { recursive: true });
      writeFileSync(projectPath, readFileSync(templatePath, "utf-8"));
      created.push(file);
      continue;
    }

    skipped.push({ file, reason: getStrategy(file) + " - already exists" });
  }

  if (created.length > 0) {
    console.log("Created " + created.length + " file(s):");
    for (const f of created) console.log("  + " + f);
  }

  if (skipped.length > 0) {
    console.log("Skipped " + skipped.length + " file(s):");
    for (const entry of skipped) console.log("  - " + entry.file + " (" + entry.reason + ")");
  }

  const gitignoreAction = ensureGitignore(projectRoot);
  if (gitignoreAction === "created") {
    console.log("Created .gitignore with ritus managed block");
  } else if (gitignoreAction === "appended") {
    console.log("Appended ritus managed block to .gitignore");
  } else if (gitignoreAction === "updated") {
    console.log("Updated ritus managed block in .gitignore");
  }

  if (created.length === 0 && gitignoreAction === "present") {
    console.log("ritus: project files up to date (v" + pluginVersion + ")");
  }
}

const args = process.argv.slice(2);
const command = args[0] || "--check";

switch (command) {
  case "--check":
    check();
    break;
  case "--apply":
    apply();
    break;
  default:
    console.log("Usage: sync.ts [--check | --apply]");
    console.log("");
    console.log("  --check   Report missing files (safe, no writes)");
    console.log("  --apply   Create missing files, never overwrite existing");
    process.exit(1);
}
