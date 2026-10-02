# Writing standard

For text a person reads or posts as written: replies to review comments, PR descriptions, and entries promoted into
`docs/LESSONS.md`, `docs/DECISIONS.md`, and `docs/ARCHITECTURE.md`. Reviewers and teammates read these without the
conversation behind them, and a reply that sounds generated gets skimmed or dismissed along with its point. Reports
between the workflow's own steps follow their skill's Output section instead.

## What good looks like

- The point first: what changed, what was decided, or why you disagree - then the evidence (`file:line`, a command and
  its result).
- The team's words for things, and identifiers exactly as the code spells them.
- As long as the reader needs and no longer. No sentence that only restates the one before it.

## The tells to remove

Check the text for these five before handing it over. Any one of them is enough to make a reader discount the rest:

1. **Contrast with a claim nobody made** - "This isn't just a fix, it's a safeguard", "not X but Y". Say Y.
2. **A closing line that restates the paragraph** - "In short, ...", "The result: ...", a one-line flourish at the
   end. End on the last fact.
3. **A bold label on every bullet** - "**Performance:** ..., **Clarity:** ...". Bold only what the reader must not
   miss.
4. **Chat residue** - "Great catch!", "Happy to help", "Hope this helps", "Let me know if you have any questions",
   apologies nobody asked for.
5. **Inflated words** - robust, seamless, comprehensive, crucial, leverage, delve - where a plain verb or a number
   would do. Say what it does, and how much.

## Review replies

Say what was done and where, or why not, in one to three sentences: "Added the null check at `src/index.ts:42`; the new
test covers an empty name." When declining, give the reason and its evidence. Promise a follow-up only when one exists.
