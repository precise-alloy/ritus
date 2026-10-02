import { readFile, rename, writeFile } from 'node:fs/promises';
import { AccountNotFoundError, InsufficientFundsError } from './errors.js';

export const FEES_ACCOUNT = 'fees';

// File-backed ledger. Every balance read and write goes through this class: it runs operations one at a time, so
// two transfers can never interleave a read-modify-write on the same file (docs/DECISIONS.md D-003).
export class Ledger {
  #path;
  #queue = Promise.resolve();

  constructor(path) {
    this.#path = path;
  }

  static async create(path, balances) {
    const accounts = {};
    for (const [id, balanceCents] of Object.entries(balances)) {
      accounts[id] = { id, balanceCents };
    }
    accounts[FEES_ACCOUNT] ??= { id: FEES_ACCOUNT, balanceCents: 0 };
    await writeFile(path, JSON.stringify({ accounts, nextReceipt: 1001 }, null, 2));
    return new Ledger(path);
  }

  getBalance(accountId) {
    return this.#serialized(async () => {
      const state = await this.#load();
      return this.#account(state, accountId).balanceCents;
    });
  }

  // Apply every entry or none. Each entry is { accountId, deltaCents }. Resolves to the receipt number and the new
  // balance of each touched account.
  apply(entries) {
    return this.#serialized(async () => {
      const state = await this.#load();
      const balances = {};
      for (const { accountId, deltaCents } of entries) {
        const current = balances[accountId] ?? this.#account(state, accountId).balanceCents;
        balances[accountId] = current + deltaCents;
      }
      for (const [accountId, balanceCents] of Object.entries(balances)) {
        if (balanceCents < 0 && accountId !== FEES_ACCOUNT) {
          const before = state.accounts[accountId].balanceCents;
          throw new InsufficientFundsError(accountId, before, before - balanceCents);
        }
      }
      for (const [accountId, balanceCents] of Object.entries(balances)) {
        state.accounts[accountId].balanceCents = balanceCents;
      }
      const receiptNumber = state.nextReceipt;
      state.nextReceipt += 1;
      await this.#save(state);
      return { receiptNumber, balances };
    });
  }

  #account(state, accountId) {
    const account = Object.hasOwn(state.accounts, accountId) ? state.accounts[accountId] : undefined;
    if (!account) {
      throw new AccountNotFoundError(accountId);
    }
    return account;
  }

  async #load() {
    return JSON.parse(await readFile(this.#path, 'utf8'));
  }

  async #save(state) {
    const tmp = `${this.#path}.tmp`;
    await writeFile(tmp, JSON.stringify(state, null, 2));
    await rename(tmp, this.#path);
  }

  #serialized(operation) {
    const run = this.#queue.then(operation, operation);
    this.#queue = run.catch(() => {});
    return run;
  }
}
