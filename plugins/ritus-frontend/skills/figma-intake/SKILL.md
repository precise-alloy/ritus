---
name: figma-intake
description: Use during ticket-review after task-generation when frontend UI tasks may have a developer-supplied Figma design URL to record for downstream implementation and deterministic verification.
argument-hint: The task files task-generation produced; figma-intake asks the developer for the ticket's Figma design URL.
user-invocable: false
---

# figma-intake

Record one node-scoped Figma URL and its task mapping. Do not build code or write back to Figma.

Run after task-generation has written the task files. If the developer says there is no design, write no marker and
report `SKIPPED`. If the design URL cannot identify an accessible node, report `BLOCKED`; do not guess a node or create
an alternate design artifact.

## Workflow

Create this TODO when starting and mark each item as it completes:

```markdown
- [ ] Identify the UI task files and each task's surface and implementation target.
- [ ] Ask for one node-scoped `figma.com/design/...?node-id=...` URL; no design means SKIPPED.
- [ ] Validate `node-id` and normalize `-` to `:` for tool calls; if it is missing, ask once, then report BLOCKED if unavailable.
- [ ] Append one URL-only `figma:` block to each UI task's CONTEXT without changing unrelated content.
- [ ] Report the marked tasks and URL, or SKIPPED/BLOCKED.
```

Do not capture, download, create, or commit a Figma image. Humans inspect the URL directly. Downstream agents use the
URL with structured Figma MCP tools.

## Marker

Append this block under each UI task's `## CONTEXT`:

```yaml
figma:
  url: <node-scoped Figma design URL>
  surface: <route-or-component>
  target: <implementation target plus create-or-extend intent>
  breakpoint: <design frame width only when known>
```

Use the same URL for tasks that share the same design selection, but preserve each task's own `surface` and `target`.
Omit `breakpoint` when unknown. It is optional design metadata and never becomes a runtime viewport automatically.

## Handoff

- `DONE`: markers written; report the marked UI tasks and node-scoped URL.
- `SKIPPED`: no design exists.
- `BLOCKED`: the URL lacks a usable node, Figma access is unavailable, or the node cannot be reached.
