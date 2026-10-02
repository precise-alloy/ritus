import assert from 'node:assert/strict';
import { test } from 'node:test';
import { renderReceipt, renderRefundReceipt } from '../src/receipt.js';

const RECEIPT = { id: 'R-1001', fromId: 'alice', toId: 'bob', amountCents: 1250, feeCents: 13 };

test('receipt lists id, parties, and amount', () => {
  assert.equal(renderReceipt(RECEIPT), ['Receipt R-1001', 'From: alice', 'To: bob', 'Amount: $12.50'].join('\n'));
});

test('receipt renders the requested currency', () => {
  assert.match(renderReceipt(RECEIPT, 'EUR'), /^Amount: €12\.50$/m);
});

test('a refund receipt names who got the money back and any fee returned', () => {
  const r = { id: 'R-1002', fromId: 'alice', toId: 'bob', amountCents: 1050, feeCents: 11 };
  assert.equal(renderRefundReceipt(r), 'Refund R-1002\nBack to: alice\nFrom: bob\nAmount: $10.50\nFee returned: $0.11');
  assert.equal(renderRefundReceipt({ ...r, feeCents: 0 }), 'Refund R-1002\nBack to: alice\nFrom: bob\nAmount: $10.50');
  assert.equal(renderRefundReceipt(r, 'EUR'), 'Refund R-1002\nBack to: alice\nFrom: bob\nAmount: €10.50\nFee returned: €0.11');
});
