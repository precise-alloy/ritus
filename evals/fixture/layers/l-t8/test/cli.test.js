import assert from 'node:assert/strict';
import { test } from 'node:test';
import { main } from '../src/cli.js';
import { refund } from '../src/refund.js';
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

test('refund prints the refund receipt', async () => {
  const { path, cleanup } = await tempLedger();
  try {
    const { code, output } = await main(['refund', 'alice', 'bob', '10.50', '--fee'], { ledgerPath: path });
    assert.equal(code, 0);
    assert.equal(output, 'Refund R-1001\nBack to: alice\nFrom: bob\nAmount: $10.50\nFee returned: $0.11');
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

// alice gets $10.50 back from bob with the fee, then $5.00 from carol.
async function ledgerWithRefunds() {
  const clock = () => new Date('2026-09-01T10:00:00.000Z');
  const temp = await tempLedger({ alice: 10000, bob: 5000, carol: 5000 }, { now: clock });
  await refund(temp.ledger, 'alice', 'bob', 1050, { refundFee: true });
  await refund(temp.ledger, 'alice', 'carol', 500);
  return temp;
}

test('refunds prints the account report', async () => {
  const { path, cleanup } = await ledgerWithRefunds();
  try {
    const { code, output } = await main(['refunds', 'alice'], { ledgerPath: path });
    assert.equal(code, 0);
    assert.equal(
      output,
      [
        'Refunds for alice',
        'R-1002  2026-09-01  alice <- carol  $5.00',
        'R-1001  2026-09-01  alice <- bob  $10.50  fee $0.11',
        '2 refunds, $15.50 back, $0.11 fees',
      ].join('\n'),
    );
  } finally {
    await cleanup();
  }
});

test('refunds for an account without any says so', async () => {
  const { path, cleanup } = await tempLedger();
  try {
    assert.deepEqual(await main(['refunds', 'bob'], { ledgerPath: path }), { code: 0, output: 'No refunds for bob' });
  } finally {
    await cleanup();
  }
});

test('refunds --csv prints the csv', async () => {
  const { path, cleanup } = await ledgerWithRefunds();
  try {
    const { code, output } = await main(['refunds', 'alice', '--csv'], { ledgerPath: path });
    assert.equal(code, 0);
    assert.equal(
      output,
      [
        'id,date,back_to,from,amount,fee',
        'R-1002,2026-09-01,alice,carol,5.00,0.00',
        'R-1001,2026-09-01,alice,bob,10.50,0.11',
      ].join('\n'),
    );
  } finally {
    await cleanup();
  }
});
