#!/usr/bin/env bun

import { loadLocalEnv, requireEnv } from './providers/http.ts';
import type { EnvCheckResult, EnvKeyStatus, EnvMapping, Provider, ProviderEnvStatus, ProviderInstance, ProviderInstanceConfig } from './providers/types.ts';
import { jiraProvider } from './providers/provider-jira.ts';
import { adoProvider } from './providers/provider-ado.ts';
import { githubProvider } from './providers/provider-github.ts';

const PROVIDERS: Provider[] = [jiraProvider, adoProvider, githubProvider];
const PROVIDER_MAP = new Map(PROVIDERS.map((p) => [p.name, p]));

const HELP_FLAGS = new Set(['-h', '--help', 'help']);

// ---------------------------------------------------------------------------
// team.yml parsing — extracts ticket_providers / git_providers lists
// ---------------------------------------------------------------------------

type RawProviderEntry = {
  type?: string;
  name?: string;
  key_prefixes?: string[];
  env?: Record<string, string>;
};

function validateAndConvertEntries(entries: unknown, sectionName: string): ProviderInstanceConfig[] {
  if (!Array.isArray(entries)) return [];

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
      const rawPrefixes = raw.key_prefixes.map(p => String(p).trim());
      for (const p of rawPrefixes) {
        if (!p) {
          console.warn(`Warning: skipping empty key_prefix for ${type}:${name}`);
        }
      }
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
        const envVarName = String(val).trim();
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

function parseTeamYaml(content: string): { ticketProviders?: ProviderInstanceConfig[]; gitProviders?: ProviderInstanceConfig[] } {
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
  let gitProviders: ProviderInstanceConfig[] | undefined;

  if (parsed.ticket_providers) {
    const items = validateAndConvertEntries(parsed.ticket_providers, 'ticket_providers');
    if (items.length > 0) ticketProviders = items;
  }

  if (parsed.git_providers) {
    const items = validateAndConvertEntries(parsed.git_providers, 'git_providers');
    if (items.length > 0) gitProviders = items;
  }

  return { ticketProviders, gitProviders };
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
  const { ticketProviders, gitProviders } = parseTeamYaml(content);

  if (!ticketProviders && !gitProviders) {
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

  if (gitProviders) {
    for (const config of gitProviders) {
      const provider = PROVIDERS.find(p => p.name === config.type);
      if (!provider) {
        console.warn(`Warning: unknown provider type "${config.type}" in team.yml git_providers (available: ${PROVIDERS.map(p => p.name).join(', ')})`);
        continue;
      }
      if (provider) {
        const key = `${provider.name}:${config.name}`;
        if (!seen.has(key)) {
          seen.add(key);
          const inst = buildInstance(provider, config);
          if (config.env) {
            const knownLogicalKeys = new Set(Object.keys(provider.defaultEnvMapping));
            for (const logicalKey of Object.keys(config.env)) {
              if (!knownLogicalKeys.has(logicalKey)) {
                console.warn(`Warning: unknown env key "${logicalKey}" in team.yml git_providers entry "${config.name}" (known keys: ${[...knownLogicalKeys].join(', ')})`);
              }
            }
          }
          instances.push(inst);
        }
      }
    }
  }

  // Add default instances for providers not covered by team.yml lists
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

  if (!(action in provider.actions)) return false;

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

  const instanceOrg = process.env[orgEnvVar]?.trim();
  const instanceProject = process.env[projectEnvVar]?.trim();
  if (!instanceOrg || !instanceProject) return instance.config.name === 'default';

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

  Provider-agnostic (auto-detect):
    ${cmd} <action> <target> [extra]

  Explicit provider:
${usageLines.map((l) => '    ' + l).join('\n')}

Examples:
${exampleLines.map((l) => '  ' + l).join('\n')}`);
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
      // No match — fall back to default instance for this provider
      const defaultInstance = instances.find(
        (inst) => inst.provider.name === explicitProvider.name && inst.config.name === 'default',
      );
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
      if (configuredNames.length > 0) {
        console.error(`Configured providers: ${configuredNames.join(', ')}`);
      } else {
        console.error('No providers are configured. Run check-env for details.');
      }
      console.error(`\nTo use a specific provider: ${getScriptCmd()} <provider> ${action} ${target}`);
      process.exit(2);
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
