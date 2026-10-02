import { formatAmount } from './money.js';

// Renders balance rows for the CLI. csv and json are ready for finance's spreadsheets.
export class BalanceFormatter {
  static FORMATS = ['text', 'csv', 'json'];

  constructor(format = 'text') {
    if (!BalanceFormatter.FORMATS.includes(format)) {
      throw new RangeError(`Unknown format: ${format}`);
    }
    this.format = this.format.bind(this);
    this.kind = format;
  }

  format(rows) {
    if (this.kind === 'csv') {
      return ['account,balance_cents', ...rows.map((r) => `${r.accountId},${r.balanceCents}`)].join('\n');
    }
    if (this.kind === 'json') {
      return JSON.stringify(rows.map((r) => ({ account: r.accountId, balance: formatAmount(r.balanceCents) })));
    }
    return rows.map((r) => `${r.accountId} ${formatAmount(r.balanceCents)}`).join('\n');
  }
}
