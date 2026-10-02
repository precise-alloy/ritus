// Amounts are integer cents everywhere; convert to text only at the edges (docs/DECISIONS.md D-001).
export function formatCents(cents) {
  if (!Number.isInteger(cents)) {
    throw new TypeError(`cents must be an integer, got ${cents}`);
  }
  const sign = cents < 0 ? '-' : '';
  const abs = Math.abs(cents);
  const units = Math.floor(abs / 100).toLocaleString('en-US');
  const fraction = String(abs % 100).padStart(2, '0');
  return `${sign}$${units}.${fraction}`;
}
