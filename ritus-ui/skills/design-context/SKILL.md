---
name: design-context
description: Parses a Figma reference, pulls frames and metadata via the Figma MCP, and summarizes them as visual acceptance criteria the ritus workflow can consume, degrading gracefully when the Figma MCP is unavailable
user-invocable: false
---

# Design Context

## When to use

This skill is exposed by ritus-ui so the ritus workflow can invoke it when available, during intake of Frontend/UI
requirements that reference a Figma design. It pulls the referenced frames as visual acceptance criteria the workflow
can fold into its review document and tasks. The workflow-side wiring that decides when to call it is decided
separately.

## Prerequisite and availability check

- This skill requires the Figma MCP tools together with access to the referenced Figma file.
- Check availability first: confirm the Figma MCP tools are present in the session and the referenced file is
  reachable.
- When the Figma MCP tools or the referenced file are unavailable, skip with a warning and let intake continue,
  mirroring the build/test/lint skip pattern (a missing capability is a skip-with-warning, and stays a soft skip
  rather than a hard failure).
- Report the skip clearly so the parent skill records that design context was not pulled.

## Steps

1. Parse the Figma reference from the requirement to resolve the file key and the target node or frame ids.
2. Pull the frames and their metadata via the Figma MCP: the frame images, layout structure, text content, and the
   design tokens (colors, spacing, and typography) the frames reference.
3. Summarize the frames as visual acceptance criteria: the layout and states each screen shows, the key components,
   and the token values a build should match.
4. Emit the design summary in a form the ritus workflow can consume when it invokes this skill: a concise set of
   visual acceptance criteria the review document and tasks can reference directly.
5. Include the source frame ids and any evidence image paths so the criteria trace back to the design.

## Handoff

- **Report:** the visual acceptance criteria with their source frame ids and evidence paths applied to the parent
  skill's work, or the skip-with-warning notice when the Figma MCP is unavailable.
