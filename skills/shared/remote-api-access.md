# Remote API Access

Every Jira, Azure DevOps, and GitHub REST call MUST go through the remote API script via `bun run`. No exceptions. Do not use `Invoke-WebRequest`, `curl`, `fetch`, `requests`, GitHub/Azure DevOps MCP tools, or hand-rolled auth headers for these systems. The helper loads `.env.local`, applies the correct auth format for each system, and preserves HTTP status on failure.

## Script location

The remote API script is located at `<plugin-root>/scripts/remote-api.ts`, where `<plugin-root>` is the ritus plugin installation directory.

To derive `<plugin-root>` from this skill file's base directory: this file is at `<plugin-root>/skills/shared/remote-api-access.md`, so the plugin root is 2 directory levels up from `skills/shared/`.

When invoking the script, use the full path: `bun run "<plugin-root>/scripts/remote-api.ts"`.

## Prerequisites

Bun is mandatory for remote access. Before running any remote helper command, verify Bun is available:

```bash
bun --version
```

If Bun is not installed or the command is unavailable, stop immediately and ask the user to install Bun. Do not continue remote analysis or review with another runtime or ad-hoc HTTP calls.

## Auto-detected invocation

The preferred syntax omits the provider name. The script auto-detects the provider from the target URL or key shape
combined with configured credentials:

```bash
bun run "<plugin-root>/scripts/remote-api.ts" <action> <target> [extra]
```

Examples:

```bash
bun run "<plugin-root>/scripts/remote-api.ts" issue "PROJ-123"                                  # Jira (key prefix)
bun run "<plugin-root>/scripts/remote-api.ts" issue 340796                                      # ADO (bare number)
bun run "<plugin-root>/scripts/remote-api.ts" pr '#18'                                          # GitHub (#-prefixed)
bun run "<plugin-root>/scripts/remote-api.ts" pr "https://github.com/owner/repo/pull/42"        # GitHub (full URL)
bun run "<plugin-root>/scripts/remote-api.ts" pr "https://dev.azure.com/org/proj/_git/repo/pullrequest/1"  # ADO (full URL)
bun run "<plugin-root>/scripts/remote-api.ts" comments "PROJ-123"                               # Jira comments
bun run "<plugin-root>/scripts/remote-api.ts" comments '#18' 10                                 # GitHub PR comments
```

Target format conventions (no ambiguity between providers):

| Provider | Short ref format | Example |
|----------|-----------------|---------|
| Jira | Key prefix | `PROJ-123` |
| ADO | Bare number | `340796` |
| GitHub | `#` prefix (requires `GITHUB_REPO_URL` in `.env.local`) | `'#18'` (quotes required — `#` is a shell comment character) |

Auto-detection logic:

1. Filters to providers with valid credentials (`.env.local` keys present).
2. Filters further to providers whose `canHandleTarget(action, target)` returns true (URL hostname / key pattern / `#` prefix match).
3. Exactly 1 match: uses that provider. 0 matches: actionable error listing configured providers. >1 match: ambiguous error with explicit disambiguation commands.

## Explicit provider (override)

When auto-detection is ambiguous or you need a specific provider, use the explicit syntax:

```bash
bun run "<plugin-root>/scripts/remote-api.ts" <provider> <action> <target> [extra]
```

This is the original syntax and remains fully supported. Use it as a fallback when auto-detection cannot resolve the
provider (e.g., a bare numeric ID that could be either an ADO work item or a Jira key from a numeric-prefix project).

## Command catalogue

> Commands below use **explicit provider syntax** for reference. To use auto-detection instead, omit the provider
> prefix — e.g., `bun run "<plugin-root>/scripts/remote-api.ts" pr <URL>` instead of `github pr <URL>`.

If the command you need is not listed, run `bun run "<plugin-root>/scripts/remote-api.ts"` with no arguments to print the current subcommand list:

```bash
bun run "<plugin-root>/scripts/remote-api.ts"                                        # print usage
bun run "<plugin-root>/scripts/remote-api.ts" check-env                              # verify .env.local + required keys

# Jira
bun run "<plugin-root>/scripts/remote-api.ts" jira issue <KEY_OR_URL> [fields]       # single ticket
bun run "<plugin-root>/scripts/remote-api.ts" jira comments <KEY_OR_URL>             # all comments
bun run "<plugin-root>/scripts/remote-api.ts" jira changelog <KEY_OR_URL>            # change history
bun run "<plugin-root>/scripts/remote-api.ts" jira attachments <KEY_OR_URL>          # list attachments
bun run "<plugin-root>/scripts/remote-api.ts" jira attachment-download <KEY_OR_URL> <OUTPUT_DIR>  # download images

# Azure DevOps (ADO)
bun run "<plugin-root>/scripts/remote-api.ts" ado pr <PR_URL>                        # PR metadata
bun run "<plugin-root>/scripts/remote-api.ts" ado pr-threads <PR_URL> [count]        # PR review threads
bun run "<plugin-root>/scripts/remote-api.ts" ado issue <WORK_ITEM_URL_OR_ID> [fields]  # work item details
bun run "<plugin-root>/scripts/remote-api.ts" ado comments <WORK_ITEM_URL_OR_ID>     # work item comments
bun run "<plugin-root>/scripts/remote-api.ts" ado changelog <WORK_ITEM_URL_OR_ID>    # work item updates

# GitHub
bun run "<plugin-root>/scripts/remote-api.ts" github pr <PR_URL_OR_#NUMBER>              # PR metadata
bun run "<plugin-root>/scripts/remote-api.ts" github comments <PR_URL_OR_#NUMBER> [count]  # PR review comments
bun run "<plugin-root>/scripts/remote-api.ts" github issue <ISSUE_URL_OR_#NUMBER>          # issue details
bun run "<plugin-root>/scripts/remote-api.ts" github issue-comments <ISSUE_URL_OR_#NUMBER> [count]  # issue comments
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
#<number>                                         # requires GITHUB_REPO_URL in .env.local
```

### GitHub Issue URLs

```text
https://github.com/<owner>/<repo>/issues/<number>
#<number>                                         # requires GITHUB_REPO_URL in .env.local
```

The `#` prefix resolves via `GITHUB_REPO_URL` (e.g., `https://github.com/owner/repo`) to construct the full URL.

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
# Optional: for #-prefixed short refs (e.g., #18 → https://github.com/owner/repo/pull/18)
GITHUB_REPO_URL=
```

Not all providers need to be configured — only the ones the project uses. `check-env` reports which providers are configured; the helper validates the required keys for the invoked provider before dispatch.

To generate a tailored `.env.example` from the project's `team.yml` provider config:

```bash
bun run "<plugin-root>/scripts/remote-api.ts" generate-env > .env.example
```

Before fetching remote data, always run the sanctioned env check via Bun. Do not use `Test-Path`, `Get-Content`, `cat .env.local`, or any other ad-hoc check.

```bash
bun run "<plugin-root>/scripts/remote-api.ts" check-env
```

Interpret the result:

- Exit 0 — at least one provider is fully configured. Proceed.
- Exit 1 with `envLocalExists: false` — report that `.env.local` is missing. Ask the user to copy `.env.example` to `.env.local` and fill in the values. Do NOT create the file yourself.
- Exit 1 with no providers configured — tell the user which keys are missing and ask them to fill those values, then re-run the skill.

Authentication or authorization failures (`401`, `403`, invalid credentials, PAT expired/revoked, permission-style `404`) are hard stops for remote analysis or review. Ask the user to provide valid access for the failing system before continuing.

## Multi-instance env configuration

Projects that use multiple instances of the same provider (e.g., two Jira tenants or github.com + GitHub Enterprise)
configure routing and env var mapping in `docs/profiles/team.yml`.

Default instances use standard env var names (backward compatible). Additional instances declare custom env var names
in their `env:` block — users pick their own env var names. Routing config lives in `team.yml`; `.env.local` carries
only credentials.

```yaml
# docs/profiles/team.yml — routing config
ticket_providers:
  - type: jira
    name: primary
    key_prefixes: ["PROJ", "CORE"]
    # omit env: → uses default keys (JIRA_BASE_URL, JIRA_PAT, JIRA_EMAIL)
  - type: jira
    name: external
    key_prefixes: ["EXT"]
    env:
      base_url: JIRA_EXT_BASE_URL
      pat: JIRA_EXT_PAT
      email: JIRA_EXT_EMAIL
```

```dotenv
# .env.local — credentials with natural names
JIRA_BASE_URL=https://company.atlassian.net
JIRA_PAT=xxx
JIRA_EMAIL=user@company.com
JIRA_EXT_BASE_URL=https://other.atlassian.net
JIRA_EXT_PAT=yyy
JIRA_EXT_EMAIL=user@other.com
```

When a target matches multiple instances (e.g., a Jira key prefix defined in two instances), the script returns a
hard error listing the candidates with explicit disambiguation commands. Single-instance setups do not need any
`team.yml` changes — existing scalar fields and env var names continue to work.
