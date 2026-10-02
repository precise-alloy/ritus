TL-27 - Refund a mistaken transfer

Support sometimes sends a transfer to the wrong account or for the wrong amount, and today someone edits ledger.json by
hand to undo it. Add a refund operation to the library; the `tl refund` command is a separate ticket (TL-28).

Acceptance criteria:

1. A refund moves the transferred amount back from the recipient to the sender, as a new ledger movement - nothing
   already recorded is edited, because finance reconciles against the ledger.
2. When the mistake was ours, support can refund the transfer fee too; the fee comes back out of the fees account.
3. Support types the original sender, recipient and amount from the receipt; there is no transfer history to look up.
4. Refunds above $500.00 need a second approver, which TL-31 will add; until then they are refused.

Today I only need the plan and task files for the team to review, no code yet.
