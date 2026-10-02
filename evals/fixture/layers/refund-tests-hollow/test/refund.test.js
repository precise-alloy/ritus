import assert from 'node:assert/strict';
import { test } from 'node:test';
import { InsufficientFundsError } from '../src/errors.js';
import { computeFee } from '../src/fees.js';
import { FEES_ACCOUNT } from '../src/ledger.js';
import { refund } from '../src/refund.js';
import { tempLedger } from './helpers.js';

test('refund moves the amount back from the recipient to the sender', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    const receipt = await refund(ledger, 'alice', 'bob', 2000);
    assert.equal(receipt.feeCents, 0);
    assert.equal(await ledger.getBalance('alice'), 12000);
    assert.equal(await ledger.getBalance('bob'), 3000);
    assert.equal(await ledger.getBalance(FEES_ACCOUNT), 0);
  } finally {
    await cleanup();
  }
});

test('refundFee also gives the sender the transfer fee back', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    const receipt = await refund(ledger, 'alice', 'bob', 2000, { refundFee: true });
    assert.equal(receipt.feeCents, computeFee(2000, 'transfer'));
    assert.equal(await ledger.getBalance('alice'), 10000 + 2000 + computeFee(2000, 'transfer'));
  } finally {
    await cleanup();
  }
});

test('refund is all or nothing', async () => {
  const { ledger, cleanup } = await tempLedger({ alice: 0, bob: 1000 });
  try {
    await assert.rejects(refund(ledger, 'alice', 'bob', 2000), InsufficientFundsError);
  } finally {
    await cleanup();
  }
});

test('refund makes a single ledger call and returns its receipt', async () => {
  const calls = [];
  const ledger = {
    async apply(entries) {
      calls.push(entries);
      return { receiptNumber: 1001, balances: {} };
    },
  };
  const receipt = await refund(ledger, 'alice', 'carol', 500);
  assert.ok(calls.length > 0);
  assert.equal(receipt.id, 'R-1001');
});

test('refund to the same account is refused', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    await assert.rejects(refund(ledger, 'alice', 'alice', 500), RangeError);
  } finally {
    await cleanup();
  }
});
