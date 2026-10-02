"""Write the iteration 15 layers (TL-40, a large EPIC with cross-task bugs). Re-runnable: it rewrites its layers.

Design: files/eval/it15-design.md. Scenario docs are written by make_it15_docs.py.
"""
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURE = HERE.parent / "fixture"
LAYERS = FIXTURE / "layers"


def read(rel: str) -> str:
    return (FIXTURE / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


def sub(text: str, old: str, new: str) -> str:
    assert text.count(old) == 1, (old, text.count(old))
    return text.replace(old, new)


LAYER_FILES: dict[str, dict[str, str]] = {}


def put(layer: str, rel: str, text: str) -> None:
    LAYER_FILES.setdefault(layer, {})[rel] = text


# ---------------------------------------------------------------- 001 refund()
REFUND_T1 = read("layers/e-t1/src/refund.js")
REFUND_TEST_T1 = read("layers/e-t1/test/refund.test.js")
HALF_UP_TEST = r"""test('the refunded fee rounds half-up like every fee (D-002)', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    const receipt = await refund(ledger, 'alice', 'bob', 1050, { refundFee: true });
    assert.equal(receipt.feeCents, 11);
    assert.equal(await ledger.getBalance('alice'), 11061);
  } finally {
    await cleanup();
  }
});

"""
assert HALF_UP_TEST in REFUND_TEST_T1
put("l-t1", "src/refund.js", REFUND_T1)
put("l-t1", "test/refund.test.js", REFUND_TEST_T1)

# ---------------------------------------------------------------- 002 the $500 limit
REFUND_T2 = sub(read("layers/e-t2-bug/src/refund.js"), "amountCents >= REFUND_LIMIT_CENTS",
                "amountCents > REFUND_LIMIT_CENTS")
LIMIT_TEST = r"""
test('refunds up to $500.00 go through; above that they are refused', async () => {
  const { ledger, cleanup } = await tempLedger({ alice: 0, bob: 100000 });
  try {
    await refund(ledger, 'alice', 'bob', 50000);
    assert.equal(await ledger.getBalance('alice'), 50000);
    await assert.rejects(refund(ledger, 'alice', 'bob', 50001), /second approver/);
    assert.equal(await ledger.getBalance('alice'), 50000);
    assert.equal(await ledger.getBalance('bob'), 50000);
  } finally {
    await cleanup();
  }
});
"""
REFUND_TEST_T2 = REFUND_TEST_T1 + LIMIT_TEST
put("l-t2", "src/refund.js", REFUND_T2)
put("l-t2", "test/refund.test.js", REFUND_TEST_T2)

# ---------------------------------------------------------------- 003 receipt, 004 tl refund
for rel in ("src/receipt.js", "test/receipt.test.js"):
    put("l-t3", rel, read(f"layers/e-t3/{rel}"))
CLI_T4 = read("layers/e-t4/src/cli.js")
CLI_TEST_T4 = read("layers/e-t4/test/cli.test.js")
put("l-t4", "src/cli.js", CLI_T4)
put("l-t4", "test/cli.test.js", CLI_TEST_T4)

# ---------------------------------------------------------------- 005 record every movement
LEDGER_T5 = read("base/src/ledger.js")
LEDGER_T5 = sub(LEDGER_T5, """  #path;
  #queue = Promise.resolve();

  constructor(path) {
    this.#path = path;
  }
""", """  #path;
  #now;
  #queue = Promise.resolve();

  // `now` is the clock that stamps recorded movements; tests pass a fixed one.
  constructor(path, { now = () => new Date() } = {}) {
    this.#path = path;
    this.#now = now;
  }
""")
LEDGER_T5 = sub(LEDGER_T5, "  static async create(path, balances) {", "  static async create(path, balances, options) {")
LEDGER_T5 = sub(LEDGER_T5, "JSON.stringify({ accounts, nextReceipt: 1001 }, null, 2)",
                "JSON.stringify({ accounts, nextReceipt: 1001, movements: [] }, null, 2)")
LEDGER_T5 = sub(LEDGER_T5, "    return new Ledger(path);", "    return new Ledger(path, options);")
LEDGER_T5 = sub(LEDGER_T5, """  // Apply every entry or none. Each entry is { accountId, deltaCents }. Resolves to the receipt number and the new
  // balance of each touched account.
  apply(entries) {""", """  // Every recorded movement, oldest first. A ledger file written before movements were recorded has none.
  movements() {
    return this.#serialized(async () => (await this.#load()).movements ?? []);
  }

  // Apply every entry or none. Each entry is { accountId, deltaCents }. The movement is recorded in the same save,
  // with its receipt id, kind, memo and time. Resolves to the receipt number and the new balance of each touched
  // account.
  apply(entries, { kind = 'adjustment', memo = {} } = {}) {""")
LEDGER_T5 = sub(LEDGER_T5, """      state.nextReceipt += 1;
      await this.#save(state);""", """      state.nextReceipt += 1;
      state.movements ??= [];
      state.movements.push({ id: `R-${receiptNumber}`, kind, at: this.#now().toISOString(), memo });
      await this.#save(state);""")

TRANSFER_T5 = sub(read("base/src/transfer.js"), "  const { receiptNumber } = await ledger.apply(entries);",
                  "  const memo = { fromId, toId, amountCents, feeCents };\n"
                  "  const { receiptNumber } = await ledger.apply(entries, { kind: 'transfer', memo });")
WITHDRAW_T5 = sub(read("layers/withdraw/src/withdraw.js"), """  const { balances } = await ledger.apply([
    { accountId, deltaCents: -(amountCents + feeCents) },
    { accountId: FEES_ACCOUNT, deltaCents: feeCents },
  ]);""", """  const entries = [
    { accountId, deltaCents: -(amountCents + feeCents) },
    { accountId: FEES_ACCOUNT, deltaCents: feeCents },
  ];
  const { balances } = await ledger.apply(entries, { kind: 'withdraw', memo: { accountId, amountCents, feeCents } });""")
REFUND_T5 = sub(REFUND_T2, "  const { receiptNumber } = await ledger.apply(entries);",
                "  const memo = { fromId, toId, amountCents, feeCents };\n"
                "  const { receiptNumber } = await ledger.apply(entries, { kind: 'refund', memo });")

HELPERS_T5 = read("base/test/helpers.js")
HELPERS_T5 = sub(HELPERS_T5, """// A fresh ledger in its own temp directory. Call cleanup() when the test is done.
export async function tempLedger(balances = { alice: 10000, bob: 5000 }) {""", """// A fresh ledger in its own temp directory; `options` go to Ledger.create (a fixed `now` clock, say). Call cleanup()
// when the test is done.
export async function tempLedger(balances = { alice: 10000, bob: 5000 }, options) {""")
HELPERS_T5 = sub(HELPERS_T5, "  const ledger = await Ledger.create(path, balances);",
                 "  const ledger = await Ledger.create(path, balances, options);")

LEDGER_TEST_T5 = read("base/test/ledger.test.js")
LEDGER_TEST_T5 = sub(LEDGER_TEST_T5, "import assert from 'node:assert/strict';\nimport { test } from 'node:test';",
                     "import assert from 'node:assert/strict';\nimport { writeFile } from 'node:fs/promises';\n"
                     "import { test } from 'node:test';")
LEDGER_TEST_T5 = sub(LEDGER_TEST_T5, "import { FEES_ACCOUNT } from '../src/ledger.js';",
                     "import { FEES_ACCOUNT, Ledger } from '../src/ledger.js';")
LEDGER_TEST_T5 += r"""
const AT = '2026-09-01T10:00:00.000Z';
const clock = () => new Date(AT);

test('apply records each movement with its receipt id, kind, memo and time', async () => {
  const { ledger, cleanup } = await tempLedger(undefined, { now: clock });
  try {
    const memo = { fromId: 'alice', toId: 'bob', amountCents: 300, feeCents: 0 };
    await ledger.apply(
      [
        { accountId: 'alice', deltaCents: -300 },
        { accountId: 'bob', deltaCents: 300 },
      ],
      { kind: 'transfer', memo },
    );
    await ledger.apply([{ accountId: 'bob', deltaCents: -100 }, { accountId: 'alice', deltaCents: 100 }]);
    assert.deepEqual(await ledger.movements(), [
      { id: 'R-1001', kind: 'transfer', at: AT, memo },
      { id: 'R-1002', kind: 'adjustment', at: AT, memo: {} },
    ]);
  } finally {
    await cleanup();
  }
});

test('a refused apply records nothing', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    await assert.rejects(
      ledger.apply(
        [
          { accountId: 'bob', deltaCents: -6000 },
          { accountId: 'alice', deltaCents: 6000 },
        ],
        { kind: 'transfer' },
      ),
      InsufficientFundsError,
    );
    assert.deepEqual(await ledger.movements(), []);
  } finally {
    await cleanup();
  }
});

test('a ledger file from before movements were recorded still loads and records', async () => {
  const { path, cleanup } = await tempLedger();
  try {
    const accounts = { alice: { id: 'alice', balanceCents: 500 }, fees: { id: 'fees', balanceCents: 0 } };
    await writeFile(path, JSON.stringify({ accounts, nextReceipt: 1001 }, null, 2));
    const ledger = new Ledger(path, { now: clock });
    assert.deepEqual(await ledger.movements(), []);
    await ledger.apply([{ accountId: 'alice', deltaCents: -25 }, { accountId: FEES_ACCOUNT, deltaCents: 25 }]);
    assert.deepEqual(await ledger.movements(), [{ id: 'R-1001', kind: 'adjustment', at: AT, memo: {} }]);
  } finally {
    await cleanup();
  }
});

test('without a clock, movements carry the system time', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    const before = Date.now();
    await ledger.apply([{ accountId: 'alice', deltaCents: -1 }, { accountId: 'bob', deltaCents: 1 }]);
    const [{ at }] = await ledger.movements();
    assert.ok(Date.parse(at) >= before && Date.parse(at) <= Date.now(), at);
  } finally {
    await cleanup();
  }
});
"""

TRANSFER_TEST_T5 = read("base/test/transfer.test.js") + r"""
test('transfer records its movement', async () => {
  const { ledger, cleanup } = await tempLedger(undefined, { now: () => new Date('2026-09-01T10:00:00.000Z') });
  try {
    await transfer(ledger, 'alice', 'bob', 2000);
    assert.deepEqual(await ledger.movements(), [
      {
        id: 'R-1001',
        kind: 'transfer',
        at: '2026-09-01T10:00:00.000Z',
        memo: { fromId: 'alice', toId: 'bob', amountCents: 2000, feeCents: 20 },
      },
    ]);
  } finally {
    await cleanup();
  }
});
"""
WITHDRAW_TEST_T5 = read("layers/withdraw/test/withdraw.test.js") + r"""
test('withdraw records its movement', async () => {
  const { ledger, cleanup } = await tempLedger(undefined, { now: () => new Date('2026-09-01T10:00:00.000Z') });
  try {
    await withdraw(ledger, 'alice', 5000);
    assert.deepEqual(await ledger.movements(), [
      {
        id: 'R-1001',
        kind: 'withdraw',
        at: '2026-09-01T10:00:00.000Z',
        memo: { accountId: 'alice', amountCents: 5000, feeCents: 100 },
      },
    ]);
  } finally {
    await cleanup();
  }
});
"""
REFUND_MOVEMENT_TEST = r"""
test('refund records its movement', async () => {
  const { ledger, cleanup } = await tempLedger(undefined, { now: () => new Date('2026-09-01T10:00:00.000Z') });
  try {
    await refund(ledger, 'alice', 'bob', 1050, { refundFee: true });
    assert.deepEqual(await ledger.movements(), [
      {
        id: 'R-1001',
        kind: 'refund',
        at: '2026-09-01T10:00:00.000Z',
        memo: { fromId: 'alice', toId: 'bob', amountCents: 1050, feeCents: 11 },
      },
    ]);
  } finally {
    await cleanup();
  }
});
"""
REFUND_TEST_T5 = REFUND_TEST_T2 + REFUND_MOVEMENT_TEST
for rel, text in (("src/ledger.js", LEDGER_T5), ("src/transfer.js", TRANSFER_T5), ("src/withdraw.js", WITHDRAW_T5),
                  ("src/refund.js", REFUND_T5), ("test/helpers.js", HELPERS_T5),
                  ("test/ledger.test.js", LEDGER_TEST_T5), ("test/transfer.test.js", TRANSFER_TEST_T5),
                  ("test/withdraw.test.js", WITHDRAW_TEST_T5), ("test/refund.test.js", REFUND_TEST_T5)):
    put("l-t5", rel, text)

# ---------------------------------------------------------------- 006 listRefunds()
REFUNDS_JS = r"""// Refunds the account took part in - as the account the money went back to (fromId) or the one it came from
// (toId) - newest first. Each is { id, at, fromId, toId, amountCents, feeCents }.
export async function listRefunds(ledger, { accountId }) {
  await ledger.getBalance(accountId); // throws AccountNotFoundError for an unknown account
  const movements = await ledger.movements();
  return movements
    .filter(({ kind, memo }) => kind === 'refund' && (memo.fromId === accountId || memo.toId === accountId))
    .map(({ id, at, memo }) => ({ id, at, ...memo }))
    .reverse();
}
"""
REFUNDS_TEST_HEAD = r"""import assert from 'node:assert/strict';
import { test } from 'node:test';
import { AccountNotFoundError } from '../src/errors.js';
import { refund } from '../src/refund.js';
import { listRefunds } from '../src/refunds.js';
import { transfer } from '../src/transfer.js';
import { withdraw } from '../src/withdraw.js';
import { tempLedger } from './helpers.js';

const AT = '2026-09-01T10:00:00.000Z';
const clock = () => new Date(AT);
"""
REFUNDS_TEST_LIST = r"""
test('lists the refunds an account took part in, on either side, newest first', async () => {
  const { ledger, cleanup } = await tempLedger({ alice: 10000, bob: 5000, carol: 5000 }, { now: clock });
  try {
    await refund(ledger, 'alice', 'bob', 1050, { refundFee: true });
    await refund(ledger, 'carol', 'alice', 500);
    await refund(ledger, 'carol', 'bob', 700);
    assert.deepEqual(await listRefunds(ledger, { accountId: 'alice' }), [
      { id: 'R-1002', at: AT, fromId: 'carol', toId: 'alice', amountCents: 500, feeCents: 0 },
      { id: 'R-1001', at: AT, fromId: 'alice', toId: 'bob', amountCents: 1050, feeCents: 11 },
    ]);
    assert.deepEqual((await listRefunds(ledger, { accountId: 'bob' })).map((r) => r.id), ['R-1003', 'R-1001']);
  } finally {
    await cleanup();
  }
});
"""
REFUNDS_TEST_TAIL = r"""
test('transfers and withdrawals are not refunds', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    await transfer(ledger, 'alice', 'bob', 2000);
    await withdraw(ledger, 'alice', 1000);
    assert.deepEqual(await listRefunds(ledger, { accountId: 'alice' }), []);
  } finally {
    await cleanup();
  }
});

test('an unknown account is refused', async () => {
  const { ledger, cleanup } = await tempLedger();
  try {
    await assert.rejects(listRefunds(ledger, { accountId: 'dave' }), AccountNotFoundError);
  } finally {
    await cleanup();
  }
});
"""
REFUNDS_TEST = REFUNDS_TEST_HEAD + REFUNDS_TEST_LIST + REFUNDS_TEST_TAIL
put("l-t6", "src/refunds.js", REFUNDS_JS)
put("l-t6", "test/refunds.test.js", REFUNDS_TEST)

# ---------------------------------------------------------------- 007 tl refunds
REPORT_T7 = r"""import { formatAmount } from './money.js';

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
"""
REPORT_TEST_T7 = r"""import assert from 'node:assert/strict';
import { test } from 'node:test';
import { renderRefundReport } from '../src/report.js';

const REFUNDS = [
  { id: 'R-1004', at: '2026-09-02T08:30:00.000Z', fromId: 'alice', toId: 'bob', amountCents: 2000, feeCents: 20 },
  { id: 'R-1002', at: '2026-09-01T23:50:00.000Z', fromId: 'carol', toId: 'alice', amountCents: 500, feeCents: 0 },
];

test('the report lists each refund and totals them', () => {
  assert.equal(
    renderRefundReport('alice', REFUNDS),
    [
      'Refunds for alice',
      'R-1004  2026-09-02  alice <- bob  $20.00  fee $0.20',
      'R-1002  2026-09-01  carol <- alice  $5.00',
      '2 refunds, $25.00 back, $0.20 fees',
    ].join('\n'),
  );
});

test('one refund is counted in the singular', () => {
  assert.match(renderRefundReport('alice', [REFUNDS[1]]), /^1 refund, \$5\.00 back, \$0\.00 fees$/m);
});

test('an account without refunds says so', () => {
  assert.equal(renderRefundReport('dave', []), 'No refunds for dave');
});
"""
CLI_T7 = CLI_T4
CLI_T7 = sub(CLI_T7, "import { refund as applyRefund } from './refund.js';\n",
             "import { refund as applyRefund } from './refund.js';\nimport { listRefunds } from './refunds.js';\n"
             "import { renderRefundReport } from './report.js';\n")
CLI_T7 = sub(CLI_T7, "  tl refund <from> <to> <amount> [--fee]`;", "  tl refund <from> <to> <amount> [--fee]\n  tl refunds <account>`;")
CLI_T7 = sub(CLI_T7, "{ refundFee: flag === '--fee' }));\n  },\n};", """{ refundFee: flag === '--fee' }));
  },
  async refunds(ledger, [accountId]) {
    return renderRefundReport(accountId, await listRefunds(ledger, { accountId }));
  },
};""")
CLI_TEST_T7 = sub(CLI_TEST_T4, "import { main } from '../src/cli.js';\n",
                  "import { main } from '../src/cli.js';\nimport { refund } from '../src/refund.js';\n")
CLI_TEST_T7 += r"""
// alice gets $10.50 back from bob with the fee, then $5.00 from carol.
async function ledgerWithRefunds() {
  const clock = () => new Date('2026-09-01T10:00:00.000Z');
  const temp = await tempLedger({ alice: 10000, bob: 5000, carol: 5000 }, { now: clock });
  await refund(temp.ledger, 'alice', 'bob', 1050, { refundFee: true });
  await refund(temp.ledger, 'alice', 'carol', 500);
  return temp;
}

test('refunds prints the account report', async () => {
  const { path, cleanup } = await ledgerWithRefunds();
  try {
    const { code, output } = await main(['refunds', 'alice'], { ledgerPath: path });
    assert.equal(code, 0);
    assert.equal(
      output,
      [
        'Refunds for alice',
        'R-1002  2026-09-01  alice <- carol  $5.00',
        'R-1001  2026-09-01  alice <- bob  $10.50  fee $0.11',
        '2 refunds, $15.50 back, $0.11 fees',
      ].join('\n'),
    );
  } finally {
    await cleanup();
  }
});

test('refunds for an account without any says so', async () => {
  const { path, cleanup } = await tempLedger();
  try {
    assert.deepEqual(await main(['refunds', 'bob'], { ledgerPath: path }), { code: 0, output: 'No refunds for bob' });
  } finally {
    await cleanup();
  }
});
"""
put("l-t7", "src/report.js", REPORT_T7)
put("l-t7", "test/report.test.js", REPORT_TEST_T7)
put("l-t7", "src/cli.js", CLI_T7)
put("l-t7", "test/cli.test.js", CLI_TEST_T7)

# ---------------------------------------------------------------- 008 tl refunds --csv
REPORT_T8 = REPORT_T7 + r"""
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
"""
REPORT_TEST_T8 = sub(REPORT_TEST_T7, "import { renderRefundReport } from '../src/report.js';",
                     "import { renderRefundReport, renderRefundsCsv } from '../src/report.js';") + r'''
test('the csv has a header, then one row per refund with plain decimal amounts', () => {
  assert.equal(
    renderRefundsCsv(REFUNDS),
    [
      'id,date,back_to,from,amount,fee',
      'R-1004,2026-09-02,alice,bob,20.00,0.20',
      'R-1002,2026-09-01,carol,alice,5.00,0.00',
    ].join('\n'),
  );
});

test('csv fields holding a comma or a quote are quoted, quotes doubled', () => {
  const refund = { ...REFUNDS[1], fromId: 'acme, inc', toId: 'the "shop"' };
  assert.equal(renderRefundsCsv([refund]).split('\n')[1], 'R-1002,2026-09-01,"acme, inc","the ""shop""",5.00,0.00');
});

test('the csv without refunds is the header alone', () => {
  assert.equal(renderRefundsCsv([]), 'id,date,back_to,from,amount,fee');
});
'''
CLI_T8 = CLI_T7
CLI_T8 = sub(CLI_T8, "import { renderRefundReport } from './report.js';",
             "import { renderRefundReport, renderRefundsCsv } from './report.js';")
CLI_T8 = sub(CLI_T8, "  tl refunds <account>`;", "  tl refunds <account> [--csv]`;")
CLI_T8 = sub(CLI_T8, """  async refunds(ledger, [accountId]) {
    return renderRefundReport(accountId, await listRefunds(ledger, { accountId }));
  },""", """  async refunds(ledger, [accountId, flag]) {
    const refunds = await listRefunds(ledger, { accountId });
    return flag === '--csv' ? renderRefundsCsv(refunds) : renderRefundReport(accountId, refunds);
  },""")
CLI_TEST_T8 = CLI_TEST_T7 + r"""
test('refunds --csv prints the csv', async () => {
  const { path, cleanup } = await ledgerWithRefunds();
  try {
    const { code, output } = await main(['refunds', 'alice', '--csv'], { ledgerPath: path });
    assert.equal(code, 0);
    assert.equal(
      output,
      [
        'id,date,back_to,from,amount,fee',
        'R-1002,2026-09-01,alice,carol,5.00,0.00',
        'R-1001,2026-09-01,alice,bob,10.50,0.11',
      ].join('\n'),
    );
  } finally {
    await cleanup();
  }
});
"""
put("l-t8", "src/report.js", REPORT_T8)
put("l-t8", "test/report.test.js", REPORT_TEST_T8)
put("l-t8", "src/cli.js", CLI_T8)
put("l-t8", "test/cli.test.js", CLI_TEST_T8)

# ---------------------------------------------------------------- B1: the refunded fee floors (001), encoded later
def floor_fee(refund_js: str) -> str:
    text = sub(refund_js, "import { computeFee } from './fees.js';", "import { FEE_RATES_BPS } from './fees.js';")
    return sub(text, "const feeCents = refundFee ? computeFee(amountCents, 'transfer') : 0;",
               "const feeCents = refundFee ? Math.floor((amountCents * FEE_RATES_BPS.transfer) / 10000) : 0;")


put("l-b1-t1", "src/refund.js", floor_fee(REFUND_T1))
put("l-b1-t1", "test/refund.test.js", sub(REFUND_TEST_T1, HALF_UP_TEST, ""))
put("l-b1-full", "src/refund.js", floor_fee(REFUND_T5))
put("l-b1-full", "test/refund.test.js",
    sub(sub(REFUND_TEST_T5, HALF_UP_TEST, ""), "amountCents: 1050, feeCents: 11 }", "amountCents: 1050, feeCents: 10 }"))
CLI_TEST_B1 = CLI_TEST_T8
for old, new in (("Fee returned: $0.11", "Fee returned: $0.10"), ("  fee $0.11',", "  fee $0.10',"),
                 ("$15.50 back, $0.11 fees", "$15.50 back, $0.10 fees"), ("10.50,0.11", "10.50,0.10")):
    CLI_TEST_B1 = sub(CLI_TEST_B1, old, new)
put("l-b1-full", "test/cli.test.js", CLI_TEST_B1)
put("l-b1-full", "test/refunds.test.js", sub(REFUNDS_TEST, "amountCents: 1050, feeCents: 11 }",
                                            "amountCents: 1050, feeCents: 10 }"))

# ---------------------------------------------------------------- B2: listRefunds misses the toId side (006)
put("l-b2-t6", "src/refunds.js", sub(REFUNDS_JS, "kind === 'refund' && (memo.fromId === accountId || memo.toId === accountId)",
                                     "kind === 'refund' && memo.fromId === accountId"))
REFUNDS_TEST_HOLLOW = r"""
test('lists the refunds an account took part in, newest first', async () => {
  const { ledger, cleanup } = await tempLedger({ alice: 10000, bob: 5000, carol: 5000 }, { now: clock });
  try {
    await refund(ledger, 'alice', 'bob', 1050, { refundFee: true });
    await refund(ledger, 'alice', 'carol', 500);
    await refund(ledger, 'carol', 'bob', 700);
    assert.deepEqual(await listRefunds(ledger, { accountId: 'alice' }), [
      { id: 'R-1002', at: AT, fromId: 'alice', toId: 'carol', amountCents: 500, feeCents: 0 },
      { id: 'R-1001', at: AT, fromId: 'alice', toId: 'bob', amountCents: 1050, feeCents: 11 },
    ]);
  } finally {
    await cleanup();
  }
});
"""
put("l-b2-t6", "test/refunds.test.js", REFUNDS_TEST_HEAD + REFUNDS_TEST_HOLLOW + REFUNDS_TEST_TAIL)


def main() -> None:
    for layer, files in LAYER_FILES.items():
        root = LAYERS / layer
        if root.exists():
            shutil.rmtree(root)
        for rel, text in files.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
        print(f"{layer}: {', '.join(sorted(files))}")


if __name__ == "__main__":
    main()
