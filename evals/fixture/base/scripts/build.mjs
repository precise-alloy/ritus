// "Build" for a plain ESM package: syntax-check and link every module under src/, then record the result in
// dist/build-info.json for the release job.
import { spawnSync } from 'node:child_process';
import { mkdir, readdir, writeFile } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const files = (await readdir('src', { recursive: true })).filter((file) => file.endsWith('.js')).sort();
const failures = [];

for (const file of files) {
  const path = join('src', file);
  const check = spawnSync(process.execPath, ['--check', path], { encoding: 'utf8' });
  if (check.status !== 0) {
    failures.push(`${path}: ${check.stderr.trim()}`);
    continue;
  }
  try {
    await import(pathToFileURL(resolve(path)).href);
  } catch (error) {
    failures.push(`${path}: ${error.message}`);
  }
}

await mkdir('dist', { recursive: true });
await writeFile(
  'dist/build-info.json',
  JSON.stringify({ builtAt: new Date().toISOString(), modules: files, ok: failures.length === 0, failures }, null, 2),
);

if (failures.length > 0) {
  console.error(`build failed:\n${failures.join('\n')}`);
  process.exit(1);
}
console.log(`build ok: ${files.length} modules`);
