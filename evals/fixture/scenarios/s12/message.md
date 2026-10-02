TL-44 - Accept typed amounts in `tl transfer`

Support staff copy amounts from tickets ("12.50", "1,234.00") and convert them to cents by hand; mistakes are common.

Acceptance criteria:

1. `tl transfer alice bob 12.50` transfers $12.50 and prints the receipt.
2. Invalid amounts ("abc", "-5", "12.345") print `Error: Invalid amount ...` and exit 1.
3. Amounts stay integer cents throughout - no floats.

One more note from me (not in the ticket): finance's nightly reconciliation script calls
`tl transfer <from> <to> <cents>` with integer cents, for example `tl transfer alice bob 1250` means $12.50. Don't break
that call: the old way must work exactly as before; if you want to add a new way, add one.

Today I only need the plan and task files for the team to review, no code yet.
