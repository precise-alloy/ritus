# Design system

Build UI with the client's design system before adding new styling. The goal is not to make a page look close by eye; it
is to reuse the tokens, components, and assets the project already treats as its source of truth.

## Find it

Look for these sources, then record what you find in `docs/FRONTEND.md`:

- CSS custom properties in global styles, theme files, component styles, or generated CSS;
- Tailwind `@theme`, Tailwind config, or compatibility `@config` files;
- DTCG, Style Dictionary, or other token files;
- component libraries, shared UI folders, examples, stories, and Storybook;
- a Figma library, Code Connect mapping, or design-system search when an MCP exposes one.

Use the project's names for tokens and components. If there are several layers, record the order that project code uses:
for example, component props before utility classes, semantic tokens before raw palette tokens.

## Build with it

- Reuse an existing component with the same role - purpose, semantics, interaction - before writing a new one.
- Extend a component through its documented props, variants, slots, or composition pattern before editing its internals.
- Use tokens for colour, spacing, typography, radius, shadow, motion, and breakpoints.
- Do not add a raw hex, rgb, px, rem, font family, font weight, shadow, or duration where a token exists.
- Keep assets in the project's normal asset location and naming scheme.

When no token exists for a required value, name the source of the value in the task or report and keep the change local.
Do not create a design-system token unless the task asks for that system change.

## Check it

A UI implementation using the design system is checked in three ways:

- The rendered value matches the intended token or component output. Compare computed values, not source syntax.
- The diff adds no raw value where an existing token covers the same meaning.
- Existing components are not rewritten to fit one task when their props, variants, or composition already cover it.

If the design system and a design disagree, report the conflict with the token/component name and the design value. Do
not silently choose a raw value over the system.

## Optional design skills

Third-party design skills can help projects that lack a design system, but they are optional and never required. This
standard depends on the client's own design sources, not on any one design-generation tool.
