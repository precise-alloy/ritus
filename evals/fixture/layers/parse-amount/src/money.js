import { InvalidAmountError } from './errors.js';

const SYMBOLS = { USD: '$', EUR: '€', GBP: '£' };
const AMOUNT_PATTERN = /^(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?$/;

// Amounts are integer cents everywhere; convert to text only at the edges (docs/DECISIONS.md D-001).
export function formatAmount(cents, currency = 'USD') {
  if (!Number.isInteger(cents)) {
    throw new TypeError(`cents must be an integer, got ${cents}`);
  }
  const symbol = Object.hasOwn(SYMBOLS, currency) ? SYMBOLS[currency] : undefined;
  if (!symbol) {
    throw new RangeError(`Unsupported currency: ${currency}`);
  }
  const sign = cents < 0 ? '-' : '';
  const abs = Math.abs(cents);
  const units = Math.floor(abs / 100).toLocaleString('en-US');
  const fraction = String(abs % 100).padStart(2, '0');
  return `${sign}${symbol}${units}.${fraction}`;
}

// Parse an amount typed by support staff ("12.34", "1,234.50", " 7 ") into integer cents. Only amounts greater than
// zero are valid.
export function parseAmount(input) {
  if (typeof input !== 'string') {
    throw new InvalidAmountError(input, 'expected text');
  }
  const match = AMOUNT_PATTERN.exec(input.trim());
  if (!match) {
    throw new InvalidAmountError(input, 'expected an amount like 12.34');
  }
  const [, units, fraction = ''] = match;
  const cents = Number(units.replaceAll(',', '')) * 100 + Number(fraction.padEnd(2, '0'));
  if (!Number.isSafeInteger(cents)) {
    throw new InvalidAmountError(input, 'amount is too large');
  }
  if (cents === 0) {
    throw new InvalidAmountError(input, 'amount must be greater than zero');
  }
  return cents;
}
