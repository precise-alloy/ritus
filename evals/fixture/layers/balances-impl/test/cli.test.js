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

test('transfer takes a typed amount and prints the receipt', async () => {
  const { path, cleanup } = await tempLedger();
  try {
    const { code, output } = await main(['transfer', 'alice', 'bob', '20.00'], { ledgerPath: path });
    assert.equal(code, 0);
    assert.match(output, /^Receipt R-1001$/m);
    assert.match(output, /^Amount: \$20\.00$/m);
  } finally {
    await cleanup();
  }
});

test('withdraw prints the new balance', async () => {
  const { path, cleanup } = await tempLedger();
  try {
    assert.deepEqual(await main(['withdraw', 'alice', '50.00'], { ledgerPath: path }), { code: 0, output: '$49.00' });
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
    const typo = await main(['transfer', 'alice', 'bob', '20,00'], { ledgerPath: path });
    assert.equal(typo.code, 1);
    assert.match(typo.output, /^Error: Invalid amount "20,00"/);
  } finally {
    await cleanup();
  }
});

test('an unknown command prints usage', async () => {
  const { code, output } = await main(['frobnicate']);
  assert.equal(code, 1);
  assert.match(output, /^Usage:/);
});

test('balances lists every account with its balance, sorted by account id', async () => {
  const { path, cleanup } = await tempLedger({ carol: 250, alice: 10000, bob: 5000 });
  try {
    assert.deepEqual(await main(['balances'], { ledgerPath: path }), {
      code: 0,
      output: 'alice $100.00\nbob $50.00\ncarol $2.50\nfees $0.00',
    });
  } finally {
    await cleanup();
  }
});
