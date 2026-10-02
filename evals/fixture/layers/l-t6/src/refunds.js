// Refunds the account took part in - as the account the money went back to (fromId) or the one it came from
// (toId) - newest first. Each is { id, at, fromId, toId, amountCents, feeCents }.
export async function listRefunds(ledger, { accountId }) {
  await ledger.getBalance(accountId); // throws AccountNotFoundError for an unknown account
  const movements = await ledger.movements();
  return movements
    .filter(({ kind, memo }) => kind === 'refund' && (memo.fromId === accountId || memo.toId === accountId))
    .map(({ id, at, memo }) => ({ id, at, ...memo }))
    .reverse();
}
