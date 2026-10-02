// Fee schedule in basis points (1 bp = 0.01%). Fees round half-up to the cent (docs/DECISIONS.md D-002).
export const FEE_RATES_BPS = { transfer: 100, withdraw: 200 };
export const MIN_FEE_CENTS = { transfer: 0, withdraw: 25 };

export function computeFee(amountCents, kind) {
  if (!Object.hasOwn(FEE_RATES_BPS, kind)) {
    throw new RangeError(`Unknown fee kind: ${kind}`);
  }
  if (!Number.isInteger(amountCents) || amountCents <= 0) {
    throw new RangeError(`amountCents must be a positive integer, got ${amountCents}`);
  }
  const fee = Math.floor((amountCents * FEE_RATES_BPS[kind] + 5000) / 10000);
  return Math.max(fee, MIN_FEE_CENTS[kind]);
}
