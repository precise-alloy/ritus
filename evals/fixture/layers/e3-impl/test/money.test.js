import assert from 'node:assert/strict';
import { test } from 'node:test';
import { InvalidAmountError } from '../src/errors.js';
import { formatAmount, parseAmount } from '../src/money.js';

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

test('parseAmount reads dollars and cents', () => {
  assert.equal(parseAmount('12.34'), 1234);
  assert.equal(parseAmount('0.5'), 50);
  assert.equal(parseAmount('7'), 700);
});

test('parseAmount accepts thousands separators and surrounding spaces', () => {
  assert.equal(parseAmount('1,234.50'), 123450);
  assert.equal(parseAmount(' 7 '), 700);
});

test('parseAmount refuses text that is not an amount', () => {
  for (const input of ['abc', '', '   ', '-5', '1.234', '1,23', '12.']) {
    assert.throws(() => parseAmount(input), InvalidAmountError, input);
  }
});

test('parseAmount refuses non-text and amounts too large to count in cents', () => {
  assert.throws(() => parseAmount(12), InvalidAmountError);
  assert.throws(() => parseAmount('90071992547410'), InvalidAmountError);
});
