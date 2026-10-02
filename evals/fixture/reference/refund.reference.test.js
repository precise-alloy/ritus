import assert from 'node:assert/strict';
import { test } from 'node:test';
import { InsufficientFundsError } from '../src/errors.js';
import { FEES_ACCOUNT } from '../src/ledger.js';
import { refund } from '../src/refund.js';
import { transfer } from '../src/transfer.js';
import { tempLedger } from './helpers.js';

async function balances(ledger) {
  return {
    alice: await ledger.getBalance('alice'),
    bob: await ledger.getBalance('bob'),
    fees: await ledger.getBalance(FEES_ACCOUNT),
  };
}

test('ref: amount goes back, fees untouched, receipt', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    const receipt = await refund(ledger, 'alice', 'bob', 2000);
    assert.deepEqual(receipt, { id: 'R-1001', fromId: 'alice', toId: 'bob', amountCents: 2000, feeCents: 0 });
    assert.deepEqual(await balances(ledger), { alice: 12000, bob: 3000, fees: 0 });
  } finally {
    await cleanup();
  }
});

test('ref: refundFee returns the transfer fee from the fees account', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    await transfer(ledger, 'alice', 'bob', 2000);
    const receipt = await refund(ledger, 'alice', 'bob', 2000, { refundFee: true });
    assert.deepEqual(receipt, { id: 'R-1002', fromId: 'alice', toId: 'bob', amountCents: 2000, feeCents: 20 });
    assert.deepEqual(await balances(ledger), { alice: 10000, bob: 5000, fees: 0 });
  } finally {
    await cleanup();
  }
});

test('ref: all or nothing when the recipient cannot cover the amount', async () => {
  const { ledger, cleanup } = await tempLedger({ alice: 0, bob: 1000 });
  try {
    await assert.rejects(refund(ledger, 'alice', 'bob', 2000, { refundFee: true }), InsufficientFundsError);
    assert.deepEqual(await balances(ledger), { alice: 0, bob: 1000, fees: 0 });
  } finally {
    await cleanup();
  }
});

test('ref: same account and bad amounts are refused', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    await assert.rejects(refund(ledger, 'alice', 'alice', 500), RangeError);
    for (const bad of [0, -500, 10.5]) {
      await assert.rejects(refund(ledger, 'alice', 'bob', bad), RangeError);
    }
    assert.deepEqual(await balances(ledger), { alice: 10000, bob: 5000, fees: 0 });
  } finally {
    await cleanup();
  }
});

test('ref: the refunded fee rounds half-up (D-002)', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    const receipt = await refund(ledger, 'alice', 'bob', 1050, { refundFee: true });
    assert.equal(receipt.feeCents, 11);
    assert.equal(await ledger.getBalance('alice'), 11061);
  } finally {
    await cleanup();
  }
});
