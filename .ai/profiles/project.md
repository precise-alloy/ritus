# Project Profile

> Project-specific technical facts and conventions live here. Keep reusable workflow rules in `.ai/AGENTS.md` and
`.ai/workflows/`.

## Project identity

| Field            | Value                  |
|------------------|------------------------|
| Project          | `{{PROJECT_NAME}}`     |
| Primary language | `{{PRIMARY_LANGUAGE}}` |
| Framework        | `{{FRAMEWORK}}`        |

## Language policy

- Primary language: `{{PRIMARY_LANGUAGE}}`
- Docs and comments: English only.

## Source layout

<!-- Filled by repo-scan or project adoption. Keep paths project-specific. -->

| Area                        | Paths                          | Notes                                 |
|-----------------------------|--------------------------------|---------------------------------------|
| Business logic              | `{{BUSINESS_LOGIC_PATHS}}`     | Services, helpers, domain logic       |
| Web/API                     | `{{WEB_API_PATHS}}`            | Controllers, endpoints, views, routes |
| Models/contracts            | `{{MODEL_CONTRACT_PATHS}}`     | DTOs, models, shared contracts        |
| Integrations                | `{{INTEGRATION_PATHS}}`        | External systems and API clients      |
| Frontend/UI                 | `{{FRONTEND_PATHS}}`           | Components, scripts, styles           |
| Generated/ignored artifacts | `{{GENERATED_ARTIFACT_PATHS}}` | Do not edit directly                  |

## Documentation layout

<!-- Filled during setup or project adoption. (Repo-scan does not infer documentation layout.) -->

| Purpose        | Path                          |
|----------------|-------------------------------|
| Ticket reviews | `{{TICKET_REVIEW_DOCS_PATH}}` |
| Architecture   | `docs/ARCHITECTURE.md`        |
| Decisions      | `docs/DECISIONS.md`           |
| Lessons        | `docs/LESSONS.md`             |
| Module docs    | `docs/modules/`               |

## Requirement source precedence

When multiple requirement sources conflict, use this order unless the team profile says otherwise:

1. Explicit user instruction in the current conversation.
2. Latest authoritative ticket comments or discussion notes.
3. Ticket acceptance criteria.
4. Ticket description.
5. Existing review/task files.

If a comment contradicts or refines the ticket description, the comment takes precedence. Document the decision in the
review output.

## Authentication

<!-- Filled by repo-scan. -->

Auth pattern: `{{AUTH_PATTERN}}`

- Token verification: `{{AUTH_TOKEN_VERIFICATION}}`
- Tenant/workspace scoping: `{{AUTH_TENANT_SCOPING}}`
- Role/permission model: `{{AUTH_ROLE_MODEL}}`

## Error handling

<!-- Filled by repo-scan. -->

`{{ERROR_HANDLING_PATTERN}}`

## Testing

Full test policy: see `.ai/standards/testing-policy.md`.

<!-- Filled by repo-scan. -->

`{{TESTING_PATTERN}}`

## Test location conventions

<!-- Filled by repo-scan or project adoption. -->

```text
{{TEST_LOCATION_CONVENTIONS}}
```

## Build commands

<!-- Filled by repo-scan. -->

| Command             | What            |
|---------------------|-----------------|
| `{{BUILD_CMD}}`     | Build project   |
| `{{TYPECHECK_CMD}}` | Type check only |
| `{{TEST_CMD}}`      | Run tests       |
| `{{LINT_CMD}}`      | Lint            |

## Project-specific constraints

<!-- Rules specific to this project and not covered by reusable workflow rules or standards. -->

`{{PROJECT_CONSTRAINTS}}`
