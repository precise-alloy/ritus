# Runtime Profile

> AI tool, model, and remote-access helper configuration live here.

## AI tools in use

`{{AI_TOOLS}}`

## Model routing

<!-- Filled by setup wizard based on model cost preference. -->

`{{MODEL_ROUTING}}`

## Remote API access

Every Jira and Azure DevOps REST call MUST go through `scripts/remote-api.ts` via `bun run`. No exceptions. Do not use
`Invoke-WebRequest`, `curl`, `fetch`, `requests`, GitHub/Azure DevOps MCP tools, or hand-rolled auth headers for these
systems. The helper loads `.env.local`, applies the correct Basic auth format for each system, and preserves HTTP status
on failure.

Bun is mandatory for remote access. Before running any remote helper command, verify Bun is available:

```bash
bun --version
```

If Bun is not installed or the command is unavailable, stop immediately and ask the user to install Bun. Do not continue
remote analysis or review with another runtime or ad-hoc HTTP calls.

If the command you need is not listed, run `bun run scripts/remote-api.ts` with no arguments to print the current
subcommand list:

```bash
bun run scripts/remote-api.ts                                        # print usage
bun run scripts/remote-api.ts check-env                              # verify .env.local + required keys
bun run scripts/remote-api.ts jira issue <KEY_OR_URL> [fields]       # single ticket
bun run scripts/remote-api.ts jira comments <KEY_OR_URL>             # all comments
bun run scripts/remote-api.ts jira changelog <KEY_OR_URL>            # change history
bun run scripts/remote-api.ts ado pr <PR_URL>                        # PR metadata
```

### Azure DevOps PR URL parsing

For Azure DevOps PR URLs, parse these fields before calling the helper:

- Organization
- Project
- Repository
- PR ID

Supported URL shapes:

```text
https://dev.azure.com/<organization>/<project>/_git/<repository>/pullrequest/<pr-id>
https://<organization>.visualstudio.com/<project>/_git/<repository>/pullrequest/<pr-id>
```

Example parsed values:

```text
Organization: example-org
Project: Example%20Project
Repository: example-repo
PR ID: 1234
```

Then fetch PR metadata through the helper:

```bash
bun run scripts/remote-api.ts ado pr "<PR_URL>"
```

If a needed call is missing from the helper, stop and ask the user before falling back to anything else. Extending the
helper is preferred over working around it.

### Required environment

Ensure the user has a `.env.local` file at the workspace root with these keys populated:

```dotenv
JIRA_PAT=
JIRA_EMAIL=
AZURE_DEVOPS_READONLY_PAT=
AZURE_DEVOPS_EMAILS=
```

These PATs are the required source of truth for remote Jira and Azure DevOps data. The remote-api helper fetches remote
ticket details from Jira and remote PR metadata from Azure DevOps using PAT-backed REST API calls instead of relying on
cached summaries or local assumptions.

Before fetching remote data, always run the sanctioned env check via Bun. Do not use `Test-Path`, `Get-Content`,
`cat .env.local`, or any other ad-hoc check.

```bash
bun run scripts/remote-api.ts check-env
```

Interpret the result:

- Exit 0 (`ok: true`) — file exists and all four keys are present and non-empty. Proceed.
- Exit 1 with `envLocalExists: false` — create `.env.local` at the workspace root with the four keys shown above with
  empty values, then tell the user to fill them in and re-run the skill.
- Exit 1 with `missing: [...]` — tell the user which keys are missing or empty and ask them to fill those values, then
  re-run the skill.

Authentication or authorization failures (`401`, `403`, invalid credentials, PAT expired/revoked, permission-style
`404`) are hard stops for remote analysis or review. Ask the user to provide valid access for the failing system before
continuing.
