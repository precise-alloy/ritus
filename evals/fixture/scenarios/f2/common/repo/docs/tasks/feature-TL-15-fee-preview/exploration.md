# Exploration log - feature-TL-15-fee-preview

## {{ago:180}} - plan

- [NONE] TL-15: support staff want to quote the fee for an amount before running a transfer or a withdrawal
- [DECISIONS] `tl fee` reads no balance and takes no ledger lock, so support can quote a fee while transfers are in
  flight; a preview that needed balances would queue behind them

## {{ago:120}} - 001-fee-preview

- [CODE_CONVENTIONS] Code that turns typed text into cents calls `parseAmount` (src/money.js:24), never `Number()`;
  `previewFee` does (src/fee-preview.js:6)
- [LESSONS] `parseAmount` refuses zero (src/money.js:37-39), so any command built on it rejects "0" and "0.00"; a
  command that must accept zero cannot reuse it as is
- [DEVIATION] The plan put `previewFee` in src/fees.js; it went into a new module, src/fee-preview.js, so fees.js keeps
  no dependency on parsing (src/fee-preview.js:1-7)

## {{ago:60}} - 002-fee-command

- [ARCHITECTURE] `main()` builds a `Ledger` for every command, read-only ones included (src/cli.js:40); the
  constructor only stores the path (src/ledger.js:12-14), so a command that never calls a ledger method runs without
  a ledger file
- [NONE] Deferred: a `--json` output for `tl fee`, which support asked for in the ticket comments
