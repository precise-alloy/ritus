import { computeFee } from './fees.js';
import { parseAmount } from './money.js';

// The fee a transfer or a withdrawal of a typed amount would cost. Reads no balance and changes none.
export function previewFee(amount, kind) {
  return computeFee(parseAmount(amount), kind);
}
