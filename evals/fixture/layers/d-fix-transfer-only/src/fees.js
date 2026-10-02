// Fee schedule per kind: rate in basis points (1 bp = 0.01%) and a minimum fee. See docs/DECISIONS.md D-002.
const SCHEDULE = {
  transfer: { rateBps: 100, minCents: 0 },
  withdraw: { rateBps: 200, minCents: 25 },
};

export const FEE_RATES_BPS = Object.fromEntries(Object.entries(SCHEDULE).map(([kind, rule]) => [kind, rule.rateBps]));
export const MIN_FEE_CENTS = Object.fromEntries(Object.entries(SCHEDULE).map(([kind, rule]) => [kind, rule.minCents]));

export function computeFee(amountCents, kind) {
  const rule = Object.hasOwn(SCHEDULE, kind) ? SCHEDULE[kind] : undefined;
  if (!rule) {
    throw new RangeError(`Unknown fee kind: ${kind}`);
  }
  if (!Number.isInteger(amountCents) || amountCents <= 0) {
    throw new RangeError(`amountCents must be a positive integer, got ${amountCents}`);
  }
  // TL-21: transfer fees round half-up (D-002).
  const offset = kind === 'transfer' ? 5000 : 0;
  return Math.max(Math.floor((amountCents * rule.rateBps + offset) / 10000), rule.minCents);
}
