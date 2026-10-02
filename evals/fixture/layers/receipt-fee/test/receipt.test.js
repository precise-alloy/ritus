import assert from 'node:assert/strict';
import { test } from 'node:test';
import { renderReceipt } from '../src/receipt.js';

const RECEIPT = { id: 'R-1001', fromId: 'alice', toId: 'bob', amountCents: 1250, feeCents: 13 };

test('receipt lists id, parties, amount, fee, and total', () => {
  assert.equal(
    renderReceipt(RECEIPT),
    ['Receipt R-1001', 'From: alice', 'To: bob', 'Amount: $12.50', 'Fee: $0.13', 'Total: $12.63'].join('\n'),
  );
});

test('receipt shows a zero fee explicitly', () => {
  const text = renderReceipt({ ...RECEIPT, feeCents: 0 });
  assert.match(text, /^Fee: \$0\.00$/m);
  assert.match(text, /^Total: \$12\.50$/m);
});

test('receipt renders every amount in the requested currency', () => {
  const text = renderReceipt(RECEIPT, 'EUR');
  assert.match(text, /^Amount: €12\.50$/m);
  assert.match(text, /^Fee: €0\.13$/m);
  assert.match(text, /^Total: €12\.63$/m);
});
