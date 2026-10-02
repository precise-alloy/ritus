import assert from 'node:assert/strict';
import { test } from 'node:test';
import { InsufficientFundsError } from '../src/errors.js';
import { FEES_ACCOUNT } from '../src/ledger.js';
import { transfer } from '../src/transfer.js';
import { tempLedger } from './helpers.js';

test('transfer moves the amount and charges the sender the fee', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    const receipt = await transfer(ledger, 'alice', 'bob', 2000);
    assert.deepEqual(receipt, { id: 'R-1001', fromId: 'alice', toId: 'bob', amountCents: 2000, feeCents: 20 });
    assert.equal(await ledger.getBalance('alice'), 7980);
    assert.equal(await ledger.getBalance('bob'), 7000);
    assert.equal(await ledger.getBalance(FEES_ACCOUNT), 20);
  } finally {
    await cleanup();
  }
});

test('transfer fails without changes when the sender cannot cover amount and fee', async () => {
  const { ledger, cleanup } = await tempLedger({ alice: 1000, bob: 0 });
  try {
    await assert.rejects(transfer(ledger, 'alice', 'bob', 1000), InsufficientFundsError);
    assert.equal(await ledger.getBalance('alice'), 1000);
    assert.equal(await ledger.getBalance('bob'), 0);
  } finally {
    await cleanup();
  }
});

test('transfer to the same account is refused', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    await assert.rejects(transfer(ledger, 'alice', 'alice', 100), RangeError);
  } finally {
    await cleanup();
  }
});

test('transfer records its movement', async () => {
  const { ledger, cleanup } = await tempLedger(undefined, { now: () => new Date('2026-09-01T10:00:00.000Z') });
  try {
    await transfer(ledger, 'alice', 'bob', 2000);
    assert.deepEqual(await ledger.movements(), [
      {
        id: 'R-1001',
        kind: 'transfer',
        at: '2026-09-01T10:00:00.000Z',
        memo: { fromId: 'alice', toId: 'bob', amountCents: 2000, feeCents: 20 },
      },
    ]);
  } finally {
    await cleanup();
  }
});
