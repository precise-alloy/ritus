import assert from 'node:assert/strict';
import { writeFile } from 'node:fs/promises';
import { test } from 'node:test';
import { AccountNotFoundError, InsufficientFundsError } from '../src/errors.js';
import { FEES_ACCOUNT, Ledger } from '../src/ledger.js';
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

const AT = '2026-09-01T10:00:00.000Z';
const clock = () => new Date(AT);

test('apply records each movement with its receipt id, kind, memo and time', async () => {
  const { ledger, cleanup } = await tempLedger(undefined, { now: clock });
  try {
    const memo = { fromId: 'alice', toId: 'bob', amountCents: 300, feeCents: 0 };
    await ledger.apply(
      [
        { accountId: 'alice', deltaCents: -300 },
        { accountId: 'bob', deltaCents: 300 },
      ],
      { kind: 'transfer', memo },
    );
    await ledger.apply([{ accountId: 'bob', deltaCents: -100 }, { accountId: 'alice', deltaCents: 100 }]);
    assert.deepEqual(await ledger.movements(), [
      { id: 'R-1001', kind: 'transfer', at: AT, memo },
      { id: 'R-1002', kind: 'adjustment', at: AT, memo: {} },
    ]);
  } finally {
    await cleanup();
  }
});

test('a refused apply records nothing', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    await assert.rejects(
      ledger.apply(
        [
          { accountId: 'bob', deltaCents: -6000 },
          { accountId: 'alice', deltaCents: 6000 },
        ],
        { kind: 'transfer' },
      ),
      InsufficientFundsError,
    );
    assert.deepEqual(await ledger.movements(), []);
  } finally {
    await cleanup();
  }
});

test('a ledger file from before movements were recorded still loads and records', async () => {
  const { path, cleanup } = await tempLedger();
  try {
    const accounts = { alice: { id: 'alice', balanceCents: 500 }, fees: { id: 'fees', balanceCents: 0 } };
    await writeFile(path, JSON.stringify({ accounts, nextReceipt: 1001 }, null, 2));
    const ledger = new Ledger(path, { now: clock });
    assert.deepEqual(await ledger.movements(), []);
    await ledger.apply([{ accountId: 'alice', deltaCents: -25 }, { accountId: FEES_ACCOUNT, deltaCents: 25 }]);
    assert.deepEqual(await ledger.movements(), [{ id: 'R-1001', kind: 'adjustment', at: AT, memo: {} }]);
  } finally {
    await cleanup();
  }
});

test('without a clock, movements carry the system time', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    const before = Date.now();
    await ledger.apply([{ accountId: 'alice', deltaCents: -1 }, { accountId: 'bob', deltaCents: 1 }]);
    const [{ at }] = await ledger.movements();
    assert.ok(Date.parse(at) >= before && Date.parse(at) <= Date.now(), at);
  } finally {
    await cleanup();
  }
});
