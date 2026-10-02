import assert from 'node:assert/strict';
import { test } from 'node:test';
import { renderReceipt } from '../src/receipt.js';

const RECEIPT = { id: 'R-1001', fromId: 'alice', toId: 'bob', amountCents: 1250, feeCents: 13 };

test('receipt lists id, parties, and amount', () => {
  assert.equal(renderReceipt(RECEIPT), ['Receipt R-1001', 'From: alice', 'To: bob', 'Amount: $12.50'].join('\n'));
});

test('receipt renders the requested currency', () => {
  assert.match(renderReceipt(RECEIPT, 'EUR'), /^Amount: €12\.50$/m);
});
