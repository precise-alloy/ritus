import assert from 'node:assert/strict';
import { test } from 'node:test';
import { AccountNotFoundError } from '../src/errors.js';
import { refund } from '../src/refund.js';
import { listRefunds } from '../src/refunds.js';
import { transfer } from '../src/transfer.js';
import { withdraw } from '../src/withdraw.js';
import { tempLedger } from './helpers.js';

const AT = '2026-09-01T10:00:00.000Z';
const clock = () => new Date(AT);

test('lists the refunds an account took part in, on either side, newest first', async () => {
  const { ledger, cleanup } = await tempLedger({ alice: 10000, bob: 5000, carol: 5000 }, { now: clock });
  try {
    await refund(ledger, 'alice', 'bob', 1050, { refundFee: true });
    await refund(ledger, 'carol', 'alice', 500);
    await refund(ledger, 'carol', 'bob', 700);
    assert.deepEqual(await listRefunds(ledger, { accountId: 'alice' }), [
      { id: 'R-1002', at: AT, fromId: 'carol', toId: 'alice', amountCents: 500, feeCents: 0 },
      { id: 'R-1001', at: AT, fromId: 'alice', toId: 'bob', amountCents: 1050, feeCents: 11 },
    ]);
    assert.deepEqual((await listRefunds(ledger, { accountId: 'bob' })).map((r) => r.id), ['R-1003', 'R-1001']);
  } finally {
    await cleanup();
  }
});

test('transfers and withdrawals are not refunds', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    await transfer(ledger, 'alice', 'bob', 2000);
    await withdraw(ledger, 'alice', 1000);
    assert.deepEqual(await listRefunds(ledger, { accountId: 'alice' }), []);
  } finally {
    await cleanup();
  }
});

test('an unknown account is refused', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    await assert.rejects(listRefunds(ledger, { accountId: 'dave' }), AccountNotFoundError);
  } finally {
    await cleanup();
  }
});
