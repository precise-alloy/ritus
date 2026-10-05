import { spawnSync } from 'node:child_process';
import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import { dirname, extname, join, resolve } from 'node:path';

async function listFiles(dir, extensions) {
  const names = await readdir(dir, { recursive: true });
  return names.filter((name) => extensions.has(extname(name))).map((name) => join(dir, name)).sort();
}

async function exists(path) {
  try {
    await readFile(path);
    return true;
  } catch {
    return false;
  }
}

async function resolvesImport(fromFile, specifier) {
  if (!specifier.startsWith('.')) {
    return true;
  }
  const base = resolve(dirname(fromFile), specifier);
  const candidates = extname(base) ? [base] : [`${base}.js`, `${base}.mjs`, join(base, 'index.js')];
  for (const candidate of candidates) {
    if (await exists(candidate)) {
      return true;
    }
  }
  return false;
}

function importSpecifiers(source) {
  const specs = [];
  const patterns = [
    /import\s+(?:[^'"]+\s+from\s+)?['"]([^'"]+)['"]/g,
    /export\s+[^'"]+\s+from\s+['"]([^'"]+)['"]/g,
    /import\(\s*['"]([^'"]+)['"]\s*\)/g,
  ];
  for (const pattern of patterns) {
    for (const match of source.matchAll(pattern)) {
      specs.push(match[1]);
    }
  }
  return specs;
}

const files = [...await listFiles('src', new Set(['.js'])), ...await listFiles('scripts', new Set(['.js', '.mjs']))];
const failures = [];

for (const file of files) {
  const check = spawnSync(process.execPath, ['--check', file], { encoding: 'utf8' });
  if (check.status !== 0) {
    failures.push(`${file}: ${check.stderr.trim()}`);
    continue;
  }
  const source = await readFile(file, 'utf8');
  for (const specifier of importSpecifiers(source)) {
    if (!(await resolvesImport(file, specifier))) {
      failures.push(`${file}: unresolved import ${specifier}`);
    }
  }
}

await mkdir('dist', { recursive: true });
await writeFile('dist/build-info.json', JSON.stringify({ builtAt: new Date().toISOString(), files, ok: failures.length === 0, failures }, null, 2));

if (failures.length > 0) {
  console.error(`build failed:\n${failures.join('\n')}`);
  process.exit(1);
}
console.log(`build ok: ${files.length} files`);
