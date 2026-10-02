import assert from 'node:assert/strict';
import { test } from 'node:test';
import { AccountNotFoundError, InsufficientFundsError } from '../src/errors.js';
import { FEES_ACCOUNT } from '../src/ledger.js';
import { tempLedger } from './helpers.js';

test('a new ledger has the given balances and an empty fees account', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    assert.equal(await ledger.getBalance('alice'), 10000);
    assert.equal(await ledger.getBalance('bob'), 5000);
    assert.equal(await ledger.getBalance(FEES_ACCOUNT), 0);
  } finally {
    await cleanup();
  }
});

test('apply moves money and numbers receipts', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    const first = await ledger.apply([
      { accountId: 'alice', deltaCents: -300 },
      { accountId: 'bob', deltaCents: 300 },
    ]);
    assert.deepEqual(first, { receiptNumber: 1001, balances: { alice: 9700, bob: 5300 } });
    const second = await ledger.apply([{ accountId: 'bob', deltaCents: -1 }, { accountId: 'alice', deltaCents: 1 }]);
    assert.equal(second.receiptNumber, 1002);
  } finally {
    await cleanup();
  }
});

test('apply changes nothing when an account would go negative', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    await assert.rejects(
      ledger.apply([
        { accountId: 'bob', deltaCents: -6000 },
        { accountId: 'alice', deltaCents: 6000 },
      ]),
      InsufficientFundsError,
    );
    assert.equal(await ledger.getBalance('alice'), 10000);
    assert.equal(await ledger.getBalance('bob'), 5000);
  } finally {
    await cleanup();
  }
});

test('unknown accounts are rejected', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    await assert.rejects(ledger.getBalance('carol'), AccountNotFoundError);
    await assert.rejects(ledger.apply([{ accountId: 'carol', deltaCents: 1 }]), AccountNotFoundError);
  } finally {
    await cleanup();
  }
});

test('concurrent operations do not lose writes', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    await Promise.all(
      Array.from({ length: 10 }, () =>
        ledger.apply([
          { accountId: 'alice', deltaCents: -100 },
          { accountId: 'bob', deltaCents: 100 },
        ]),
      ),
    );
    assert.equal(await ledger.getBalance('alice'), 9000);
    assert.equal(await ledger.getBalance('bob'), 6000);
  } finally {
    await cleanup();
  }
});
