export function formatAmount(cents) {
  const sign = cents < 0 ? '-' : '';
  const absolute = Math.abs(cents);
  const dollars = Math.floor(absolute / 100).toLocaleString('en-US');
  const remainder = String(absolute % 100).padStart(2, '0');
  return `${sign}$${dollars}.${remainder}`;
}
