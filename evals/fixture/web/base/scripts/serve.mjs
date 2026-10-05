import { createServer } from 'node:http';
import { appendFile, mkdir, readFile } from 'node:fs/promises';
import { extname, join, normalize, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(fileURLToPath(new URL('..', import.meta.url)));
const CONTENT_TYPES = new Map([
  ['.html', 'text/html; charset=utf-8'],
  ['.css', 'text/css; charset=utf-8'],
  ['.js', 'text/javascript; charset=utf-8'],
  ['.json', 'application/json; charset=utf-8'],
]);

export function resolvePort(argv = process.argv.slice(2), env = process.env) {
  const portIndex = argv.indexOf('--port');
  if (portIndex !== -1 && argv[portIndex + 1]) {
    return Number(argv[portIndex + 1]);
  }
  if (env.PORT) {
    return Number(env.PORT);
  }
  if (env.npm_package_config_port) {
    return Number(env.npm_package_config_port);
  }
  return 4173;
}

async function readAccounts() {
  return JSON.parse(await readFile(join(ROOT, 'data', 'accounts.json'), 'utf8'));
}

async function sendFile(response, relativePath, status = 200) {
  const safePath = normalize(relativePath).replace(/^(\.\.(?:\\|\/|$))+/, '');
  const fullPath = resolve(ROOT, safePath);
  if (!fullPath.startsWith(ROOT)) {
    response.writeHead(404, { 'content-type': 'text/html; charset=utf-8' });
    response.end('Not found');
    return;
  }
  const content = await readFile(fullPath);
  response.writeHead(status, { 'content-type': CONTENT_TYPES.get(extname(fullPath)) ?? 'application/octet-stream' });
  response.end(content);
}

async function handleRequest(request, response) {
  const url = new URL(request.url ?? '/', 'http://localhost');
  if (url.pathname === '/') {
    response.writeHead(302, { location: '/accounts' });
    response.end();
    return;
  }
  if (url.pathname === '/api/accounts') {
    response.writeHead(200, { 'content-type': 'application/json; charset=utf-8' });
    response.end(JSON.stringify(await readAccounts()));
    return;
  }
  if (url.pathname.startsWith('/api/accounts/')) {
    const id = url.pathname.split('/').pop();
    const account = (await readAccounts()).find((item) => item.id === id);
    if (account) {
      response.writeHead(200, { 'content-type': 'application/json; charset=utf-8' });
      response.end(JSON.stringify(account));
      return;
    }
    response.writeHead(404, { 'content-type': 'application/json; charset=utf-8' });
    response.end(JSON.stringify({ error: 'not_found' }));
    return;
  }
  if (url.pathname.startsWith('/src/')) {
    await sendFile(response, url.pathname.slice(1));
    return;
  }
  if (['/accounts', '/accounts/checking', '/accounts/savings', '/accounts/travel', '/transfer'].includes(url.pathname)) {
    await sendFile(response, 'public/index.html');
    return;
  }
  await sendFile(response, 'public/404.html', 404);
}

export function createTinyLedgerServer() {
  return createServer((request, response) => {
    handleRequest(request, response).catch(() => {
      response.writeHead(500, { 'content-type': 'text/html; charset=utf-8' });
      response.end('Server error');
    });
  });
}

export async function startServer({ port = 4173, host = 'localhost' } = {}) {
  const server = createTinyLedgerServer();
  await new Promise((resolveListen) => server.listen(port, host, resolveListen));
  const address = server.address();
  const actualPort = typeof address === 'object' && address ? address.port : port;
  await mkdir(join(ROOT, '.cache'), { recursive: true });
  await appendFile(join(ROOT, '.cache', 'dev-server.pids'), `${process.pid} ${actualPort}\n`);
  return { server, port: actualPort };
}

const invokedPath = process.argv[1] ? fileURLToPath(import.meta.url) === resolve(process.argv[1]) : false;
if (invokedPath) {
  const port = resolvePort();
  const { port: actualPort } = await startServer({ port });
  process.stdout.write(`TinyLedger Web running at http://localhost:${actualPort}/\n`);
}
