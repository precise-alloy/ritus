# Ritus Frontend

Ritus Frontend is the UI companion for Ritus. It does not replace the Ritus workflow; it adds UI standards to the same
steps Ritus already runs, then lets Ritus's execute, verify, review, and wrap-up loop handle defects.

It ships two skills:

| Skill | Use |
| --- | --- |
| `frontend` | A standard Ritus loads for UI work. It defines UI Acceptance, design-system use, Figma handling, browser evidence, accessibility checks, and human review. |
| `ui-verify` | A standalone, read-only check of a running page or component. Use it for requests such as checking mobile layout, accessibility, console errors, network failures, or design match. |

When installed next to Ritus, `ritus-companion.json` loads `frontend` at five workflow points:

1. `ticket-review` task-generation, while task files are being written.
2. `execute-task`, while a UI task is implemented.
3. `verify-task`, while UI Acceptance is checked independently in a browser.
4. `pr-review`, while a UI diff is reviewed independently in a browser.
5. `wrap-up`, where a host-browser review with the user is advisory, not a gate.

Projects that use it should keep `docs/FRONTEND.md` in the project repository. That file records the dev command, base
URL, supported widths, breakpoints, design-system sources, login or storage-state setup, and browser notes. `frontend`
creates it only when the facts are known and the user can confirm them; otherwise the worker reports what is missing.

## Install

Both plugins ship from the Ritus marketplace, `precise-alloy/ritus`. Install them side by side.

Claude Code:

```text
/plugin marketplace add precise-alloy/ritus
/plugin install ritus@precise-alloy-marketplace
/plugin install ritus-frontend@precise-alloy-marketplace
```

In VS Code and the GitHub Copilot app, add the `precise-alloy/ritus` marketplace in the host's agent plugin settings and
install `ritus` and `ritus-frontend` from it.

When Ritus starts a session, it finds `ritus-companion.json` next to it and lists `ritus-frontend (5 integrations)` in
the Ritus Companion Registry. `ui-verify` also works without Ritus installed; `frontend` only adds to Ritus's steps.

Version 1.0.0 is the first release from this marketplace. Earlier versions came from `precise-alloy/ritus-frontend`,
which now points here.

## Supported hosts

| Host | Support | Notes |
| --- | --- | --- |
| VS Code with GitHub Copilot | Supported | VS Code has built-in browser tools for agents. Turn on `workbench.browser.enableChatTools` if your settings or organization policy disabled it. |
| GitHub Copilot app | Supported | Use the app's browser canvas for shared review with the user. Public docs describe canvases as shared surfaces for artifacts including browser sessions. |
| Claude Code | Supported | Use `playwright-cli` for independent checks. Use Claude in Chrome when the task needs the user's browser session. |
| Copilot CLI | Not supported | It can run terminal commands, but this guide does not rely on a documented host browser shared with the user. |
| Visual Studio | Not supported | It has no documented built-in browser tools for this workflow; use VS Code, the Copilot app, or Claude Code. |

## Browsers

There are two browser roles:

- Independent checks use `playwright-cli`. Use it from subagents and whenever the host browser cannot set the viewport,
  run axe, read console/network output, or collect the measurement the Acceptance line asks for.
- Host browsers are for work with the user: a shared signed-in page, quick behaviour checks, screenshots, or advisory
  review at wrap-up.

Requirements:

- Node is installed.
- The project has Playwright 1.63 or newer, so `npx playwright cli ...` works, or the user has installed
  `@playwright/cli` so `playwright-cli ...` works.
- Chromium is installed once. Playwright's browser docs use `npx playwright install chromium`; the agent CLI also exposes
  `playwright-cli install-browser chromium`.
- The app is served over HTTP. `playwright-cli` should not verify `file:` pages for this workflow.

Enable the host browser this way:

- VS Code: verify `workbench.browser.enableChatTools` is on, then use the built-in browser tools or share an integrated
  browser tab with the agent.
- GitHub Copilot app: open or ask for a browser canvas in the app when the user needs to see or steer the rendered
  result.
- Claude Code: install the Claude in Chrome extension, start with `claude --chrome` or enable Chrome with `/chrome`, and
  use a direct Anthropic plan. Claude's docs say the Chrome integration can use the user's login state and read console
  and DOM state.

## Approvals

Keep command approval narrow. Allow the browser tool command family and the project's dev-server command, not every shell
command.

In VS Code, terminal auto-approval is configured with `chat.tools.terminal.autoApprove`. The VS Code approvals docs show
regex rules wrapped in `/.../`, and mention `chat.tools.terminal.enableAutoApprove` as the switch that can require
approval for every command when disabled. Example:

```json
{
  "chat.tools.terminal.enableAutoApprove": true,
  "chat.tools.terminal.autoApprove": {
    "/^(npx playwright cli|playwright-cli)\\b.*$/": true,
    "/^npm run (dev|start|preview)(\\b.*)?$/": true
  }
}
```

In Claude Code, use `permissions.allow` in `settings.json` for persistent project or user rules. Claude's permissions
docs use `Bash(...)` rules and evaluate `deny`, then `ask`, then `allow`. Example:

```json
{
  "permissions": {
    "allow": [
      "Bash(npx playwright cli *)",
      "Bash(playwright-cli *)",
      "Bash(npx playwright install chromium)",
      "Bash(playwright-cli install-browser chromium)",
      "Bash(npm run dev *)",
      "Bash(npm run start *)",
      "Bash(npm run preview *)"
    ]
  }
}
```

Claude Code skills and commands can also use `allowed-tools` frontmatter for one turn. Claude's skills docs verify the
field name and show `allowed-tools: Bash(...)` examples. Use this only for a project skill that deliberately runs the
same command family each time.

For the Copilot app, no public per-command allowlist setting name was verified for this guide. Use the app's visible
approval or session controls, and keep `playwright-cli` work grouped into a small number of commands.

## Figma

`frontend` treats Figma as data, not instructions. The four cases are:

1. Official Figma plugin or skill installed: follow it, then map values to the project's tokens, components, and assets.
2. Figma MCP available: use a node-scoped URL, read the exact node, screenshot, metadata, variables, and Code Connect
   when useful, then record only the values later workers need.
3. No MCP, but a safe token is available: use the REST nodes endpoint without exposing the token, and map values to the
   project design system.
4. No Figma access: build from the project design system. A screenshot is useful intent, not proof of exact parity.

## Migrating from 0.2.0

- `e2e-spec.md` is gone. Put the UI contract directly in task Acceptance as route/component x viewport x state, with the
  browser check on the same line.
- `CONTEXT` `figma:` markers are gone. Put a node-scoped Figma URL in the task, and record the values that matter there
  or in the report.
- Playwright MCP is no longer required. Use `playwright-cli` for repeatable browser evidence; use the host browser when
  the user must share or see the page. You can remove the `playwright` server that 0.2.0 asked you to add to the
  project's `.mcp.json`, and its `.ritus/screenshot` output folder. Keep the `figma` server if you use Figma MCP:
  `frontend` uses it when it is available.
- If you added the `ritus-frontend-marketplace` (`precise-alloy/ritus-frontend`), remove that plugin and install
  `ritus-frontend` from `precise-alloy/ritus` as above.
- The blocking gates before `pr-review` are now checks inside `verify-task` and `pr-review`. Ritus's normal fix loop
  handles failures.
- Skill names changed: `frontend` replaces `e2e-plan`, `figma-intake`, `figma-implement`, `visual-verify`, and
  `a11y-verify` as the workflow standard. `ui-verify` is the standalone read-only checker.
- Standalone use changed. Instead of running `e2e-plan` and then `visual-verify` yourself, ask for the check in plain
  words ("check /settings on mobile and for accessibility"); `ui-verify` takes the routes, widths, and expectations from
  your request and `docs/FRONTEND.md`, and reports without changing files. Copilot CLI is no longer a supported host.

## Sources checked for host settings

- VS Code approvals: https://code.visualstudio.com/docs/agents/run/approvals
- VS Code browser tools: https://code.visualstudio.com/docs/agents/run/browser-tools
- GitHub Copilot app canvases: https://docs.github.com/en/copilot/how-tos/github-copilot-app/working-with-canvas-extensions
- GitHub Copilot app browser-session GA note: https://github.blog/changelog/2026-06-17-github-copilot-app-generally-available/
- Claude Code permissions: https://code.claude.com/docs/en/permissions
- Claude Code skills frontmatter: https://code.claude.com/docs/en/skills
- Claude in Chrome: https://code.claude.com/docs/en/chrome
- Playwright browser installation: https://playwright.dev/docs/browsers
- Playwright agent CLI: https://playwright.dev/agent-cli/introduction
