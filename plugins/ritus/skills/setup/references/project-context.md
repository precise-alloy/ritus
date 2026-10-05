# Rendering docs/PROJECT_CONTEXT.md

`docs/PROJECT_CONTEXT.md` is rendered from the three profiles into the structure of the template `sync` creates. Every
skill reads it, so re-render it whenever a profile changes - `setup` and `repo-scan` both do. Keep the sections the
user added and anything outside the placeholders as it is.

| Placeholder | From |
|---|---|
| `{{PROJECT_NAME}}`, `{{PRIMARY_LANGUAGE}}`, `{{FRAMEWORK}}` | `project.yml` `project_name`, `primary_language`, `framework` |
| `{{BUSINESS_LOGIC_PATHS}}`, `{{WEB_API_PATHS}}`, `{{MODEL_CONTRACT_PATHS}}`, `{{INTEGRATION_PATHS}}`, `{{FRONTEND_PATHS}}`, `{{GENERATED_ARTIFACT_PATHS}}` | `project.yml` `source_layout`: `business_logic`, `web_api`, `models`, `integrations`, `frontend`, `generated` |
| `{{BUILD_CMD}}`, `{{TYPECHECK_CMD}}`, `{{TEST_CMD}}`, `{{LINT_CMD}}` | `project.yml` `build_commands`: `build`, `typecheck`, `test`, `lint` |
| `{{AUTH_PATTERN}}`, `{{AUTH_TOKEN_VERIFICATION}}`, `{{AUTH_TENANT_SCOPING}}`, `{{AUTH_ROLE_MODEL}}` | `project.yml` `authentication`: `pattern`, `token_verification`, `tenant_scoping`, `role_model` |
| `{{ERROR_HANDLING_PATTERN}}` | `project.yml` `error_handling` |
| `{{TESTING_PATTERN}}`, `{{TEST_LOCATION_CONVENTIONS}}` | `project.yml` `testing`: `pattern`, `location_conventions` |
| `{{TICKET_REVIEW_DOCS_PATH}}` | `project.yml` `documentation.ticket_reviews` |
| `{{MODULE_MAP}}` | `project.yml` `module_map`, as a table of each entry's `kebab_case_name` and `human_phrase` |
| `{{PROJECT_CONSTRAINTS}}` | `project.yml` `project_constraints`, one bullet each |
| `{{TEAM_SIZE}}`, `{{GIT_PLATFORM}}`, `{{GIT_FLOW}}`, `{{WORKFLOW_OWNER}}`, `{{TICKET_FORMAT}}`, `{{QA_MODE}}` | `team.yml`: `team_size`, `git_platform`, `git_flow`, `workflow_owner`, `ticket_format`, `qa_mode` |
| `{{MEMORY_EXPIRY_DAYS}}`, `{{BRANCH_FORMAT}}`, `{{TASKS_PATH_CONVENTION}}`, `{{PR_REVIEWERS}}`, `{{DEFAULT_BASE_BRANCH}}`, `{{TRACEABILITY_POLICY}}` | `team.yml`: `memory_expiry_days`, `branch_format`, `tasks_path_convention`, `pr_reviewers`, `default_base_branch`, `traceability_policy` |
| `{{TICKET_PROVIDERS}}` | `team.yml` `ticket_providers`, as `type:name (prefixes: X, Y)`, comma-separated; the comment above its row in the template says when to uncomment it |
| `{{AI_TOOLS}}` | `runtime.yml` `ai_tools` |

A field that is still empty renders as `not set`, so a reader knows it is unknown rather than seeing a placeholder.

A file rendered by an older version may carry a `## Model routing` section. Drop it: Ritus no longer picks models, and
an agent reading the old tables would follow them.
