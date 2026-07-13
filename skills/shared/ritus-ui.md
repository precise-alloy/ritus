# ritus-ui Integration

`ritus-ui` is the optional, opt-in companion plugin that adds browser-driven frontend/UI capabilities to the ritus
workflow. Core ritus references its skills by name and works with or without it: when the plugin is enabled its
skills run; when it is disabled core ritus behaves exactly as before.

## Skills

`ritus-ui` contributes these skills, each invoked by name:

- `ui-preview` - drive the change in a real browser, capture evidence at each state, and assess it against intent.
- `e2e-generator` - generate and run committed Playwright end-to-end specs for a user journey.
- `visual-regression` - compare routes against stored screenshot baselines.
- `a11y-audit` - run an axe-core accessibility audit against rendered routes.
- `design-context` - pull Figma design references in as visual acceptance criteria.

## Invoke by name

Invoke a `ritus-ui` skill by name and let the runtime resolve it from the enabled plugin. The skill and its
Playwright MCP tools load into the session from the plugin, so the session is the place to read availability.

## Availability

A `ritus-ui` skill is available when the skill and its Playwright MCP tools are present in the current session.
Invoke it when they are present. When they are absent, the plugin is disabled or its browser capability is
unavailable, so skip that step with a warning and continue - mirroring the build/test/lint skip pattern. Core ritus
stays exactly as before when the plugin is disabled.
