# Frontend

Confirmed for TinyLedger Web.

## Dev server

- Command: `npm run dev`.
- Base URL: `http://localhost:4173/`.
- The port is `4173` from `package.json` `config.port`; this is the URL printed by `npm run dev`.

## Viewports and breakpoints

- Breakpoints: `640px` and `1024px`.
- Supported viewport widths: `375px` through `1440px`.
- Check the narrowest supported width, the common mid-widths, both sides of changed breakpoints, and desktop width.

## Design system

- Tokens and CSS variables: `src/styles/tokens.css`.
- Components: `src/components/`.
- Reuse existing tokens and components before adding page-specific values.

## Authentication and state

- Login: none. The app is an internal staff demo with read-only seed data.
- Seed data is under `data/accounts.json`.

## Browser checks

- Use `playwright-cli` through the project's Playwright dependency.
- Serve the app with `npm run dev` over HTTP before browser checks; do not use `file:` URLs.
- Accessibility target: WCAG 2.2 AA, including visible labels, keyboard/focus behavior, axe scope checks, and contrast for changed UI.
