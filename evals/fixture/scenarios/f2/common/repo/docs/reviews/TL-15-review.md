# TL-15: Fee preview command

Level: STANDARD - a new CLI command and module; fees are a payments risk area - Last reviewed: {{ts:1:09:40}} UTC
Sources: Jira TL-15 (In Progress), comments by Quan Le

## Decisions to confirm

| # | Decision | Recommendation | Alternatives | Why |
|---|---|---|---|---|
| 1 | Where the preview lives | `previewFee(amount, kind)` in `src/fees.js` | A new module | `fees.js` already owns the schedule |
| 2 | Ledger access | None: a preview reads no balance | Read the balance to warn about insufficient funds | Support quotes fees while transfers run |

## Summary

Support staff can quote the fee for a typed amount before they run a transfer or a withdrawal:
`tl fee <amount> <transfer|withdraw>` prints `Fee: $X.YZ` and changes no balance.

## Acceptance criteria

- AC1 `node src/cli.js fee 10.50 transfer` -> `Fee: $0.11`, exit 0 (ticket)
- AC2 `node src/cli.js fee 50.25 withdraw` -> `Fee: $1.01`, exit 0 (ticket)
- AC3 `node src/cli.js fee 10 foo` -> `Error: Unknown fee kind: foo`, exit 1 (comment by Quan Le)
- AC4 USAGE lists `tl fee <amount> <transfer|withdraw>` (ticket)
- AC5 `npm run build`, `npm test` and `npm run lint` pass

## Scope / Non-goals

- Fee previews for refunds - later.
- Previews in other currencies - revisit when TL-20 (currency accounts) ships.

## Task breakdown

| # | Task | Depends | Produces |
|---|---|---|---|
| 001 | `previewFee` | - | `previewFee(amount, kind): number` |
| 002 | The `tl fee` command | 001 | The CLI command and its USAGE line |
