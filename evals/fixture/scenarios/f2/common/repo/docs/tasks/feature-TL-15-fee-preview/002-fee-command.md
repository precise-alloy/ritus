# Task 002: Add the `tl fee` command

Level: STANDARD - Depends on: 001 - Plan: docs/reviews/TL-15-review.md
Status: verified

## Goal

Support staff run `tl fee <amount> <transfer|withdraw>` to see a fee before they move money (TL-15, AC1-AC4).

## Acceptance

- [AC1] `node src/cli.js fee 10.50 transfer` -> `Fee: $0.11`, exit 0
- [AC2] `node src/cli.js fee 50.25 withdraw` -> `Fee: $1.01`, exit 0
- [AC3] `node src/cli.js fee 10 foo` -> `Error: Unknown fee kind: foo`, exit 1
- [AC4] USAGE lists `tl fee <amount> <transfer|withdraw>` - diff: `src/cli.js`
- [AC5] `npm run build` -> exit 0; `npm test` -> 0 failures; `npm run lint` -> `lint ok`

## Interfaces

- Consumes: `previewFee(amount: string, kind: 'transfer' | 'withdraw'): number`

## Starting points

- `src/cli.js:15-26` - `commands`; add `fee` next to `withdraw`
- Pattern: Add a CLI command (`docs/ARCHITECTURE.md`)

## Docs

- `README.md`: add a `tl fee` example to the command examples
