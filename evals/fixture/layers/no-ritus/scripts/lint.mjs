// Project lint rules (money, ledger access, output). Writes .cache/lint-report.json.
import { mkdir, readdir, readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

const CLI = join('src', 'cli.js');
const RULES = [
  { id: 'no-var', dirs: ['src', 'test'], message: 'use const or let', test: (line) => /\bvar\s/.test(line) },
  {
    id: 'no-console',
    dirs: ['src'],
    message: 'only src/cli.js prints',
    test: (line, file) => file !== CLI && /\bconsole\.(log|info|debug)\b/.test(line),
  },
  {
    id: 'async-io',
    dirs: ['src'],
    message: 'use node:fs/promises (D-003)',
    test: (line) => /\b(readFileSync|writeFileSync|appendFileSync|renameSync)\b/.test(line),
  },
  { id: 'trailing-space', dirs: ['src', 'test'], message: 'trailing whitespace', test: (line) => /[ \t]+$/.test(line) },
];

const problems = [];
for (const dir of ['src', 'test']) {
  const files = (await readdir(dir, { recursive: true })).filter((file) => file.endsWith('.js')).sort();
  for (const name of files) {
    const file = join(dir, name);
    const lines = (await readFile(file, 'utf8')).split(/\r?\n/);
    lines.forEach((line, index) => {
      for (const rule of RULES) {
        if (rule.dirs.includes(dir) && rule.test(line, file)) {
          problems.push({ file, line: index + 1, rule: rule.id, message: rule.message });
        }
      }
    });
  }
}

await mkdir('.cache', { recursive: true });
await writeFile(
  '.cache/lint-report.json',
  JSON.stringify({ checkedAt: new Date().toISOString(), problems }, null, 2),
);

for (const problem of problems) {
  console.error(`${problem.file}:${problem.line}  ${problem.rule}  ${problem.message}`);
}
if (problems.length > 0) {
  console.error(`lint failed: ${problems.length} problem(s)`);
  process.exit(1);
}
console.log('lint ok');
