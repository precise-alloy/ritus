---
name: security
description: Loaded automatically by execute-task and verify-task when changes touch auth, billing, migration, tenant isolation, infra, or shared contracts — security checklist. Do not invoke standalone unless the user specifically asks for a security review
argument-hint: Provide the changed auth, billing, migration, tenant, infra, or contract areas to review
---

# Security Standards

## When to use

Load this skill for any task touching auth, billing, migrations, tenant isolation, infra config, or shared contracts.
All checklist items are hard gates — must pass before reporting done.

## Tenant / user data isolation

- Every DB query touching user data must filter by the ownership key (e.g. `tenantId`, `orgId`, `userId`).
- The ownership key must come from the authenticated session — never from the request body.
- Data retrieval must scope to the authenticated entity — no cross-tenant data access.

## Input validation

- Validate at system boundaries: API endpoints, job/queue inputs, webhook handlers.
- Never trust client-supplied entity IDs without verifying ownership against the session.
- Validate enum values explicitly before use in DB queries or business logic.
- File uploads: validate MIME type + extension + max size before processing.

## Authentication and authorization

- Token/session verification in middleware — not inside route handlers.
- Role checks are explicit per endpoint — "authenticated" does not imply "authorized."
- Integration tokens and API credentials must be encrypted at rest before storage.

## Secret handling

- No secrets in: source code, git history, logs, error messages, or API responses.
- All secrets live in environment variables only — never in code or DB plaintext.
- Application validates required env vars at startup — fail fast if missing.

## Injection prevention

- No string interpolation in DB queries — parameterized queries or ORM always.
- No user input passed to shell commands.
- User-supplied content stored in DB must be sanitized if it will be rendered as HTML.

## Output encoding

- All user-generated content rendered in frontend must be HTML-escaped.
- No raw `innerHTML` with untrusted content.

## SSRF (Server-Side Request Forgery) prevention

- External URL fetching must validate against a configured allowlist.
- No arbitrary URL fetch from user-supplied input without validation.

## Audit logging

- Write to an audit log for: state-changing actions, permission changes, destructive operations.
- Required fields: `actorId`, `entityType`, `entityId`, `action`, `beforeSnapshot`, `afterSnapshot`.
- Never silently overwrite important records — version or snapshot before overwriting.

## Checklist (required for all safety override changes)

- [ ] Tenant/ownership scoping verified on all new queries
- [ ] No new secrets in code or logs
- [ ] Auth/authz enforced in middleware, not handler
- [ ] Sensitive fields encrypted before persistence
- [ ] Audit log entry created for state changes
- [ ] Input validation present at system boundary
- [ ] No raw SQL string interpolation
- [ ] Classified STANDARD or above — no TRIVIAL/SIMPLE for safety override changes

## Next

This is a companion skill — it does not chain to another skill. Return to the parent skill (execute-task or
verify-task) that loaded it.
