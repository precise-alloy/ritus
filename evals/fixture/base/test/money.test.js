import assert from 'node:assert/strict';
import { test } from 'node:test';
import { formatAmount } from '../src/money.js';

test('formatAmount renders dollars and cents', () => {
  assert.equal(formatAmount(1234), '$12.34');
  assert.equal(formatAmount(5), '$0.05');
  assert.equal(formatAmount(0), '$0.00');
});

test('formatAmount groups thousands', () => {
  assert.equal(formatAmount(123456789), '$1,234,567.89');
});

test('formatAmount puts the sign before the symbol', () => {
  assert.equal(formatAmount(-50), '-$0.50');
});

test('formatAmount supports EUR and GBP', () => {
  assert.equal(formatAmount(1999, 'EUR'), '€19.99');
  assert.equal(formatAmount(1999, 'GBP'), '£19.99');
});

test('formatAmount rejects fractional cents and unknown currencies', () => {
  assert.throws(() => formatAmount(1.5), TypeError);
  assert.throws(() => formatAmount(100, 'JPY'), RangeError);
});
