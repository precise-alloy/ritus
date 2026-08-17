#!/usr/bin/env bun

import { readdirSync, readFileSync, realpathSync, statSync } from "node:fs";
import { delimiter, dirname, join, resolve } from "node:path";

type HookInput = {
  cwd?: unknown;
};

type CompanionIntegration = {
  skill: string;
  prompt: string;
};

type CompanionManifest = {
  name: string;
  integrations: CompanionIntegration[];
};

type LoadedCompanion = {
  manifest: CompanionManifest;
  path: string;
};

const MAX_MANIFESTS = 25;
const MANIFEST_FILE = "ritus-companion.json";
const SKIP_DIRS = new Set(["node_modules", ".git"]);

function readHookInput(): HookInput {
  try {
    const input = readFileSync(0, "utf-8").trim();
    if (!input) return {};
    return JSON.parse(input) as HookInput;
  } catch {
    return {};
  }
}

function isDirectory(path: string): boolean {
  try {
    return statSync(path).isDirectory();
  } catch {
    return false;
  }
}

function isFile(path: string): boolean {
  try {
    return statSync(path).isFile();
  } catch {
    return false;
  }
}

function readDirSafe(dir: string) {
  try {
    return readdirSync(dir, { withFileTypes: true });
  } catch {
    return [];
  }
}

function canonical(path: string): string {
  try {
    return realpathSync(path);
  } catch {
    return resolve(path);
  }
}

function addManifestFile(paths: Set<string>, file: string): void {
  if (paths.size >= MAX_MANIFESTS) return;
  if (isFile(file) && file.endsWith(MANIFEST_FILE)) paths.add(canonical(file));
}

function addManifestInDir(paths: Set<string>, dir: string | undefined): void {
  if (!dir || paths.size >= MAX_MANIFESTS || !isDirectory(dir)) return;
  addManifestFile(paths, join(dir, MANIFEST_FILE));
}

function addPath(paths: Set<string>, path: string | undefined): void {
  if (!path || paths.size >= MAX_MANIFESTS) return;
  const resolved = resolve(path);
  if (isDirectory(resolved)) {
    addManifestFile(paths, join(resolved, MANIFEST_FILE));
  } else {
    addManifestFile(paths, resolved);
  }
}

// Companion plugins install as siblings of this plugin; Claude nests each under
// a version dir (<marketplace>/<plugin>/<version>), so scan sibling plugin dirs
// and their version subdirs from both the parent and grandparent of pluginRoot.
function addPluginSiblings(paths: Set<string>, pluginRoot: string | undefined): void {
  if (!pluginRoot || paths.size >= MAX_MANIFESTS) return;

  const marketplaceRoots = [dirname(pluginRoot), dirname(dirname(pluginRoot))];
  for (const marketplaceRoot of marketplaceRoots) {
    if (!isDirectory(marketplaceRoot) || paths.size >= MAX_MANIFESTS) continue;

    for (const plugin of readDirSafe(marketplaceRoot)) {
      if (paths.size >= MAX_MANIFESTS) return;
      if (!plugin.isDirectory() || SKIP_DIRS.has(plugin.name)) continue;

      const pluginDir = join(marketplaceRoot, plugin.name);
      addManifestInDir(paths, pluginDir);

      for (const child of readDirSafe(pluginDir)) {
        if (paths.size >= MAX_MANIFESTS) return;
        if (!child.isDirectory() || SKIP_DIRS.has(child.name)) continue;
        addManifestInDir(paths, join(pluginDir, child.name));
      }
    }
  }
}

function splitPathList(value: string | undefined): string[] {
  if (!value) return [];
  return value
    .split(delimiter)
    .map((path) => path.trim())
    .filter(Boolean);
}

function discoverManifestPaths(hookInput: HookInput): string[] {
  const paths = new Set<string>();
  const cwd = typeof hookInput.cwd === "string" ? hookInput.cwd : process.cwd();
  const projectRoot = process.env.CLAUDE_PROJECT_DIR || cwd;
  const pluginRoot = process.env.CLAUDE_PLUGIN_ROOT || process.env.PLUGIN_ROOT;

  for (const explicitPath of splitPathList(process.env.RITUS_COMPANION_PATHS)) {
    addPath(paths, explicitPath);
  }

  // Project/workspace: the manifest must live at the repo root — no deep scan.
  addManifestInDir(paths, projectRoot);

  // Installed companion plugins: this plugin's dir plus sibling plugin dirs.
  addManifestInDir(paths, pluginRoot);
  addPluginSiblings(paths, pluginRoot);

  return Array.from(paths).slice(0, MAX_MANIFESTS);
}

function validateManifest(value: unknown): CompanionManifest | null {
  if (!value || typeof value !== "object") return null;

  const manifest = value as Record<string, unknown>;
  if (typeof manifest.name !== "string" || manifest.name.trim().length === 0) return null;
  if (!Array.isArray(manifest.integrations)) return null;

  const integrations: CompanionIntegration[] = [];
  for (const entry of manifest.integrations) {
    if (!entry || typeof entry !== "object") return null;
    const candidate = entry as Record<string, unknown>;
    if (typeof candidate.skill !== "string" || candidate.skill.trim().length === 0) return null;
    if (typeof candidate.prompt !== "string" || candidate.prompt.trim().length === 0) return null;
    integrations.push({ skill: candidate.skill.trim(), prompt: candidate.prompt.trim() });
  }

  if (integrations.length === 0) return null;

  return { name: manifest.name.trim(), integrations };
}

function loadCompanions(paths: string[]): LoadedCompanion[] {
  const companions: LoadedCompanion[] = [];

  for (const path of paths) {
    try {
      const manifest = validateManifest(JSON.parse(readFileSync(path, "utf-8")));
      if (manifest) companions.push({ manifest, path });
    } catch {
      continue;
    }
  }

  companions.sort((left, right) => left.manifest.name.localeCompare(right.manifest.name));
  return companions;
}

function formatRegistry(companions: LoadedCompanion[]): string {
  const lines = [
    "<EXTREMELY_IMPORTANT>",
    "## Ritus Companion Registry",
    "",
    "These are companion extensions to the Ritus workflow. They apply only while this session is executing that workflow - that is, after you invoke a Ritus skill (start-ritus, triage, ticket-review, task-generation, execute-task, verify-task, pr-review, wrap-up, comprehension, brainstorm, debug, address-feedback). Editing Ritus's own source files or discussing Ritus does not count. Until you invoke a Ritus skill, ignore this registry and leave the manifests below unread.",
    "",
    "Each line names a companion manifest on disk. Before you build or update the workflow TODO list, read each manifest below and ensure a TODO exists for every integration at the workflow point it names - add it if missing, never duplicate. Honor these manifests instead of editing core Ritus workflow files.",
    "",
    "Once you invoke a Ritus skill this session, persist this registry: if you have a memory or notes tool, save the companion names and manifest paths to a companion memory file (session scope, e.g. a `ritus-companions` note) so a long context or compaction can't drop them, then re-read that memory whenever you plan or update the workflow TODO.",
    "",
    ...companions.map(({ manifest, path }) => {
      const count = manifest.integrations.length;
      const noun = count === 1 ? "integration" : "integrations";
      return `- ${manifest.name} (${count} ${noun}): ${path}`;
    }),
    "</EXTREMELY_IMPORTANT>",
  ];

  return lines.join("\n");
}

function main(): void {
  const hookInput = readHookInput();
  const companions = loadCompanions(discoverManifestPaths(hookInput));
  if (companions.length === 0) return;

  const context = formatRegistry(companions);

  // Copilot CLI injects only a top-level additionalContext; Claude Code and VS
  // Code Copilot (Claude-format hooks) read it nested under hookSpecificOutput.
  const output = process.env.COPILOT_CLI
    ? { additionalContext: context }
    : { hookSpecificOutput: { hookEventName: "SessionStart", additionalContext: context } };

  process.stdout.write(JSON.stringify(output));
}

main();