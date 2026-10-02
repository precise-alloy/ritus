import assert from 'node:assert/strict';
import { test } from 'node:test';
import { InsufficientFundsError } from '../src/errors.js';
import { FEES_ACCOUNT } from '../src/ledger.js';
import { refund } from '../src/refund.js';
import { transfer } from '../src/transfer.js';
import { tempLedger } from './helpers.js';

test('refund moves the amount back to the sender and leaves the fees account alone', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    const receipt = await refund(ledger, 'alice', 'bob', 2000);
    assert.deepEqual(receipt, { id: 'R-1001', fromId: 'alice', toId: 'bob', amountCents: 2000, feeCents: 0 });
    assert.equal(await ledger.getBalance('alice'), 12000);
    assert.equal(await ledger.getBalance('bob'), 3000);
    assert.equal(await ledger.getBalance(FEES_ACCOUNT), 0);
  } finally {
    await cleanup();
  }
});

test('refundFee gives the transfer fee back from the fees account', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    await transfer(ledger, 'alice', 'bob', 2000);
    const receipt = await refund(ledger, 'alice', 'bob', 2000, { refundFee: true });
    assert.deepEqual(receipt, { id: 'R-1002', fromId: 'alice', toId: 'bob', amountCents: 2000, feeCents: 20 });
    assert.equal(await ledger.getBalance('alice'), 10000);
    assert.equal(await ledger.getBalance('bob'), 5000);
    assert.equal(await ledger.getBalance(FEES_ACCOUNT), 0);
  } finally {
    await cleanup();
  }
});

test('the refunded fee rounds half-up like every fee (D-002)', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    const receipt = await refund(ledger, 'alice', 'bob', 1050, { refundFee: true });
    assert.equal(receipt.feeCents, 11);
    assert.equal(await ledger.getBalance('alice'), 11061);
  } finally {
    await cleanup();
  }
});

test('refund changes nothing when the recipient cannot cover the amount', async () => {
  const { ledger, cleanup } = await tempLedger({ alice: 0, bob: 1000 });
  try {
    await assert.rejects(refund(ledger, 'alice', 'bob', 2000, { refundFee: true }), InsufficientFundsError);
    assert.equal(await ledger.getBalance('alice'), 0);
    assert.equal(await ledger.getBalance('bob'), 1000);
    assert.equal(await ledger.getBalance(FEES_ACCOUNT), 0);
  } finally {
    await cleanup();
  }
});

test('refund refuses the same account and amounts that are not positive whole cents', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    await assert.rejects(refund(ledger, 'alice', 'alice', 500), RangeError);
    await assert.rejects(refund(ledger, 'alice', 'bob', 0), RangeError);
    await assert.rejects(refund(ledger, 'alice', 'bob', -500), RangeError);
    await assert.rejects(refund(ledger, 'alice', 'bob', 10.5), RangeError);
    assert.equal(await ledger.getBalance('alice'), 10000);
    assert.equal(await ledger.getBalance('bob'), 5000);
  } finally {
    await cleanup();
  }
});

test('large refunds need a second approver', async () => {
  const { ledger, cleanup } = await tempLedger({ alice: 0, bob: 100000 });
  try {
    await assert.rejects(refund(ledger, 'alice', 'bob', 60000), /second approver/);
    await refund(ledger, 'alice', 'bob', 20000);
    assert.equal(await ledger.getBalance('alice'), 20000);
    assert.equal(await ledger.getBalance('bob'), 80000);
  } finally {
    await cleanup();
  }
});
