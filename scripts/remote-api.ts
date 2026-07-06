#!/usr/bin/env bun

import { loadLocalEnv, requireEnv } from './providers/http.ts';
import type { EnvCheckResult, EnvKeyStatus, Provider, ProviderEnvStatus } from './providers/types.ts';
import { jiraProvider } from './providers/provider-jira.ts';
import { adoProvider } from './providers/provider-ado.ts';
import { githubProvider } from './providers/provider-github.ts';

const PROVIDERS: Provider[] = [jiraProvider, adoProvider, githubProvider];
const PROVIDER_MAP = new Map(PROVIDERS.map((p) => [p.name, p]));

const HELP_FLAGS = new Set(['-h', '--help', 'help']);

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
${usageLines.map((l) => '  ' + l).join('\n')}

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

async function checkEnv(): Promise<EnvCheckResult> {
  const envLocalPath = `${process.cwd()}/.env.local`;
  const envLocalExists = await Bun.file(envLocalPath).exists();

  const providers = PROVIDERS.map(checkProviderEnv);
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
  const result = await checkEnv();
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

  const [system, action, target, extra] = getCliArgs(Bun.argv);
  if (!system) {
    printUsage();
    process.exit(2);
  }

  if (HELP_FLAGS.has(system)) {
    printUsage();
    process.exit(0);
  }

  if (system === 'check-env') {
    await runCheckEnv();
    return;
  }

  const provider = PROVIDER_MAP.get(system);
  if (!provider) {
    printUsage();
    process.exit(2);
  }

  if (!action || !target) {
    printUsage();
    process.exit(2);
  }

  if (provider.name === 'github') {
    if (!process.env.GITHUB_TOKEN?.trim() && !process.env.GH_TOKEN?.trim()) {
      throw new Error('Missing GITHUB_TOKEN (or GH_TOKEN). Populate it in .env.local before using this helper.');
    }
  } else {
    for (const key of provider.requiredEnvKeys) {
      requireEnv(key);
    }
  }

  const handler = provider.actions[action];
  if (!handler) {
    console.error(`Unknown action "${action}" for ${provider.label}. Available: ${Object.keys(provider.actions).join(', ')}`);
    printUsage();
    process.exit(2);
  }

  const result = await handler(target, extra);
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
