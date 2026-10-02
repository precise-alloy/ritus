import assert from 'node:assert/strict';
import { test } from 'node:test';
import { InvalidAmountError } from '../src/errors.js';
import { previewFee } from '../src/fee-preview.js';

test('previewFee charges the transfer fee on a typed amount', () => {
  assert.equal(previewFee('10.50', 'transfer'), 11);
});

test('previewFee applies the withdrawal rate and its minimum', () => {
  assert.equal(previewFee('50.25', 'withdraw'), 101);
  assert.equal(previewFee('5', 'withdraw'), 25);
});

test('previewFee refuses text that is not an amount', () => {
  assert.throws(() => previewFee('abc', 'transfer'), InvalidAmountError);
});
