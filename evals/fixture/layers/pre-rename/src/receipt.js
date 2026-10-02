import { formatCents } from './money.js';

export function renderReceipt(receipt) {
  return [
    `Receipt ${receipt.id}`,
    `From: ${receipt.fromId}`,
    `To: ${receipt.toId}`,
    `Amount: ${formatCents(receipt.amountCents)}`,
  ].join('\n');
}
