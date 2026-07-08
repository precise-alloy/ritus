#!/usr/bin/env bun

import { loadLocalEnv, requireEnv } from './providers/http.ts';
import type { EnvCheckResult, EnvKeyStatus, EnvMapping, Provider, ProviderEnvStatus, ProviderInstance, ProviderInstanceConfig } from './providers/types.ts';
import { jiraProvider } from './providers/provider-jira.ts';
import { adoProvider, normalizeAdoOrg } from './providers/provider-ado.ts';
import { githubProvider } from './providers/provider-github.ts';

const PROVIDERS: Provider[] = [jiraProvider, adoProvider, githubProvider];
const PROVIDER_MAP = new Map(PROVIDERS.map((p) => [p.name, p]));

const HELP_FLAGS = new Set(['-h', '--help', 'help']);

// ---------------------------------------------------------------------------
// team.yml parsing — extracts ticket_providers list
// ---------------------------------------------------------------------------

type RawProviderEntry = {
  type?: string;
  name?: string;
  key_prefixes?: string[];
  env?: Record<string, string>;
};

function validateAndConvertEntries(entries: unknown, sectionName: string): ProviderInstanceConfig[] {
  if (entries == null) return [];
  if (!Array.isArray(entries)) {
    console.warn(`Warning: team.yml ${sectionName} must be a list`);
    return [];
  }
  const configs: ProviderInstanceConfig[] = [];
  for (const entry of entries) {
    if (!entry || typeof entry !== 'object') continue;
    const raw = entry as RawProviderEntry;

    const type = typeof raw.type === 'string' ? raw.type.trim() : '';
    const name = typeof raw.name === 'string' ? raw.name.trim() : '';

    if (!type) {
      console.warn(`Warning: skipping team.yml ${sectionName} entry with empty "type"`);
      continue;
    }
    if (!name) {
      console.warn(`Warning: skipping team.yml ${sectionName} entry with empty "name"`);
      continue;
    }

    const config: ProviderInstanceConfig = { type, name };

    const knownKeys = new Set(['type', 'name', 'key_prefixes', 'env']);
    const unknownKeys = Object.keys(raw).filter(k => !knownKeys.has(k));
    if (unknownKeys.length > 0) {
      console.warn(`Warning: unknown keys in team.yml ${sectionName} entry "${name}": ${unknownKeys.join(', ')}`);
    }

    if (raw.key_prefixes) {
      if (!Array.isArray(raw.key_prefixes)) {
        console.warn(`Warning: skipping team.yml ${sectionName} entry "${name}": "key_prefixes" must be a list, got ${typeof raw.key_prefixes}`);
        continue;
      }
      // Non-alphanumeric prefixes (e.g. "#") are intentionally allowed:
      // GitHub uses hostname matching (not prefix matching) for routing,
      // so the prefix field is only used by Jira-style providers.
      const rawPrefixes = raw.key_prefixes.map((p) => {
        if (typeof p !== 'string') {
          console.warn(`Warning: skipping non-string key_prefix for ${type}:${name}`);
          return '';
        }
        const trimmed = p.trim();
        if (!trimmed) console.warn(`Warning: skipping empty key_prefix for ${type}:${name}`);
        return trimmed;
      });
      const prefixes = rawPrefixes.filter(Boolean);
      if (prefixes.length > 0) config.keyPrefixes = prefixes;
    }

    if (raw.env && Array.isArray(raw.env)) {
      console.warn(`Warning: skipping team.yml ${sectionName} entry "${name}": "env" must be a plain object, not an array`);
      continue;
    }

    if (raw.env && typeof raw.env === 'object') {
      const envObj: EnvMapping = {};
      let hasInvalidEnv = false;
      for (const [key, val] of Object.entries(raw.env)) {
        if (typeof val !== 'string' || !val.trim()) {
          console.warn(`Warning: skipping team.yml ${sectionName} entry "${name}": env var name for key "${key}" must be a non-empty string`);
          hasInvalidEnv = true;
          break;
        }
        const envVarName = val.trim();
        if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(envVarName)) {
          console.warn(`Warning: skipping team.yml ${sectionName} entry "${name}": invalid env var name "${envVarName}" for key "${key}" (must match [A-Za-z_][A-Za-z0-9_]*)`);
          hasInvalidEnv = true;
          break;
        }
        envObj[key] = envVarName;
      }
      if (hasInvalidEnv) continue;
      config.env = envObj;
    }

    configs.push(config);
  }

  return configs;
}

function parseTeamYaml(content: string): { ticketProviders?: ProviderInstanceConfig[] } {
  let parsed: Record<string, unknown> | null;
  try {
    parsed = Bun.YAML.parse(content) as Record<string, unknown> | null;
  } catch (err) {
    throw new Error(`Failed to parse team.yml: ${err instanceof Error ? err.message : String(err)}`);
  }
  if (!parsed || typeof parsed !== 'object') {
    return {};
  }

  let ticketProviders: ProviderInstanceConfig[] | undefined;

  if (parsed.ticket_providers) {
    const items = validateAndConvertEntries(parsed.ticket_providers, 'ticket_providers');
    if (items.length > 0) ticketProviders = items;
  }

  return { ticketProviders };
}

// ---------------------------------------------------------------------------
// Instance loading — builds ProviderInstance[] from team.yml or defaults
// ---------------------------------------------------------------------------

type LoadedInstances = {
  instances: ProviderInstance[];
  hasTeamConfig: boolean;
};

function buildInstance(provider: Provider, config: ProviderInstanceConfig): ProviderInstance {
  const envMapping = config.env
    ? { ...provider.defaultEnvMapping, ...config.env }
    : { ...provider.defaultEnvMapping };
  return { provider, config, envMapping };
}

async function loadInstances(): Promise<LoadedInstances> {
  const teamYamlPath = `${process.cwd()}/docs/profiles/team.yml`;
  const file = Bun.file(teamYamlPath);

  if (!(await file.exists())) {
    return { instances: buildDefaultInstances(), hasTeamConfig: false };
  }

  const content = await file.text();
  const { ticketProviders } = parseTeamYaml(content);

  if (!ticketProviders) {
    return { instances: buildDefaultInstances(), hasTeamConfig: false };
  }

  const instances: ProviderInstance[] = [];
  const seen = new Set<string>();

  if (ticketProviders) {
    for (const config of ticketProviders) {
      const provider = PROVIDERS.find(p => p.name === config.type);
      if (!provider) {
        console.warn(`Warning: unknown provider type "${config.type}" in team.yml ticket_providers (available: ${PROVIDERS.map(p => p.name).join(', ')})`);
        continue;
      }
      if (provider) {
        const key = `${provider.name}:${config.name}`;
        if (!seen.has(key)) {
          seen.add(key);
          const inst = buildInstance(provider, config);
          if (config.env) {
            const knownLogicalKeys = new Set(Object.keys(provider.defaultEnvMapping));
            if (provider.name === 'github') {
              knownLogicalKeys.add('api_base_url');
              knownLogicalKeys.add('repo_url');
            }
            for (const logicalKey of Object.keys(config.env)) {
              if (!knownLogicalKeys.has(logicalKey)) {
                console.warn(`Warning: unknown env key "${logicalKey}" in team.yml ticket_providers entry "${config.name}" (known keys: ${[...knownLogicalKeys].join(', ')})`);
              }
            }
          }
          instances.push(inst);
        }
      }
    }
  }

  // Add default instances for providers not covered by team.yml ticket_providers
  const coveredTypes = new Set(instances.map(i => i.provider.name));
  for (const provider of PROVIDERS) {
    if (!coveredTypes.has(provider.name)) {
      instances.push(buildInstance(provider, { type: provider.name, name: 'default' }));
    }
  }

  return { instances, hasTeamConfig: true };
}

function buildDefaultInstances(): ProviderInstance[] {
  return PROVIDERS.map(provider =>
    buildInstance(provider, { type: provider.name, name: 'default' }),
  );
}

// ---------------------------------------------------------------------------
// Instance-aware target matching
// ---------------------------------------------------------------------------

function canInstanceHandleTarget(instance: ProviderInstance, action: string, target: string): boolean {
  const { provider, config } = instance;

  if (!Object.hasOwn(provider.actions, action)) return false;

  // GitHub: custom hostname matching for GHE support
  if (provider.name === 'github') {
    return canGitHubInstanceHandle(instance, action, target);
  }

  // ADO: org/project matching for multi-instance
  if (provider.name === 'ado') {
    return canAdoInstanceHandle(instance, action, target);
  }

  // Jira (and others): standard canHandleTarget + key prefix filtering
  if (!provider.canHandleTarget(action, target)) return false;

  if (config.keyPrefixes && config.keyPrefixes.length > 0) {
    const key = extractTicketPrefix(target);
    if (key) {
      return config.keyPrefixes.some(p => p.toUpperCase() === key);
    }
  }

  return true;
}

function extractTicketPrefix(target: string): string | undefined {
  const bareMatch = target.match(/^([A-Z][A-Z0-9]+)-\d+$/i);
  if (bareMatch) return bareMatch[1].toUpperCase();
  const urlMatch = target.match(/\/browse\/([A-Z][A-Z0-9]+)-\d+/i);
  if (urlMatch) return urlMatch[1].toUpperCase();
  return undefined;
}

function canGitHubInstanceHandle(instance: ProviderInstance, action: string, target: string): boolean {
  // Delegate path-pattern matching to the provider
  if (!instance.provider.canHandleTarget(action, target)) return false;

  // Handle #-prefixed numbers (e.g., #18): check if repo_url env var is set and hostname matches
  if (/^#\d+$/.test(target)) {
    const repoUrlEnvVar = instance.envMapping.repo_url;
    if (!repoUrlEnvVar) return false;
    const repoUrl = process.env[repoUrlEnvVar]?.trim();
    if (!repoUrl) return false;

    let repoHostname: string;
    try {
      repoHostname = new URL(repoUrl).hostname;
    } catch {
      console.warn(`Warning: invalid ${repoUrlEnvVar} value — must be a valid URL (e.g., https://github.com/owner/repo).`);
      return false;
    }

    const expectedHostname = getExpectedGitHubHostname(instance.envMapping);
    return repoHostname.toLowerCase() === expectedHostname.toLowerCase();
  }

  // Add hostname disambiguation for multi-instance (github.com vs GHE)
  let url: URL;
  try {
    url = new URL(target);
  } catch {
    return false;
  }

  const expectedHostname = getExpectedGitHubHostname(instance.envMapping);
  return url.hostname.toLowerCase() === expectedHostname.toLowerCase();
}

function getExpectedGitHubHostname(envMapping: EnvMapping): string {
  if (envMapping.api_base_url) {
    const apiUrl = process.env[envMapping.api_base_url]?.trim();
    if (apiUrl) {
      try {
        return new URL(apiUrl).hostname;
      } catch { /* fall through */ }
    }
  }
  return 'github.com';
}

function canAdoInstanceHandle(instance: ProviderInstance, action: string, target: string): boolean {
  if (!instance.provider.canHandleTarget(action, target)) return false;

  const isBareId = /^\d+$/.test(target);
  const { envMapping } = instance;
  const orgEnvVar = envMapping.org;
  const projectEnvVar = envMapping.project;

  if (isBareId) {
    if (!orgEnvVar || !projectEnvVar) return false;
    const instanceOrg = process.env[orgEnvVar]?.trim();
    const instanceProject = process.env[projectEnvVar]?.trim();
    return !!(instanceOrg && instanceProject);
  }

  if (!orgEnvVar || !projectEnvVar) return instance.config.name === 'default';

  const rawOrg = process.env[orgEnvVar]?.trim();
  const rawProject = process.env[projectEnvVar]?.trim();
  if (!rawOrg || !rawProject) return instance.config.name === 'default';

  const instanceOrg = normalizeAdoOrg(rawOrg);
  const instanceProject = decodeURIComponent(rawProject);

  try {
    const url = new URL(target);
    const segments = url.pathname.split('/').filter(Boolean).map(s => decodeURIComponent(s));
    let urlOrg: string | undefined;
    let urlProject: string | undefined;
    const host = url.hostname.toLowerCase();

    if (host === 'dev.azure.com' && segments.length >= 2) {
      urlOrg = segments[0];
      urlProject = segments[1];
    } else if (host.endsWith('.visualstudio.com')) {
      urlOrg = host.replace('.visualstudio.com', '');
      urlProject = segments[0];
    }

    if (urlOrg && urlProject) {
      return urlOrg.toLowerCase() === instanceOrg.toLowerCase() &&
             urlProject.toLowerCase() === instanceProject.toLowerCase();
    }
  } catch {
    // Not a URL — should have been caught by isBareId check above
  }

  return false;
}

// ---------------------------------------------------------------------------
// Instance-aware credential checking
// ---------------------------------------------------------------------------

function checkInstanceEnv(instance: ProviderInstance): ProviderEnvStatus {
  // Check credential/auth keys from provider.requiredEnvKeys, plus api_base_url for GitHub.
  // Non-auth keys like ADO_ORG/ADO_PROJECT should not affect the ok status.
  const requiredEnvVarNames = new Set(instance.provider.requiredEnvKeys);
  const envMapping = instance.envMapping;

  // Map required env keys through the instance's env mapping to get actual env var names
  const keys: EnvKeyStatus[] = Object.entries(envMapping)
    .filter(([logicalKey]) => {
      if (logicalKey === 'api_base_url') return instance.provider.name === 'github';
      const defaultEnvVar = instance.provider.defaultEnvMapping[logicalKey];
      if (defaultEnvVar && requiredEnvVarNames.has(defaultEnvVar)) return true;
      return requiredEnvVarNames.has(envMapping[logicalKey]);
    })
    .map(([, envVarName]) => ({
      name: envVarName,
      present: !!process.env[envVarName]?.trim(),
    }));

  // GitHub special case: GH_TOKEN fallback for GITHUB_TOKEN
  if (instance.provider.name === 'github') {
    const tokenKey = keys.find(k => k.name === 'GITHUB_TOKEN');
    if (tokenKey && !tokenKey.present && !!process.env.GH_TOKEN?.trim()) {
      tokenKey.present = true;
    }
  }

  const hasMultipleOfType = instance.config.name !== 'default';
  const label = hasMultipleOfType
    ? `${instance.provider.label} (${instance.config.name})`
    : instance.provider.label;

  return {
    name: hasMultipleOfType ? `${instance.provider.name}-${instance.config.name}` : instance.provider.name,
    label,
    keys,
    ok: keys.every(k => k.present),
  };
}

function getScriptCmd(): string {
  const scriptPath = Bun.argv[1] === 'run' ? Bun.argv[2] : Bun.argv[1];
  return `bun run ${scriptPath}`;
}

function getCliArgs(argv: string[]): string[] {
  if (argv[1] === 'run') {
    return argv.slice(3);
  }

  return argv.slice(2);
}

function printUsage(): void {
  const cmd = getScriptCmd();
  const usageLines = PROVIDERS.flatMap((p) => p.usageLines(cmd));
  const exampleLines = PROVIDERS.flatMap((p) => p.exampleLines(cmd));
  console.error(`Usage:
  ${cmd} check-env
  ${cmd} generate-env

  Provider-agnostic (auto-detect):
    ${cmd} <action> <target> [extra]

  Explicit provider:
${usageLines.map((l) => '    ' + l).join('\n')}

  Target formats:
    Jira:       PROJ-123 (key prefix routes to correct instance)
    ADO:        340796 (bare number) or full work item URL
    GitHub:     #18 (requires GITHUB_REPO_URL) or full PR/issue URL

Examples:
${exampleLines.map((l) => '  ' + l).join('\n')}

  Auto-detect (provider inferred from target format):
    ${cmd} issue AMPS-123                    # → Jira (key prefix match)
    ${cmd} issue 340796                      # → ADO (bare number)
    ${cmd} pr '#18'                          # → GitHub (#-prefixed number)
    ${cmd} comments '#18'                    # → GitHub PR comments

  Multi-instance (configured via docs/profiles/team.yml):
    # Two Jira instances with different key prefixes:
    #   ticket_providers:
    #     - type: jira
    #       name: primary
    #       key_prefixes: ["AMPS", "AMP"]
    #     - type: jira
    #       name: external
    #       key_prefixes: ["EXT"]
    #       env:
    #         base_url: JIRA_EXT_BASE_URL
    #         pat: JIRA_EXT_PAT
    #         email: JIRA_EXT_EMAIL
    ${cmd} issue AMPS-123                    # → Jira (primary)
    ${cmd} issue EXT-456                     # → Jira (external)

  Generate .env.example from team.yml:
    ${cmd} generate-env > .env.example`);
}

function checkProviderEnv(provider: Provider): ProviderEnvStatus {
  const keys: EnvKeyStatus[] = provider.requiredEnvKeys.map((name) => ({
    name,
    present: !!process.env[name]?.trim(),
  }));

  // GitHub special case: accept GH_TOKEN as fallback for GITHUB_TOKEN
  if (provider.name === 'github') {
    const ghKey = keys.find((k) => k.name === 'GITHUB_TOKEN');
    if (ghKey && !ghKey.present && !!process.env.GH_TOKEN?.trim()) {
      ghKey.present = true;
    }
  }

  return {
    name: provider.name,
    label: provider.label,
    keys,
    ok: keys.every((k) => k.present),
  };
}

async function checkEnv(loaded?: LoadedInstances): Promise<EnvCheckResult> {
  const envLocalPath = `${process.cwd()}/.env.local`;
  const envLocalExists = await Bun.file(envLocalPath).exists();

  const { instances, hasTeamConfig } = loaded ?? await loadInstances();

  let providers: ProviderEnvStatus[];
  if (hasTeamConfig) {
    providers = instances.map(checkInstanceEnv);
  } else {
    providers = PROVIDERS.map(checkProviderEnv);
  }

  const keys = providers.flatMap((p) => p.keys);
  const missing = keys.filter((k) => !k.present).map((k) => k.name);

  return {
    envLocalPath,
    envLocalExists,
    providers,
    keys,
    missing,
    ok: envLocalExists && providers.some((p) => p.ok),
  };
}

async function runCheckEnv(): Promise<void> {
  const loaded = await loadInstances();
  const result = await checkEnv(loaded);
  console.log(JSON.stringify(result, null, 2));

  if (!result.envLocalExists) {
    console.error(`\n.env.local is missing at ${result.envLocalPath}.`);
    console.error('Create it with the keys you need:\n');

    if (loaded.hasTeamConfig) {
      const seen = new Set<string>();
      for (const inst of loaded.instances) {
        const { provider, config, envMapping } = inst;
        const isCustom = config.name !== 'default';
        const header = isCustom ? `${provider.label} (${config.name})` : provider.label;
        console.error(`  # ${header}`);
        for (const [, envVarName] of Object.entries(envMapping)) {
          if (typeof envVarName !== 'string' || !envVarName) continue;
          if (seen.has(envVarName)) continue;
          seen.add(envVarName);
          console.error(`  ${envVarName}=`);
        }
        if (provider.name === 'github' && !seen.has('GH_TOKEN')) {
          seen.add('GH_TOKEN');
          console.error('  # Optional: alternative token name used by GitHub CLI');
          console.error('  GH_TOKEN=');
        }
        console.error('');
      }
    } else {
      for (const provider of PROVIDERS) {
        console.error(`  # ${provider.label}`);
        for (const key of provider.requiredEnvKeys) {
          console.error(`  ${key}=`);
        }
        if (provider.name === 'github') {
          console.error('  # Optional: alternative token name used by GitHub CLI');
          console.error('  GH_TOKEN=');
        }
        console.error('');
      }
    }

    console.error(`Tip: run \`${getScriptCmd()} generate-env\` to generate a complete .env.local template.`);
    process.exit(1);
  }

  const configured = result.providers.filter((p) => p.ok);
  const unconfigured = result.providers.filter((p) => !p.ok);

  if (configured.length === 0) {
    console.error('\nNo providers are fully configured.');
    for (const p of unconfigured) {
      const missing = p.keys.filter((k) => !k.present).map((k) => k.name);
      console.error(`  ${p.label}: missing ${missing.join(', ')}`);
    }
    console.error('\nFill at least one provider in .env.local.');
    process.exit(1);
  }

  for (const p of configured) {
    console.error(`${p.label}: ✓ configured`);
  }
  for (const p of unconfigured) {
    const missing = p.keys.filter((k) => !k.present).map((k) => k.name);
    console.error(`${p.label}: ✗ not configured (${missing.join(', ')})`);
  }

  process.exit(0);
}

async function runGenerateEnv(): Promise<void> {
  const { instances, hasTeamConfig } = await loadInstances();
  const lines: string[] = [
    '# Generated from provider registry' + (hasTeamConfig ? ' + docs/profiles/team.yml' : ''),
    '# Copy to .env.local and fill in values',
    '',
  ];

  const seen = new Set<string>();
  for (const inst of instances) {
    const { provider, config, envMapping } = inst;
    const isCustom = config.name !== 'default';
    const header = isCustom ? `${provider.label} (${config.name})` : provider.label;

    lines.push(`# ${header}`);

    const requiredSet = new Set(provider.requiredEnvKeys);
    for (const [logicalKey, envVarName] of Object.entries(envMapping)) {
      if (seen.has(envVarName)) continue;
      seen.add(envVarName);
      const defaultVar = provider.defaultEnvMapping[logicalKey];
      const isRequired = (defaultVar && requiredSet.has(defaultVar)) || requiredSet.has(envVarName);
      if (!isRequired) lines.push(`# Optional: ${logicalKey}`);
      lines.push(`${envVarName}=`);
    }

    if (provider.name === 'github') {
      if (!seen.has('GH_TOKEN')) {
        seen.add('GH_TOKEN');
        lines.push('# Optional: alternative token name used by GitHub CLI');
        lines.push('GH_TOKEN=');
      }
    }

    lines.push('');
  }

  console.log(lines.join('\n'));
}

async function main(): Promise<void> {
  await loadLocalEnv();

  const args = getCliArgs(Bun.argv);
  const firstArg = args[0];

  if (!firstArg) {
    printUsage();
    process.exit(2);
  }

  if (HELP_FLAGS.has(firstArg)) {
    printUsage();
    process.exit(0);
  }

  if (firstArg === 'check-env') {
    await runCheckEnv();
    return;
  }

  if (firstArg === 'generate-env') {
    await runGenerateEnv();
    return;
  }

  const { instances } = await loadInstances();

  let provider: Provider;
  let action: string;
  let target: string;
  let extra: string | undefined;
  let resolvedEnvMapping: EnvMapping | undefined;

  if (PROVIDER_MAP.has(firstArg)) {
    // Explicit dispatch: <provider> <action> <target> [extra]
    const explicitProvider = PROVIDER_MAP.get(firstArg)!;
    action = args[1];
    target = args[2];
    extra = args[3];

    if (!action || !target) {
      printUsage();
      process.exit(2);
    }

    if (!Object.hasOwn(explicitProvider.actions, action)) {
      console.error(`Unknown action "${action}" for ${explicitProvider.label}. Available: ${Object.keys(explicitProvider.actions).join(', ')}`);
      printUsage();
      process.exit(2);
    }

    // Resolve the best matching instance for this provider + target
    const matchingInstances = instances.filter(
      (inst) => inst.provider.name === explicitProvider.name &&
                checkInstanceEnv(inst).ok &&
                canInstanceHandleTarget(inst, action, target),
    );

    if (matchingInstances.length === 1) {
      provider = matchingInstances[0].provider;
      resolvedEnvMapping = matchingInstances[0].envMapping;
    } else if (matchingInstances.length > 1) {
      // Multiple instances can handle this target — ambiguous, error out
      const candidateNames = matchingInstances.map((inst) =>
        inst.config.name !== 'default'
          ? `${inst.provider.name} (${inst.config.name})`
          : inst.provider.name,
      ).join(', ');
      console.error(`Ambiguous target: multiple instances can handle "${action} ${target}": ${candidateNames}`);
      console.error('Disambiguate by configuring distinct key_prefixes, hostnames, or org/project in team.yml.');
      process.exit(2);
    } else {
      // No match. If team.yml defines non-default instances for this provider, fail fast instead of
      // silently falling back to default env vars (can route to the wrong host/tenant).
      const providerInstances = instances.filter((inst) => inst.provider.name === explicitProvider.name);
      const hasCustomInstances = providerInstances.length > 1 || providerInstances.some((inst) => inst.config.name !== 'default');

      if (hasCustomInstances) {
        const instanceNames = providerInstances
          .map((inst) => (inst.config.name !== 'default' ? `${inst.provider.name} (${inst.config.name})` : inst.provider.name))
          .join(', ');
        console.error(`No configured ${explicitProvider.name} instance can handle "${action} ${target}". Known instances: ${instanceNames}`);
        console.error('Disambiguate by configuring distinct key_prefixes, hostnames, or org/project in team.yml.');
        process.exit(2);
      }

      // Single-instance (default) fallback remains backward compatible.
      const defaultInstance = providerInstances.find((inst) => inst.config.name === 'default');
      provider = explicitProvider;
      resolvedEnvMapping = defaultInstance?.envMapping;
    }
  } else {
    // Auto-detect mode: <action> <target> [extra]
    action = firstArg;
    target = args[1];
    extra = args[2];

    if (!target) {
      console.error(`Auto-detect mode requires both <action> and <target>.`);
      printUsage();
      process.exit(2);
    }
    if (!PROVIDERS.some((p) => Object.hasOwn(p.actions, action))) {
      const actions = [...new Set(PROVIDERS.flatMap((p) => Object.keys(p.actions)))].sort();
      console.error(`Unknown action "${action}". Available: ${actions.join(', ')}`);
      printUsage();
      process.exit(2);
    }

    const candidates = instances.filter(
      (inst) => checkInstanceEnv(inst).ok && canInstanceHandleTarget(inst, action, target),
    );

    if (candidates.length === 0) {
      const configured = instances.filter((inst) => checkInstanceEnv(inst).ok);
      const configuredNames = configured.map((inst) => {
        const label = inst.config.name !== 'default'
          ? `${inst.provider.name} (${inst.config.name})`
          : `${inst.provider.name} (${inst.provider.label})`;
        return label;
      });
      console.error(`No configured provider can handle: ${action} ${target}`);

      // Helpful hint: bare numeric targets are Azure DevOps work item IDs and require org/project context.
      if (/^\d+$/.test(target) && ['issue', 'comments', 'changelog'].includes(action)) {
        const ado = instances.find((i) => i.provider.name === 'ado');
        if (ado && checkInstanceEnv(ado).ok) {
          const orgVar = ado.envMapping.org ?? 'AZURE_DEVOPS_ORG';
          const projectVar = ado.envMapping.project ?? 'AZURE_DEVOPS_PROJECT';
          console.error(`Note: Azure DevOps bare work item IDs require ${orgVar} and ${projectVar} (or pass the full work item URL).`);
        }
      }

      if (configuredNames.length > 0) {
        console.error(`Configured providers: ${configuredNames.join(', ')}`);
      } else {
        console.error('No providers are configured. Run check-env for details.');
      }
      console.error(`\nTo use a specific provider: ${getScriptCmd()} <provider> ${action} ${target}`);
      process.exit(2);
    }

    if (candidates.length > 1) {
      const isShortRef = /^\d+$/.test(target) || /^#\d+$/.test(target);
      if (isShortRef) {
        // Do not collapse candidates for short refs. Multiple matching instances must remain
        // ambiguous so the disambiguation error below can trigger.
      }
    }

    if (candidates.length > 1) {
      const hasDuplicateTypes = new Set(candidates.map(c => c.provider.name)).size < candidates.length;
      const candidateNames = candidates.map((inst) => {
        return (hasDuplicateTypes || inst.config.name !== 'default')
          ? `${inst.provider.name} (${inst.config.name})`
          : inst.provider.name;
      }).join(', ');

      if (hasDuplicateTypes) {
         console.error(`Ambiguous target: multiple instances can handle "${action} ${target}": ${candidateNames}`);
         console.error('Disambiguate by configuring distinct key_prefixes, hostnames, or org/project in team.yml.');
       } else {
         console.error(`Ambiguous target: multiple providers can handle "${action} ${target}": ${candidateNames}`);
         console.error('Disambiguate by specifying the provider explicitly:');

         for (const c of candidates) {
           console.error(`  ${getScriptCmd()} ${c.provider.name} ${action} ${target}`);
         }
      }
      process.exit(2);
    }

    provider = candidates[0].provider;
    resolvedEnvMapping = candidates[0].envMapping;
  }

  // Validate credentials using resolved env mapping or provider defaults
  const envMapping = resolvedEnvMapping ?? provider.defaultEnvMapping;
  if (provider.name === 'github') {
    const tokenEnvVar = envMapping.token ?? 'GITHUB_TOKEN';
    const token = process.env[tokenEnvVar]?.trim();
    if (!token && tokenEnvVar === 'GITHUB_TOKEN' && !process.env.GH_TOKEN?.trim()) {
      throw new Error('Missing GITHUB_TOKEN (or GH_TOKEN). Populate it in .env.local before using this helper.');
    } else if (!token && tokenEnvVar !== 'GITHUB_TOKEN') {
      throw new Error(`Missing ${tokenEnvVar}. Populate it in .env.local before using this helper.`);
    }
  } else {
    // Only require credential/auth env vars (those in provider.requiredEnvKeys).
    // Non-auth keys like ADO_ORG/ADO_PROJECT are action-specific and resolved by handlers.
    const requiredDefaults = new Set(provider.requiredEnvKeys);
    for (const [logicalKey, envVarName] of Object.entries(envMapping)) {
      if (logicalKey === 'api_base_url') continue;
      const defaultEnvVar = provider.defaultEnvMapping[logicalKey];
      if (defaultEnvVar && requiredDefaults.has(defaultEnvVar)) {
        requireEnv(envVarName);
      }
    }
  }

  const handler = provider.actions[action];
  if (!handler) {
    console.error(`Unknown action "${action}" for ${provider.label}. Available: ${Object.keys(provider.actions).join(', ')}`);
    printUsage();
    process.exit(2);
  }

  const result = await handler(target, extra, resolvedEnvMapping);
  console.log(JSON.stringify(result, null, 2));
}

main().catch((error: unknown) => {
  if (error instanceof Error) {
    console.error(error.message);
  } else {
    console.error(String(error));
  }
  process.exit(1);
});
