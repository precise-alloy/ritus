import { formatAmount } from './money.js';

export function renderReceipt(receipt, currency = 'USD') {
  return [
    `Receipt ${receipt.id}`,
    `From: ${receipt.fromId}`,
    `To: ${receipt.toId}`,
    `Amount: ${formatAmount(receipt.amountCents, currency)}`,
    `Fee: ${formatAmount(receipt.feeCents, currency)}`,
    `Total: ${formatAmount(receipt.amountCents + receipt.feeCents, currency)}`,
  ].join('\n');
}
