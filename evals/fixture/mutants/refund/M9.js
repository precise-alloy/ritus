// Mutant M9: the refunded fee is taken from the recipient instead of the fees account
import { computeFee } from './fees.js';

// Undo a mistaken transfer from fromId to toId: the amount goes back from toId to fromId, and with refundFee the
// transfer fee goes back to fromId from the fees account. One ledger.apply() call, so it is all or nothing.
export async function refund(ledger, fromId, toId, amountCents, { refundFee = false } = {}) {
  if (fromId === toId) {
    throw new RangeError('Cannot refund to the same account');
  }
  if (!Number.isInteger(amountCents) || amountCents <= 0) {
    throw new RangeError(`amountCents must be a positive integer, got ${amountCents}`);
  }
  const feeCents = refundFee ? computeFee(amountCents, 'transfer') : 0;
  const entries = [
    { accountId: toId, deltaCents: -(amountCents + feeCents) },
    { accountId: fromId, deltaCents: amountCents + feeCents },
  ];
  const { receiptNumber } = await ledger.apply(entries);
  return { id: `R-${receiptNumber}`, fromId, toId, amountCents, feeCents };
}
