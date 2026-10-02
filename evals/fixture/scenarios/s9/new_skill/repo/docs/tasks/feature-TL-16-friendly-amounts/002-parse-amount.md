# Task 002: Add parseAmount for typed amounts

Level: STANDARD - Depends on: none - Plan: docs/reviews/TL-16-review.md
Status: implemented

## Goal

Turn an amount typed by support staff ("12.34", "1,234.50", " 7 ") into integer cents, and refuse anything that is
not an amount greater than zero. Task 003 uses it in `tl transfer`.

## Acceptance

- [ ] Valid forms - `npm test` -> the money tests show "12.34" -> 1234, "0.5" -> 50, "7" -> 700, "1,234.50" ->
  123450, " 7 " -> 700
- [ ] Refused with `InvalidAmountError`: "abc", "", "   ", "-5", "1.234", "1,23", "12.", "0", "0.00" - `npm test`
- [ ] Refused with `InvalidAmountError`: non-text input, and amounts too large to count in cents ("90071992547410") -
  `npm test`
- [ ] Smoke - `node -e "import('./src/money.js').then((m) => console.log(m.parseAmount('1,234.50')))"` -> `123450`
- [ ] `npm run build` -> exit 0; `npm test` -> 0 failures; `npm run lint` -> `lint ok`

## Constraints

- Integer cents without float arithmetic - D-001
- Every refusal throws `InvalidAmountError` (`src/errors.js:26-31`), so the CLI prints `Error: Invalid amount ...`
  and exits 1
- Only amounts greater than zero are valid - plan D2 (support lead, ticket comment)

## Interfaces

- Consumes: `InvalidAmountError(input: unknown, reason: string)` (`src/errors.js:26-31`)
- Produces: `parseAmount(input: string): number` - integer cents, always greater than zero (used by task 003)

## Non-goals

- The CLI - task 003 switches `tl transfer` to `parseAmount`
- Other locales - "1.234,50" is refused, not read as 1234.50

## Starting points

- `src/money.js:4-17` - `formatAmount`; add `parseAmount` next to it
- `test/money.test.js` - valid forms and every refusal
