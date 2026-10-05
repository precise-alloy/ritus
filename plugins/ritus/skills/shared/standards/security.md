# Security standard

A rubric for changes that hit a risk trigger below. Auth, billing, migrations, tenant isolation, infra config, and
shared contracts always get at least STANDARD process (the safety override). Every check under a trigger the change
hits is a hard gate: security defects rarely show up in tests, so done means each check holds, or the report says why
it does not apply.

## Triggers and checks

**Reads or writes user data**
- Every query on user data filters by its ownership key (`tenantId`, `orgId`, `userId`, ...).
- The ownership key comes from the authenticated session, never from the request body or query string.
- A client-supplied entity ID is checked against the session's ownership before it is used.

**Auth, sessions, tokens, permissions**
- Token or session verification runs in middleware, not inside handlers.
- Each endpoint checks its role or permission explicitly: authenticated does not mean authorized.
- Integration tokens and API credentials are encrypted at rest.

**Input crossing a boundary** (API, job or queue payload, webhook, file upload, CLI arguments and flags)
- Validated where it enters: required fields present, enum values checked explicitly (a CLI refuses a flag it
  doesn't know, in any position), uploads checked by MIME type, extension, and size.
- Never interpolated into SQL - use parameters or the ORM - and never passed to a shell.

**Renders user content**
- Escaped on output; no raw `innerHTML` or equivalent with untrusted content. Stored content that will be rendered as
  HTML is sanitized.

**Fetches a URL the user can influence**
- The target is checked against a configured allowlist (SSRF).

**Secrets, infra, or runtime config**
- Secrets live in environment variables or a secret store - never in code, git history, logs, errors, or responses.
- The application fails fast at startup when a required variable is missing.

**Changes state that matters** (billing, permissions, destructive or admin actions)
- The action is written to the audit log with `actorId`, `entityType`, `entityId`, `action`, `beforeSnapshot`, and
  `afterSnapshot`.
- Important records are versioned or snapshotted before they change, never silently overwritten.

**Migrations and shared contracts**
- The migration and contract rows in `engineering.md` and `testing.md` apply, and a migration states whether it can be
  rolled back.
