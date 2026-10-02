import { formatAmount } from './money.js';

// The `tl refunds` report: a title, one line per refund in the order given (listRefunds gives newest first), and a
// totals line.
export function renderRefundReport(accountId, refunds) {
  if (refunds.length === 0) {
    return `No refunds for ${accountId}`;
  }
  const lines = [`Refunds for ${accountId}`];
  for (const r of refunds) {
    const fee = r.feeCents > 0 ? `  fee ${formatAmount(r.feeCents)}` : '';
    lines.push(`${r.id}  ${r.at.slice(0, 10)}  ${r.fromId} <- ${r.toId}  ${formatAmount(r.amountCents)}${fee}`);
  }
  const back = refunds.reduce((sum, r) => sum + r.amountCents, 0);
  const fees = refunds.reduce((sum, r) => sum + r.feeCents, 0);
  const count = refunds.length === 1 ? '1 refund' : `${refunds.length} refunds`;
  lines.push(`${count}, ${formatAmount(back)} back, ${formatAmount(fees)} fees`);
  return lines.join('\n');
}

const CSV_HEADER = 'id,date,back_to,from,amount,fee';

// CSV for finance's spreadsheets: amounts as plain decimals (10.50) so they read as numbers.
export function renderRefundsCsv(refunds) {
  const rows = refunds.map((r) =>
    [r.id, r.at.slice(0, 10), r.fromId, r.toId, decimal(r.amountCents), decimal(r.feeCents)].map(csvField).join(','),
  );
  return [CSV_HEADER, ...rows].join('\n');
}

function decimal(cents) {
  return `${Math.floor(cents / 100)}.${String(cents % 100).padStart(2, '0')}`;
}

// RFC 4180: a field holding a comma, a double quote or a line break is quoted, and its quotes are doubled.
function csvField(value) {
  const text = String(value);
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}
