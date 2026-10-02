import { formatAmount } from './money.js';

export function renderReceipt(receipt, currency = 'USD') {
  return [
    `Receipt ${receipt.id}`,
    `From: ${receipt.fromId}`,
    `To: ${receipt.toId}`,
    `Amount: ${formatAmount(receipt.amountCents, currency)}`,
  ].join('\n');
}

export function renderRefundReceipt(refund, currency = 'USD') {
  const lines = [
    `Refund ${refund.id}`,
    `Back to: ${refund.fromId}`,
    `From: ${refund.toId}`,
    `Amount: ${formatAmount(refund.amountCents, currency)}`,
  ];
  if (refund.feeCents > 0) {
    lines.push(`Fee returned: ${formatAmount(refund.feeCents, currency)}`);
  }
  return lines.join('\n');
}
