# Browser checks

Choose the browser by capability, not by host name. A check may need JavaScript evaluation, viewport control, console
messages, network requests, subagent access, a session the user shares for login, or a browser the user can watch. Use
the smallest browser that has the needed capabilities; when a required capability is missing, use `playwright-cli`.

## Host browser capabilities

| Browser | Use it when | Known limits |
|---|---|---|
| VS Code integrated browser | The user is in VS Code and the check needs navigation, clicks, typing, screenshots, Playwright code, or console errors | No confirmed agent viewport tool, network-request list, or scored accessibility audit |
| Copilot app browser canvas | The main thread is with the user and the check fits the shared canvas: navigation, clicks, typing, screenshots, JavaScript evaluation, or a user-visible review | Main thread only; fixed 1280x720 viewport; narrow widths need a same-origin iframe; no console or network tool |
| Claude in Chrome | The check needs the user's signed-in Chrome profile, user-visible browsing, or console/DOM debugging | No confirmed agent viewport, network, axe, or JavaScript-evaluation contract in this standard |
| Claude Desktop browser pane | A clean browser profile is acceptable and the check needs user-visible navigation, screenshots, DOM inspection, clicks, or form filling | Clean profile, not the user's login; no confirmed agent viewport, network, console, axe, or JavaScript-evaluation contract in this standard |

Host browsers are good for shared review and quick behaviour checks. They do not replace measured checks when the task
names widths, rendered values, console, network, or axe evidence that the host cannot collect.

## `playwright-cli`

Use `playwright-cli` for subagents and for any check the host browser cannot run. Prefer the project's Playwright:

```powershell
npx playwright cli -s=<check-name> <command>
```

If the project does not provide Playwright 1.63 or newer, use `@playwright/cli` from the user's approved setup. Do not
install tools unless the task asks for it or the chosen validation command fails because the tool is missing.

Rules:

- Serve the app over HTTP. The CLI refuses `file:` pages.
- Start the app with the dev command in `docs/FRONTEND.md`, and stop only the process you started, by PID.
- Use one named session per check with `-s=<check-name>`. Sessions are shared machine-wide, so names must be specific.
- Close the session at the end.
- Keep `.playwright-cli/` out of the diff. It is a tool artifact folder.
- `run-code` cannot use `require`, `import`, `process`, or project modules. Pass literal file paths and use the
  Playwright `page` object.

## Verified recipes

Replace the URL, route, session name, selector, path, and filenames with values for the current project. The flags shown
here were verified on Windows with `npx playwright cli`.

Open a route:

```powershell
npx playwright cli -s=<check-name> open http://localhost:<port>/<route>
```

Set the viewport:

```powershell
npx playwright cli -s=<check-name> resize 375 800
```

Read the accessibility snapshot:

```powershell
npx playwright cli -s=<check-name> snapshot --raw
```

Measure rendered values:

```powershell
npx playwright cli -s=<check-name> eval '() => { const el = document.querySelector("<selector>"); const box = el.getBoundingClientRect(); const style = getComputedStyle(el); return { width: window.innerWidth, box: { x: box.x, y: box.y, width: box.width, height: box.height }, color: style.color, fontWeight: style.fontWeight }; }' --raw
```

Run several Playwright actions in one call:

```powershell
npx playwright cli -s=<check-name> run-code 'async page => ({ url: page.url(), title: await page.title(), width: await page.evaluate(() => window.innerWidth) })' --raw
```

Read console errors:

```powershell
npx playwright cli -s=<check-name> console error --raw
```

Read network requests:

```powershell
npx playwright cli -s=<check-name> requests --raw
```

Save a screenshot:

```powershell
npx playwright cli -s=<check-name> screenshot --filename=<evidence-name>.png --raw
```

Close the session:

```powershell
npx playwright cli -s=<check-name> close
```

## Approvals

Many hosts ask before every shell command. Keep checks readable, but group related measurements into one `eval` or
`run-code` call when that avoids repeated approvals. For regular use, point the user to the host's command-approval or
allowlist guide for `npx playwright cli` or `playwright-cli`.

## When no browser can run

Do not infer a pass from code or screenshots alone. If no available browser can provide the evidence the Acceptance line
asks for, report `BLOCKED` with the missing capability, tool, URL, login, app process, or target.
