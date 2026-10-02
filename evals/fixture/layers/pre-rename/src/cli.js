#!/usr/bin/env node
import { pathToFileURL } from 'node:url';
import { Ledger } from './ledger.js';
import { formatCents } from './money.js';
import { renderReceipt } from './receipt.js';
import { transfer } from './transfer.js';

const USAGE = `Usage:
  tl balance <account>
  tl transfer <from> <to> <cents>`;

// Each command resolves to the text to print. main() turns errors into `Error: <message>` and exit code 1.
export const commands = {
  async balance(ledger, [accountId]) {
    return formatCents(await ledger.getBalance(accountId));
  },
  async transfer(ledger, [fromId, toId, cents]) {
    const receipt = await transfer(ledger, fromId, toId, Number(cents));
    return renderReceipt(receipt);
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
