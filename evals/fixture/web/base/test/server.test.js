import test from 'node:test';
import assert from 'node:assert/strict';
import { startServer } from '../scripts/serve.mjs';

async function withServer(run) {
  const { server, port } = await startServer({ port: 0 });
  try {
    await run(`http://localhost:${port}`);
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
}

async function responseFor(base, path) {
  return fetch(`${base}${path}`, { redirect: 'manual' });
}

test('root redirects to accounts', async () => {
  await withServer(async (base) => {
    const response = await responseFor(base, '/');
    assert.equal(response.status, 302);
    assert.equal(response.headers.get('location'), '/accounts');
  });
});

test('page routes return html', async () => {
  await withServer(async (base) => {
    for (const path of ['/accounts', '/accounts/checking', '/accounts/savings', '/accounts/travel', '/transfer']) {
      const response = await responseFor(base, path);
      assert.equal(response.status, 200, path);
      assert.match(response.headers.get('content-type'), /text\/html/);
    }
  });
});

test('account api returns three accounts', async () => {
  await withServer(async (base) => {
    const response = await responseFor(base, '/api/accounts');
    assert.equal(response.status, 200);
    const accounts = await response.json();
    assert.equal(accounts.length, 3);
  });
});

test('travel account api returns no transactions', async () => {
  await withServer(async (base) => {
    const response = await responseFor(base, '/api/accounts/travel');
    assert.equal(response.status, 200);
    const account = await response.json();
    assert.deepEqual(account.transactions, []);
  });
});

test('missing routes return 404 html', async () => {
  await withServer(async (base) => {
    for (const path of ['/accounts/nope', '/missing']) {
      const response = await responseFor(base, path);
      assert.equal(response.status, 404, path);
      assert.match(response.headers.get('content-type'), /text\/html/);
    }
  });
});

test('static routes return expected content types', async () => {
  await withServer(async (base) => {
    const css = await responseFor(base, '/src/styles/tokens.css');
    assert.equal(css.status, 200);
    assert.match(css.headers.get('content-type'), /text\/css/);
    const js = await responseFor(base, '/src/main.js');
    assert.equal(js.status, 200);
    assert.match(js.headers.get('content-type'), /text\/javascript/);
  });
});
