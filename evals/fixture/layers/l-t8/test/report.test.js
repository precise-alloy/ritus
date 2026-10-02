import assert from 'node:assert/strict';
import { test } from 'node:test';
import { renderRefundReport, renderRefundsCsv } from '../src/report.js';

const REFUNDS = [
  { id: 'R-1004', at: '2026-09-02T08:30:00.000Z', fromId: 'alice', toId: 'bob', amountCents: 2000, feeCents: 20 },
  { id: 'R-1002', at: '2026-09-01T23:50:00.000Z', fromId: 'carol', toId: 'alice', amountCents: 500, feeCents: 0 },
];

test('the report lists each refund and totals them', () => {
  assert.equal(
    renderRefundReport('alice', REFUNDS),
    [
      'Refunds for alice',
      'R-1004  2026-09-02  alice <- bob  $20.00  fee $0.20',
      'R-1002  2026-09-01  carol <- alice  $5.00',
      '2 refunds, $25.00 back, $0.20 fees',
    ].join('\n'),
  );
});

test('one refund is counted in the singular', () => {
  assert.match(renderRefundReport('alice', [REFUNDS[1]]), /^1 refund, \$5\.00 back, \$0\.00 fees$/m);
});

test('an account without refunds says so', () => {
  assert.equal(renderRefundReport('dave', []), 'No refunds for dave');
});

test('the csv has a header, then one row per refund with plain decimal amounts', () => {
  assert.equal(
    renderRefundsCsv(REFUNDS),
    [
      'id,date,back_to,from,amount,fee',
      'R-1004,2026-09-02,alice,bob,20.00,0.20',
      'R-1002,2026-09-01,carol,alice,5.00,0.00',
    ].join('\n'),
  );
});

test('csv fields holding a comma or a quote are quoted, quotes doubled', () => {
  const refund = { ...REFUNDS[1], fromId: 'acme, inc', toId: 'the "shop"' };
  assert.equal(renderRefundsCsv([refund]).split('\n')[1], 'R-1002,2026-09-01,"acme, inc","the ""shop""",5.00,0.00');
});

test('the csv without refunds is the header alone', () => {
  assert.equal(renderRefundsCsv([]), 'id,date,back_to,from,amount,fee');
});
