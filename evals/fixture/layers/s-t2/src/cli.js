#!/usr/bin/env node
import { pathToFileURL } from 'node:url';
import { Ledger } from './ledger.js';
import { formatAmount, parseAmount } from './money.js';
import { renderReceipt } from './receipt.js';
import { refund as applyRefund } from './refund.js';
import { transfer } from './transfer.js';
import { withdraw } from './withdraw.js';

const USAGE = `Usage:
  tl balance <account>
  tl transfer <from> <to> <amount>
  tl withdraw <account> <amount>
  tl refund <from> <to> <amount> [--fee]`;

// Each command resolves to the text to print. main() turns errors into `Error: <message>` and exit code 1.
export const commands = {
  async balance(ledger, [accountId]) {
    return formatAmount(await ledger.getBalance(accountId));
  },
  async transfer(ledger, [fromId, toId, amount]) {
    const receipt = await transfer(ledger, fromId, toId, parseAmount(amount));
    return renderReceipt(receipt);
  },
  async withdraw(ledger, [accountId, amount]) {
    return formatAmount(await withdraw(ledger, accountId, parseAmount(amount)));
  },
  async refund(ledger, [fromId, toId, amount, flag]) {
    const receipt = await applyRefund(ledger, fromId, toId, parseAmount(amount), { refundFee: flag === '--fee' });
    const fee = receipt.feeCents > 0 ? ` and ${formatAmount(receipt.feeCents)} fee` : '';
    return `Refund ${receipt.id}: ${formatAmount(receipt.amountCents)}${fee} back to ${receipt.fromId}`;
  },
};

export async function main(argv, { ledgerPath = process.env.TL_LEDGER ?? 'ledger.json' } = {}) {
  const [name, ...args] = argv;
  const command = Object.hasOwn(commands, name) ? commands[name] : undefined;
  if (!command) {
    return { code: 1, output: USAGE };
  }
  try {
    return { code: 0, output: await command(new Ledger(ledgerPath), args) };
  } catch (error) {
    return { code: 1, output: `Error: ${error.message}` };
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const { code, output } = await main(process.argv.slice(2));
  console.log(output);
  process.exitCode = code;
}
