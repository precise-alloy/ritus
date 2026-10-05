export function transferFee(amountCents) {
  if (!Number.isInteger(amountCents) || amountCents <= 0) {
    throw new RangeError(`amountCents must be a positive integer, got ${amountCents}`);
  }
  return Math.max(Math.floor((amountCents + 50) / 100), 25);
}
