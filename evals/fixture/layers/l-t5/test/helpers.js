import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { Ledger } from '../src/ledger.js';

// A fresh ledger in its own temp directory; `options` go to Ledger.create (a fixed `now` clock, say). Call cleanup()
// when the test is done.
export async function tempLedger(balances = { alice: 10000, bob: 5000 }, options) {
  const dir = await mkdtemp(join(tmpdir(), 'tinyledger-'));
  const path = join(dir, 'ledger.json');
  const ledger = await Ledger.create(path, balances, options);
  return { ledger, path, cleanup: () => rm(dir, { recursive: true, force: true }) };
}
