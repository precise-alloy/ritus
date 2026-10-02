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

test('refund prints what went back to the sender', async () => {
  const { path, cleanup } = await tempLedger();
  try {
    assert.deepEqual(await main(['refund', 'alice', 'bob', '20.00'], { ledgerPath: path }), {
      code: 0,
      output: 'Refund R-1001: $20.00 back to alice',
    });
    assert.deepEqual(await main(['refund', 'alice', 'bob', '10.50', '--fee'], { ledgerPath: path }), {
      code: 0,
      output: 'Refund R-1002: $10.50 and $0.11 fee back to alice',
    });
  } finally {
    await cleanup();
  }
});

test('refund above the limit prints the error and exits 1', async () => {
  const { path, cleanup } = await tempLedger({ alice: 0, bob: 100000 });
  try {
    assert.deepEqual(await main(['refund', 'alice', 'bob', '600.00'], { ledgerPath: path }), {
      code: 1,
      output: 'Error: Refunds above $500.00 need a second approver (TL-31)',
    });
  } finally {
    await cleanup();
  }
});

test('refund rejects an option it does not know and moves nothing', async () => {
  const { ledger, path, cleanup } = await tempLedger();
  try {
    assert.deepEqual(await main(['refund', 'alice', 'bob', '10.50', '--fees'], { ledgerPath: path }), {
      code: 1,
      output: 'Error: Unknown option --fees',
    });
    assert.equal(await ledger.getBalance('alice'), 10000);
    assert.equal(await ledger.getBalance('bob'), 5000);
  } finally {
    await cleanup();
  }
});
