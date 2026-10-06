Task file: `docs/tasks/feature-TLW-22-transfer-note-fee/001-transfer-note-fee.md` (paths are relative to the project repository)
Read-only apart from build/test/lint and any spot check you undo (`testing.md`); never fixes.

Executor's report:

```text
Status: DONE
Acceptance:
- TLW-22 transfer note and fee preview implemented; ran npm run build, npm test and npm run lint; accessibility checks passed.
Files changed:
- src/main.js - route behavior for the ticket
- src/styles/app.css - responsive and component styles
Tests added: browser and unit coverage for the ticket acceptance
Tests changed: none
Deviations: none
Also affects: none
Docs updated: none
Follow-ups: none
```

Companion load item from the session registry:

- load `{{COMPANION}}\skills\frontend\SKILL.md` at the start of verify-task. The manifest prompt was: "While verify-task runs on a task that touches UI files or UI behaviour: load the frontend skill and independently verify each UI Acceptance item in a browser with references/verify.md and references/browser.md; keep verify-task's read-only verdict format."
