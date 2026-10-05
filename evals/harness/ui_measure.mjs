import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { join } from 'node:path';

const input = JSON.parse(await readFile(process.argv[2], 'utf8'));
const modules = process.env.UI_MODULES;
if (!modules) {
  throw new Error('UI_MODULES is required');
}
const require = createRequire(join(modules, 'package.json'));
const { chromium } = require('playwright');
const axePath = require.resolve('axe-core/axe.min.js');

function cardProbeWrapper() {
  const original = '/src/components/card.js?ui-probe-orig';
  return `import * as __uiProbeOriginal from '${original}';
export * from '${original}';
export default __uiProbeOriginal.default;
export function card(...args) {
  const result = __uiProbeOriginal.card(...args);
  if (result instanceof Element) {
    result.setAttribute('data-ui-probe-card', '');
  }
  return result;
}
`;
}

const cardWrapperSource = cardProbeWrapper();

const widths = [375, 768, 1280];
const routes = ['/accounts', '/accounts/checking', '/accounts/travel', '/transfer'];
const NAVIGATION_TIMEOUT = 5000;
const READY_TIMEOUT = 2000;
const SCRIPT_TIMEOUT = 5000;
const EVALUATE_TIMEOUT = 3000;
const AXE_TIMEOUT = 7000;

function timeoutError(label, milliseconds) {
  return new Error(`${label} timed out after ${milliseconds}ms`);
}

function withTimeout(promise, milliseconds, label) {
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(timeoutError(label, milliseconds)), milliseconds);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}

function errorMessage(error) {
  return error && error.message ? error.message : String(error);
}

function errorMeasurement(error) {
  return { error: errorMessage(error) };
}

function emptyRoute() {
  return {};
}

const out = {
  routes: emptyRoute(),
  overflow: emptyRoute(),
  axe: emptyRoute(),
  console: emptyRoute(),
  summary_card: {},
  empty_state: emptyRoute(),
  transfer_layout: {},
};

function visible(el) {
  if (!el) return false;
  const style = getComputedStyle(el);
  const box = el.getBoundingClientRect();
  return style.visibility !== 'hidden' && style.display !== 'none' && box.width > 0 && box.height > 0;
}

function edgeColorVisible(style, side) {
  const width = Number.parseFloat(style.getPropertyValue(`border-${side}-width`));
  const color = style.getPropertyValue(`border-${side}-color`);
  const borderStyle = style.getPropertyValue(`border-${side}-style`);
  return width > 0 && borderStyle !== 'none' && !/rgba\([^)]*,\s*0\s*\)/.test(color) && color !== 'transparent';
}

function hasPaint(el) {
  const style = getComputedStyle(el);
  const bg = style.backgroundColor;
  return !/rgba\([^)]*,\s*0\s*\)/.test(bg) && bg !== 'transparent'
    || ['top', 'right', 'bottom', 'left'].some((side) => edgeColorVisible(style, side));
}

function boxOf(el) {
  if (!el) return null;
  const rect = el.getBoundingClientRect();
  return { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom, width: rect.width, height: rect.height };
}

function blockBox(el, stop) {
  let node = el;
  while (node && node !== stop && getComputedStyle(node).display === 'inline') {
    node = node.parentElement;
  }
  return node || el;
}

function textLeafMatch(root, exact) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
  const all = [];
  let node = walker.currentNode;
  while (node) {
    if (node.textContent.trim() === exact && ![...node.children].some((child) => child.textContent.trim() === exact)) {
      all.push(node);
    }
    node = walker.nextNode();
  }
  return all;
}

function elementTextMatches(root, pattern) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
  let node = walker.currentNode;
  while (node) {
    if (pattern.test(node.textContent.trim()) && ![...node.children].some((child) => pattern.test(child.textContent.trim()))) {
      return node;
    }
    node = walker.nextNode();
  }
  return null;
}

function measureSummaryCard() {
  const main = document.querySelector('main');
  if (!main) return { found: false, reason: 'no main found' };
  const labels = textLeafMatch(main, 'Total balance').filter(visible);
  if (labels.length === 0) return { found: false, label_count: 0, reason: "no 'Total balance' text found" };
  const label = labels[0];
  const money = /^-?\$\d{1,3}(,\d{3})*\.\d{2}$/;
  let container = label.parentElement;
  while (container && container !== main) {
    const value = elementTextMatches(container, money);
    if (value && value !== label && hasPaint(container)) {
      const labelBoxEl = blockBox(label, container);
      const valueBoxEl = blockBox(value, container);
      const cStyle = getComputedStyle(container);
      const lStyle = getComputedStyle(label);
      const vStyle = getComputedStyle(value);
      const cBox = boxOf(container);
      const lBox = boxOf(labelBoxEl);
      const vBox = boxOf(valueBoxEl);
      const inner = {
        left: cBox.left + Number.parseFloat(cStyle.borderLeftWidth),
        top: cBox.top + Number.parseFloat(cStyle.borderTopWidth),
        right: cBox.right - Number.parseFloat(cStyle.borderRightWidth),
        bottom: cBox.bottom - Number.parseFloat(cStyle.borderBottomWidth),
      };
      const mainStyle = getComputedStyle(main);
      const mainBox = boxOf(main);
      const content = {
        left: mainBox.left + Number.parseFloat(mainStyle.borderLeftWidth) + Number.parseFloat(mainStyle.paddingLeft),
        right: mainBox.right - Number.parseFloat(mainStyle.borderRightWidth) - Number.parseFloat(mainStyle.paddingRight),
      };
      const labelled = container.getAttribute('aria-labelledby');
      const labelledEl = labelled ? document.getElementById(labelled) : null;
      return {
        found: true,
        label_count: labels.length,
        label_value_same_block: labelBoxEl === valueBoxEl,
        insets: {
          top: lBox.top - inner.top,
          left: Math.min(lBox.left, vBox.left) - inner.left,
          bottom: inner.bottom - vBox.bottom,
          right_intrusion: Math.max(lBox.right, vBox.right) - (inner.right - 16),
        },
        gap: vBox.top - lBox.bottom,
        radius: [cStyle.borderTopLeftRadius, cStyle.borderTopRightRadius, cStyle.borderBottomRightRadius, cStyle.borderBottomLeftRadius],
        background: cStyle.backgroundColor,
        borders: ['top', 'right', 'bottom', 'left'].map((side) => ({
          width: cStyle.getPropertyValue(`border-${side}-width`),
          style: cStyle.getPropertyValue(`border-${side}-style`),
          color: cStyle.getPropertyValue(`border-${side}-color`),
        })),
        label_style: { fontSize: lStyle.fontSize, lineHeight: lStyle.lineHeight, fontWeight: lStyle.fontWeight, color: lStyle.color },
        value_style: { fontSize: vStyle.fontSize, lineHeight: vStyle.lineHeight, fontWeight: vStyle.fontWeight, color: vStyle.color },
        value_text: value.textContent.trim(),
        content_column: content,
        container_edges: { left: cBox.left, right: cBox.right },
        component_signature: (() => {
          let node = container;
          while (node && node !== main) {
            if (node.hasAttribute('data-ui-probe-card')) return true;
            node = node.parentElement;
          }
          return false;
        })(),
      };
    }
    container = container.parentElement;
  }
  return { found: false, label_count: labels.length, reason: 'no painted container with a money value found' };
}

function measureEmptyState(route) {
  const main = document.querySelector('main');
  if (!main) return { reason: 'no main found' };
  const message = [...main.querySelectorAll('*')].find((el) => /^No transactions yet\.?$/.test(el.textContent.trim()));
  const link = [...main.querySelectorAll('a')].find((el) => new URL(el.href, location.href).pathname === '/transfer');
  const tables = [...main.querySelectorAll('table')].filter(visible);
  const rows = tables.map((table) => table.querySelectorAll('tbody tr').length);
  if (route === '/accounts/travel') {
    return { message_visible: !!message && visible(message), link_visible: !!link && visible(link), visible_tables: tables.length };
  }
  return { visible_tables: tables.length, tbody_rows: rows };
}

function measureTransferLayout() {
  const main = document.querySelector('main');
  if (!main) return { found: false, reason: 'no main found' };
  const form = main.querySelector('form');
  const headings = textLeafMatch(main, 'Fee preview').filter(visible);
  if (!form || headings.length === 0) {
    return { found: false, reason: !form ? 'no form found' : "no 'Fee preview' text found", form: boxOf(form) };
  }
  let panel = headings[0].parentElement;
  while (panel && panel !== main && !hasPaint(panel)) {
    panel = panel.parentElement;
  }
  if (!panel || panel === main) return { found: false, reason: 'no painted fee preview panel found', form: boxOf(form) };
  return { found: true, form: boxOf(form), panel: boxOf(panel) };
}


const browserMeasureSource = [
  visible,
  edgeColorVisible,
  hasPaint,
  boxOf,
  blockBox,
  textLeafMatch,
  elementTextMatches,
  measureSummaryCard,
  measureEmptyState,
  measureTransferLayout,
].map((fn) => fn.toString()).join('\n')
  + '\nwindow.__measureSummaryCard = measureSummaryCard;'
  + '\nwindow.__measureEmptyState = measureEmptyState;'
  + '\nwindow.__measureTransferLayout = measureTransferLayout;';

const browser = await chromium.launch({ headless: true });
try {
  for (const route of routes) {
    out.routes[route] = {};
    out.overflow[route] = {};
    out.axe[route] = {};
    out.console[route] = {};
    if (route === '/accounts/travel' || route === '/accounts/checking') out.empty_state[route] = {};
    for (const width of widths) {
      const context = await browser.newContext({ viewport: { width, height: 800 } });
      const messages = [];
      try {
        await context.route('**/src/components/card.js*', async (route) => {
          const url = new URL(route.request().url());
          if (url.searchParams.has('ui-probe-orig')) {
            await route.continue();
            return;
          }
          await route.fulfill({ status: 200, contentType: 'text/javascript', body: cardWrapperSource });
        });
        const page = await context.newPage();
        page.setDefaultTimeout(EVALUATE_TIMEOUT);
        page.setDefaultNavigationTimeout(NAVIGATION_TIMEOUT);
        page.on('console', (msg) => { if (msg.type() === 'error') messages.push({ type: 'console', text: msg.text() }); });
        page.on('pageerror', (error) => messages.push({ type: 'pageerror', text: error.message }));
        page.on('response', (response) => { if (response.status() >= 400) messages.push({ type: 'response', url: response.url(), status: response.status() }); });
        const response = await withTimeout(page.goto(new URL(route, input.baseUrl).toString(), { waitUntil: 'networkidle', timeout: NAVIGATION_TIMEOUT }), NAVIGATION_TIMEOUT + 500, `${route}@${width} navigation`);
        await withTimeout(page.evaluate(() => document.fonts.ready), READY_TIMEOUT, `${route}@${width} document.fonts.ready`);
        out.routes[route][width] = {
          status: response ? response.status() : null,
          h1: await page.locator('h1').first().textContent({ timeout: EVALUATE_TIMEOUT }).catch(() => null),
        };
        out.overflow[route][width] = await withTimeout(page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth), EVALUATE_TIMEOUT, `${route}@${width} overflow evaluate`);
        await withTimeout(page.addScriptTag({ path: axePath }), SCRIPT_TIMEOUT, `${route}@${width} axe injection`);
        await withTimeout(page.addScriptTag({ content: browserMeasureSource }), SCRIPT_TIMEOUT, `${route}@${width} measurement injection`);
        const axe = await withTimeout(page.evaluate(async () => window.axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'] } })), AXE_TIMEOUT, `${route}@${width} axe run`);
        out.axe[route][width] = axe.violations.map((violation) => ({ id: violation.id, impact: violation.impact, node_count: violation.nodes.length, first_target: violation.nodes[0]?.target?.join(' ') ?? '' }));
        if (route === '/accounts') out.summary_card[width] = await withTimeout(page.evaluate(() => window.__measureSummaryCard()), EVALUATE_TIMEOUT, `${route}@${width} summary_card evaluate`);
        if (route === '/accounts/travel' || route === '/accounts/checking') out.empty_state[route][width] = await withTimeout(page.evaluate((value) => window.__measureEmptyState(value), route), EVALUATE_TIMEOUT, `${route}@${width} empty_state evaluate`);
        if (route === '/transfer') out.transfer_layout[width] = await withTimeout(page.evaluate(() => window.__measureTransferLayout()), EVALUATE_TIMEOUT, `${route}@${width} transfer_layout evaluate`);
      } catch (error) {
        const failed = errorMeasurement(error);
        out.routes[route][width] = { status: null, h1: null, ...failed };
        out.overflow[route][width] = failed;
        out.axe[route][width] = failed;
        messages.push({ type: 'measurement', text: failed.error });
        if (route === '/accounts') out.summary_card[width] = { found: false, reason: failed.error, ...failed };
        if (route === '/accounts/travel' || route === '/accounts/checking') out.empty_state[route][width] = failed;
        if (route === '/transfer') out.transfer_layout[width] = { found: false, reason: failed.error, ...failed };
      } finally {
        out.console[route][width] = messages;
        await context.close();
      }
    }
  }
} finally {
  await browser.close();
}
console.log(JSON.stringify(out));
