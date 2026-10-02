import { computeFee } from './fees.js';
import { FEES_ACCOUNT } from './ledger.js';

// Take amountCents out of an account; the account also pays the withdrawal fee. Resolves to the new balance.
export async function withdraw(ledger, accountId, amountCents) {
  const feeCents = computeFee(amountCents, 'withdraw');
  const entries = [
    { accountId, deltaCents: -(amountCents + feeCents) },
    { accountId: FEES_ACCOUNT, deltaCents: feeCents },
  ];
  const { balances } = await ledger.apply(entries, { kind: 'withdraw', memo: { accountId, amountCents, feeCents } });
  return balances[accountId];
}
