import assert from 'node:assert/strict';
import { test } from 'node:test';
import { main } from '../src/cli.js';
import { tempLedger } from './helpers.js';

test('balance prints the formatted balance', async () => {
  const { path, cleanup } = await tempLedger();
  try {
    assert.deepEqual(await main(['balance', 'alice'], { ledgerPath: path }), { code: 0, output: '$100.00' });
  } finally {
    await cleanup();
  }
});

test('transfer prints the receipt', async () => {
  const { path, cleanup } = await tempLedger();
  try {
    const { code, output } = await main(['transfer', 'alice', 'bob', '2000'], { ledgerPath: path });
    assert.equal(code, 0);
    assert.match(output, /^Receipt R-1001$/m);
    assert.match(output, /^Amount: \$20\.00$/m);
  } finally {
    await cleanup();
  }
});

test('errors are printed and exit 1', async () => {
  const { path, cleanup } = await tempLedger();
  try {
    assert.deepEqual(await main(['balance', 'carol'], { ledgerPath: path }), {
      code: 1,
      output: 'Error: Account carol not found',
    });
  } finally {
    await cleanup();
  }
});

test('an unknown command prints usage', async () => {
  const { code, output } = await main(['frobnicate']);
  assert.equal(code, 1);
  assert.match(output, /^Usage:/);
});
