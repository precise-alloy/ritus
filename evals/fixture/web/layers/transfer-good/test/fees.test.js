import test from 'node:test';
import assert from 'node:assert/strict';
import { transferFee } from '../src/lib/fees.js';

test('transferFee applies the minimum fee', () => {
  assert.equal(transferFee(1000), 25);
  assert.equal(transferFee(2549), 25);
});

test('transferFee rounds half up to the nearest cent', () => {
  assert.equal(transferFee(2550), 26);
  assert.equal(transferFee(100000), 1000);
});
