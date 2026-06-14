# Team Profile

> Team process, ownership, ticket, branch, and PR conventions live here. Keep technical project facts in
`.ai/profiles/project.md`.

## Team config

<!-- Filled by setup wizard. -->

| Field              | Value                         |
|--------------------|-------------------------------|
| Team size          | `{{TEAM_SIZE}}`               |
| Git platform       | `{{GIT_PLATFORM}}`            |
| Git workflow       | `{{GIT_FLOW}}`                |
| Workflow owner     | `{{WORKFLOW_OWNER}}`          |
| Ticket format      | `{{TICKET_FORMAT}}`           |
| EPIC memory expiry | `{{MEMORY_EXPIRY_DAYS}}` days |
| QA mode            | `{{QA_MODE}}`                 |

## Branch conventions

```text
{{BRANCH_FORMAT}}
```

## tasks/ path convention

```text
{{TASKS_PATH_CONVENTION}}
```

When creating a task file, the branch slug = current git branch name with `/` replaced by `-`.

## Pull request requirements

- Title must match commit convention: `type(scope): subject`.
- Body must include: what changed, why, DONE WHEN conditions verified.
- Required reviewers: `{{PR_REVIEWERS}}`.
- Link ticket if `{{TICKET_FORMAT}}` is not `none`.
- No PR merges with failing CI.

## Review defaults

| Field               | Value                                                                     |
|---------------------|---------------------------------------------------------------------------|
| Default base branch | `{{DEFAULT_BASE_BRANCH}}`                                                 |
| Local review scopes | committed branch diff, staged changes, unstaged changes, full worktree    |
| Review verdict bias | Request changes unless critical paths and requirements are proven correct |

## Traceability policy

<!-- Example policies: ticket ID in commit message only, ticket ID in task/review docs, or ticket ID comments for special workarounds only. -->

`{{TRACEABILITY_POLICY}}`

## Stakeholders and escalation

Stakeholders live in `.ai/standards/stakeholders.md`. Load that file when requirements, architecture, integration, QA,
or approval ownership is unclear.
