#!/usr/bin/env bun

import { appendFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";

// Patterns that cause git to ignore `.env.local`.
const ENV_LOCAL_IGNORE_PATTERNS = new Set([
  ".env.local",
  ".env.local/",
  ".env.*.local",
  ".env*",
  ".env.*",
  "*.local",
]);

function gitignoreCoversEnvLocal(content: string): boolean {
  for (const rawLine of content.split(/\r?\n/)) {
    let line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    if (line.startsWith("/")) line = line.slice(1);
    if (ENV_LOCAL_IGNORE_PATTERNS.has(line)) return true;
  }
  return false;
}

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
    ".ritus/scripts/remote-api.ts",
    ".ritus/scripts/providers/types.ts",
    ".ritus/scripts/providers/http.ts",
    ".ritus/scripts/providers/provider-jira.ts",
    ".ritus/scripts/providers/sanitize.ts",
    ".ritus/scripts/providers/provider-ado.ts",
    ".ritus/scripts/providers/provider-github.ts",
    ".ritus/scripts/tsconfig.json",
    ".env.example",
  ],
};

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

const GITIGNORE_ENV_LOCAL_BLOCK =
  "\n# Local secrets — never commit (Jira PAT, GitHub token, etc.)\n.env.local\n.env.*.local\n";

function checkGitignore(): "missing" | "needs-update" | null {
  const projectPath = join(projectRoot, ".gitignore");
  const templatePath = join(templateDir, ".gitignore");

  if (!existsSync(templatePath)) return null;
  if (!existsSync(projectPath)) return "missing";
  if (!gitignoreCoversEnvLocal(readFileSync(projectPath, "utf-8"))) return "needs-update";
  return null;
}

function applyGitignore(): "created" | "appended" | null {
  const projectPath = join(projectRoot, ".gitignore");
  const templatePath = join(templateDir, ".gitignore");

  if (!existsSync(templatePath)) return null;

  if (!existsSync(projectPath)) {
    mkdirSync(dirname(projectPath), { recursive: true });
    writeFileSync(projectPath, readFileSync(templatePath, "utf-8"));
    return "created";
  }

  const content = readFileSync(projectPath, "utf-8");
  if (gitignoreCoversEnvLocal(content)) return null;

  const prefix = content.length > 0 && !content.endsWith("\n") ? "\n" : "";
  appendFileSync(projectPath, prefix + GITIGNORE_ENV_LOCAL_BLOCK);
  return "appended";
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

  const gitignoreStatus = checkGitignore();

  if (missing.length === 0 && !gitignoreStatus) {
    console.log("ritus: project files up to date (v" + pluginVersion + ")");
    return;
  }

  if (missing.length > 0) {
    console.log("ritus: " + missing.length + " file(s) missing. Re-run this script with --apply to create them.");
    for (const f of missing) console.log("  + " + f);
  }

  if (gitignoreStatus === "missing") {
    console.log("ritus: .gitignore missing. Re-run this script with --apply to create it (ignores .env.local).");
  } else if (gitignoreStatus === "needs-update") {
    console.log("ritus: .gitignore does not ignore .env.local. Re-run this script with --apply to append it.");
  }
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

    skipped.push({ file, reason: getStrategy(file) + " — already exists" });
  }

  const gitignoreResult = applyGitignore();
  if (gitignoreResult === "created") {
    created.push(".gitignore");
  } else if (gitignoreResult === "appended") {
    console.log("Updated .gitignore: appended .env.local so local secrets are never committed.");
  }

  if (created.length > 0) {
    console.log("Created " + created.length + " file(s):");
    for (const f of created) console.log("  + " + f);
  }

  if (skipped.length > 0) {
    console.log("Skipped " + skipped.length + " file(s):");
    for (const entry of skipped) console.log("  - " + entry.file + " (" + entry.reason + ")");
  }

  if (created.length === 0 && !gitignoreResult) {
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
