# Remote API Access

Every Jira, Azure DevOps, and GitHub REST call MUST go through `.ritus/scripts/remote-api.ts` via `bun run`. No exceptions. Do not use `Invoke-WebRequest`, `curl`, `fetch`, `requests`, GitHub/Azure DevOps MCP tools, or hand-rolled auth headers for these systems. The helper loads `.env.local`, applies the correct auth format for each system, and preserves HTTP status on failure.

Bun is mandatory for remote access. Before running any remote helper command, verify Bun is available:

```bash
bun --version
```

If Bun is not installed or the command is unavailable, stop immediately and ask the user to install Bun. Do not continue remote analysis or review with another runtime or ad-hoc HTTP calls.

If the command you need is not listed, run `bun run .ritus/scripts/remote-api.ts` with no arguments to print the current subcommand list:

```bash
bun run .ritus/scripts/remote-api.ts                                        # print usage
bun run .ritus/scripts/remote-api.ts check-env                              # verify .env.local + required keys

# Jira
bun run .ritus/scripts/remote-api.ts jira issue <KEY_OR_URL> [fields]       # single ticket
bun run .ritus/scripts/remote-api.ts jira comments <KEY_OR_URL>             # all comments
bun run .ritus/scripts/remote-api.ts jira changelog <KEY_OR_URL>            # change history
bun run .ritus/scripts/remote-api.ts jira attachments <KEY_OR_URL>          # list attachments
bun run .ritus/scripts/remote-api.ts jira attachment-download <KEY_OR_URL> <OUTPUT_DIR>  # download images

# Azure DevOps (ADO)
bun run .ritus/scripts/remote-api.ts ado pr <PR_URL>                        # PR metadata
bun run .ritus/scripts/remote-api.ts ado issue <WORK_ITEM_URL_OR_ID> [fields]  # work item details
bun run .ritus/scripts/remote-api.ts ado comments <WORK_ITEM_URL_OR_ID>     # work item comments
bun run .ritus/scripts/remote-api.ts ado changelog <WORK_ITEM_URL_OR_ID>    # work item updates

# GitHub
bun run .ritus/scripts/remote-api.ts github pr <PR_URL>                     # PR metadata
```

## URL parsing

### Jira ticket keys

Accepts a bare key (e.g. `PROJ-123`) or a full browse URL (e.g. `https://your-company.atlassian.net/browse/PROJ-123`).

### Azure DevOps PR URLs

Supported URL shapes:

```text
https://dev.azure.com/<organization>/<project>/_git/<repository>/pullrequest/<pr-id>
https://<organization>.visualstudio.com/<project>/_git/<repository>/pullrequest/<pr-id>
```

### Azure DevOps work item URLs

Supported URL shapes:

```text
https://dev.azure.com/<organization>/<project>/_workitems/edit/<work-item-id>
https://<organization>.visualstudio.com/<project>/_workitems/edit/<work-item-id>
```

Bare numeric IDs (e.g. `12345`) are also accepted when `AZURE_DEVOPS_ORG` and `AZURE_DEVOPS_PROJECT` are set in `.env.local`.

### GitHub PR URLs

```text
https://github.com/<owner>/<repo>/pull/<number>
```

If a needed call is missing from the helper, stop and ask the user before falling back to anything else. Extending the helper is preferred over working around it.

## Required environment

Ensure the user has a `.env.local` file at the workspace root with the keys for the providers they use:

```dotenv
# Jira Cloud
JIRA_BASE_URL=
JIRA_PAT=
JIRA_EMAIL=

# Azure DevOps
AZURE_DEVOPS_READONLY_PAT=
# Optional: for bare work item IDs
AZURE_DEVOPS_ORG=
AZURE_DEVOPS_PROJECT=

# GitHub
GITHUB_TOKEN=
# Optional: alternative token name used by GitHub CLI
GH_TOKEN=
```

Not all providers need to be configured — only the ones the project uses. `check-env` reports which providers are configured; the helper validates the required keys for the invoked provider before dispatch.

Before fetching remote data, always run the sanctioned env check via Bun. Do not use `Test-Path`, `Get-Content`, `cat .env.local`, or any other ad-hoc check.

```bash
bun run .ritus/scripts/remote-api.ts check-env
```

Interpret the result:

- Exit 0 — at least one provider is fully configured. Proceed.
- Exit 1 with `envLocalExists: false` — report that `.env.local` is missing. Ask the user to copy `.env.example` to `.env.local` and fill in the values. Do NOT create the file yourself.
- Exit 1 with no providers configured — tell the user which keys are missing and ask them to fill those values, then re-run the skill.

Authentication or authorization failures (`401`, `403`, invalid credentials, PAT expired/revoked, permission-style `404`) are hard stops for remote analysis or review. Ask the user to provide valid access for the failing system before continuing.
