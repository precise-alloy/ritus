import assert from 'node:assert/strict';
import { test } from 'node:test';
import { computeFee } from '../src/fees.js';

test('transfer fee is 1% of the amount', () => {
  assert.equal(computeFee(10000, 'transfer'), 100);
  assert.equal(computeFee(250000, 'transfer'), 2500);
});

test('withdraw fee is 2% with a 25 cent minimum', () => {
  assert.equal(computeFee(10000, 'withdraw'), 200);
  assert.equal(computeFee(500, 'withdraw'), 25);
});

test('computeFee rejects unknown kinds and non-positive amounts', () => {
  assert.throws(() => computeFee(100, 'refund'), RangeError);
  assert.throws(() => computeFee(0, 'transfer'), RangeError);
  assert.throws(() => computeFee(-100, 'transfer'), RangeError);
  assert.throws(() => computeFee(10.5, 'transfer'), RangeError);
});
