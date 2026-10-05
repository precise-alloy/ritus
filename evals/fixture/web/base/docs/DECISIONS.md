# Decisions

## D-001 - No runtime dependencies

The app uses browser ES modules and a small Node server. This keeps local startup predictable and avoids an install step for normal development.

## D-002 - Token-owned visual values

Colors, spacing, radius and type values are centralized in `src/styles/tokens.css`. Page CSS consumes custom properties so visual changes are reviewable in one place.

## D-003 - Server routes stay explicit

`scripts/serve.mjs` lists every page and API route. Unknown account pages return the same 404 treatment as any missing URL.
