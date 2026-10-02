import assert from 'node:assert/strict';
import { test } from 'node:test';
import { InsufficientFundsError } from '../src/errors.js';
import { FEES_ACCOUNT } from '../src/ledger.js';
import { withdraw } from '../src/withdraw.js';
import { tempLedger } from './helpers.js';

test('withdraw takes the amount plus a 2% fee and resolves to the new balance', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    assert.equal(await withdraw(ledger, 'alice', 5000), 4900);
    assert.equal(await ledger.getBalance(FEES_ACCOUNT), 100);
  } finally {
    await cleanup();
  }
});

test('small withdrawals pay the 25 cent minimum fee', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    assert.equal(await withdraw(ledger, 'alice', 500), 9475);
    assert.equal(await ledger.getBalance(FEES_ACCOUNT), 25);
  } finally {
    await cleanup();
  }
});

test('withdraw fails without changes when the account cannot cover amount and fee', async () => {
  const { ledger, cleanup } = await tempLedger({ alice: 1000 });
  try {
    await assert.rejects(withdraw(ledger, 'alice', 1000), InsufficientFundsError);
    assert.equal(await ledger.getBalance('alice'), 1000);
    assert.equal(await ledger.getBalance(FEES_ACCOUNT), 0);
  } finally {
    await cleanup();
  }
});
