# Settings

What setup records, where to look for it first, and what to ask when the repository doesn't say. Present what you
detected with its source for the user to confirm; ask the rest one at a time, each question with its default.

| Setting | Field | Detect from | Default |
|---|---|---|---|
| New or existing codebase | not stored; decides whether `repo-scan` runs next | Commits and source files exist | Existing |
| Project name | `project.yml` `project_name` - lowercase kebab-case, used in task files and commit scopes | The package manifest's name, else the folder name | The folder name |
| Team size | `team.yml` `team_size`: `solo`, `small` (2-5), `medium` (6-20), `large` (20+) | Distinct commit authors in the last 90 days - a hint to confirm, not an answer | Ask |
| Language and framework | `project.yml` `primary_language`, `framework` | Manifests and their dependencies | Ask |
| Git platform | `team.yml` `git_platform`: GitHub, GitLab, Azure DevOps, Bitbucket, other | The host of `git remote get-url origin` | GitHub |
| Git workflow | `team.yml` `git_flow`: `PR-based`, `trunk-based`, `gitflow` | A long-lived `develop` branch suggests gitflow | `PR-based` |
| Default base branch | `team.yml` `default_base_branch` | `git symbolic-ref refs/remotes/origin/HEAD`, else `main` or `master` | `main`; `develop` under gitflow |
| Plans folder | `project.yml` `documentation.ticket_reviews` - where `ticket-review` writes its plans (`<KEY>-review.md`) | An existing folder of `*-review.md` files | `docs/reviews` |
| Ticket systems | `team.yml` `ticket_providers`, `ticket_format` | Ticket keys in recent branch names and commit messages: `PROJ-123` is Jira; `#123` is GitHub Issues, or Azure DevOps work items when the remote is on Azure DevOps | `none` |
| Workflow owner | `team.yml` `workflow_owner`: `tech-lead` or `team` - who changes profiles and conventions | Nothing to detect | `team` |
| QA mode | `team.yml` `qa_mode`: `task` (a `.qa.md` per STANDARD or EPIC task, plus an EPIC summary in `docs/qa/`), `epic-only` (the EPIC summary only), `off` | Nothing to detect | `off` |
| AI tools | `runtime.yml` `ai_tools` | `CLAUDE_PLUGIN_ROOT` set means Claude Code; `PLUGIN_ROOT` set means GitHub Copilot | Ask |

For a **solo** team, don't ask about the git platform, ticket systems, or workflow owner: use what the remote shows
(else GitHub), no ticket systems, and `developer` as the owner.

## Ticket systems

- Record each system as `{type: jira | github | ado, name: default}`. `ticket_format` is the first system's key shape -
  `PROJ-123` for Jira, `#123` for GitHub, `12345` for Azure DevOps - or `none`.
- GitHub Issues' short `#123` refs need `GITHUB_REPO_URL` in `.ritus/.env.local`; full URLs work without it.
- For each system, ask whether there are several instances of it (two Jira sites, several Azure DevOps orgs). If so,
  ask each instance's name and, for Jira, its key prefixes. The first instance uses the default variable names from
  `.ritus/.env.example`; each other one maps only the settings that differ to its own variables under `env` - a shared
  token can keep the default. The keys are `base_url`, `pat`, `email` for Jira; `pat`, `org`, `project` for Azure
  DevOps; `token`, `repo_url`, and `api_base_url` (Enterprise) for GitHub:

```yaml
ticket_providers:
  - {type: jira, name: primary, key_prefixes: ["AMPS"]}
  - {type: jira, name: maintenance, key_prefixes: ["AMP"], env: {base_url: JIRA_AMP_BASE_URL}}
```

## Writing the values

- YAML: quote every string value, as the templates do. Unquoted, `ticket_format: #123` is a comment and `qa_mode: off`
  a boolean.
- Fill empty fields only. A value already in the profiles was set by someone; change it only when the user changes it
  in this run.
