# Architecture - TinyLedger Web

```text
scripts/serve.mjs -> public/index.html -> src/main.js
                                      -> src/components/card.js
                                      -> src/lib/accounts.js
                                      -> src/lib/money.js
scripts/serve.mjs -> data/accounts.json
```

- The server owns routing, static file responses and JSON account endpoints.
- Browser pages are rendered from `src/main.js` using reusable components and tokenized CSS.
- Account data is read-only seed data stored in `data/accounts.json`.

## Patterns

### Add a page route

1. Add the server route in `scripts/serve.mjs` if it needs a clean URL.
2. Render the page in `src/main.js` with one `h1` and the shared shell.
3. Add route coverage in `test/server.test.js`.
4. Check the page at 375px, 768px and 1280px.

### Add reusable UI

1. Put the component in `src/components/`.
2. Use values from `src/styles/tokens.css`; do not introduce raw color values elsewhere.
3. Give controls and regions accessible names before adding visual polish.
