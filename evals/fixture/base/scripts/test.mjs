// Runs the test suite with a console report plus a JUnit file for CI (.cache/junit.xml).
// Pass file paths to run a subset: npm test -- test/money.test.js
import { spawnSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';

mkdirSync('.cache', { recursive: true });
const targets = process.argv.length > 2 ? process.argv.slice(2) : ['test/**/*.test.js'];
const result = spawnSync(
  process.execPath,
  [
    '--test',
    '--test-reporter=spec',
    '--test-reporter-destination=stdout',
    '--test-reporter=junit',
    '--test-reporter-destination=.cache/junit.xml',
    ...targets,
  ],
  { stdio: 'inherit' },
);
process.exit(result.status ?? 1);
