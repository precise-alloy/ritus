import { computeFee } from './fees.js';
import { FEES_ACCOUNT } from './ledger.js';

// Refunds above $500.00 need a second approver, which TL-31 adds; until then they are refused.
export const REFUND_LIMIT_CENTS = 50000;

// Undo a mistaken transfer from fromId to toId: the amount goes back from toId to fromId, and with refundFee the
// transfer fee goes back to fromId from the fees account. One ledger.apply() call, so it is all or nothing.
export async function refund(ledger, fromId, toId, amountCents, { refundFee = false } = {}) {
  if (fromId === toId) {
    throw new RangeError('Cannot refund to the same account');
  }
  if (!Number.isInteger(amountCents) || amountCents <= 0) {
    throw new RangeError(`amountCents must be a positive integer, got ${amountCents}`);
  }
  if (amountCents >= REFUND_LIMIT_CENTS) {
    throw new RangeError('Refunds above $500.00 need a second approver (TL-31)');
  }
  const feeCents = refundFee ? computeFee(amountCents, 'transfer') : 0;
  const entries = [
    { accountId: toId, deltaCents: -amountCents },
    { accountId: fromId, deltaCents: amountCents + feeCents },
  ];
  if (feeCents > 0) {
    entries.push({ accountId: FEES_ACCOUNT, deltaCents: -feeCents });
  }
  const { receiptNumber } = await ledger.apply(entries);
  return { id: `R-${receiptNumber}`, fromId, toId, amountCents, feeCents };
}
