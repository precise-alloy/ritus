import assert from 'node:assert/strict';
import { test } from 'node:test';
import { formatCents } from '../src/money.js';

test('formatCents renders dollars and cents', () => {
  assert.equal(formatCents(1234), '$12.34');
  assert.equal(formatCents(5), '$0.05');
  assert.equal(formatCents(0), '$0.00');
});

test('formatCents groups thousands', () => {
  assert.equal(formatCents(123456789), '$1,234,567.89');
});

test('formatCents puts the sign before the symbol', () => {
  assert.equal(formatCents(-50), '-$0.50');
});

test('formatCents rejects fractional cents', () => {
  assert.throws(() => formatCents(1.5), TypeError);
});
