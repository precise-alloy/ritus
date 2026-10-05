import test from 'node:test';
import assert from 'node:assert/strict';
import accounts from '../data/accounts.json' with { type: 'json' };
import { totalBalance } from '../src/lib/accounts.js';
import { formatAmount } from '../src/lib/money.js';

test('formatAmount renders zero cents', () => {
  assert.equal(formatAmount(0), '$0.00');
});

test('formatAmount renders cents under one dollar', () => {
  assert.equal(formatAmount(5), '$0.05');
});

test('formatAmount renders grouped dollars', () => {
  assert.equal(formatAmount(1234567), '$12,345.67');
});

test('formatAmount renders negative cents', () => {
  assert.equal(formatAmount(-8450), '-$84.50');
});

test('totalBalance sums the seed balances', () => {
  assert.equal(totalBalance(accounts), 1234567);
});
