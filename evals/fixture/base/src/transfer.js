import { computeFee } from './fees.js';
import { FEES_ACCOUNT } from './ledger.js';

// Move amountCents from one account to another. The sender also pays the transfer fee.
export async function transfer(ledger, fromId, toId, amountCents) {
  if (fromId === toId) {
    throw new RangeError('Cannot transfer to the same account');
  }
  const feeCents = computeFee(amountCents, 'transfer');
  const entries = [
    { accountId: fromId, deltaCents: -(amountCents + feeCents) },
    { accountId: toId, deltaCents: amountCents },
  ];
  if (feeCents > 0) {
    entries.push({ accountId: FEES_ACCOUNT, deltaCents: feeCents });
  }
  const { receiptNumber } = await ledger.apply(entries);
  return { id: `R-${receiptNumber}`, fromId, toId, amountCents, feeCents };
}
