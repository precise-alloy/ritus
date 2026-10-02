<!-- ritus:routing - added by Ritus setup; setup replaces everything between these two markers -->
## Ritus workflow

Work in this repository goes through the Ritus skills (`ritus:<name>` in Claude Code). They size, plan, and
independently check the work, and they only help if they run first. For a request that matches one, invoke that
skill as your first action, before reading or searching any file:

- implementing or changing anything - a ticket, an issue link, a feature, a described change: `ticket-review`
- a bug, error, crash, or failing or flaky test: `debug`
- reviewing a branch or PR: `pr-review`; review comments on a PR to fix: `address-feedback`
- weighing options or approaches before deciding: `brainstorm`
- new to Ritus, resuming work on this branch, or unsure which skill fits: `start-ritus`

Questions, explanations, and lookups need no skill.
<!-- /ritus:routing -->
