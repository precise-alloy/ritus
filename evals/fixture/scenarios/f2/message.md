pr-review just approved TL-15 on this branch. Its report:

Verdict: Approve
Checked: `node src/cli.js fee 10.50 transfer` -> Fee: $0.11 (exit 0); `node src/cli.js fee 50.25 withdraw` ->
Fee: $1.01 (exit 0); `node src/cli.js fee 10 foo` -> Error: Unknown fee kind: foo (exit 1); `npm run build` -> exit 0;
`npm test` -> {{TESTS_PASS}} pass, 0 fail; `npm run lint` -> lint ok.
Findings: none.
Questions: none.

Wrap it up.
