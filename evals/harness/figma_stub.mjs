#!/usr/bin/env node
import { appendFileSync, readFileSync } from 'node:fs';
import { createInterface } from 'node:readline';
import { Buffer } from 'node:buffer';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const designDir = join(here, '..', 'fixture', 'web', 'design');
const design = JSON.parse(readFileSync(join(designDir, 'file.json'), 'utf8'));
const guidancePath = join(designDir, 'figma-design-to-code', 'SKILL.md');
const guidance = readFileSync(guidancePath, 'utf8');
const resourceUri = 'skill://figma/figma-design-to-code/SKILL.md';
const fallbackProtocol = '2025-06-18';

const toolNames = ['get_design_context', 'get_variable_defs', 'get_metadata', 'get_screenshot', 'get_code_connect_map'];

function logRequest(request) {
  const line = JSON.stringify({ at: new Date().toISOString(), method: request.method, id: request.id ?? null }) + '\n';
  process.stderr.write(line);
  if (process.env.FIGMA_STUB_LOG) {
    appendFileSync(process.env.FIGMA_STUB_LOG, line, 'utf8');
  }
}

function respond(id, result) {
  process.stdout.write(JSON.stringify({ jsonrpc: '2.0', id, result }) + '\n');
}

function error(id, code, message) {
  process.stdout.write(JSON.stringify({ jsonrpc: '2.0', id, error: { code, message } }) + '\n');
}

function toolResult(text, isError = false) {
  return { isError, content: [{ type: 'text', text }] };
}

function normalizeNodeId(value) {
  return typeof value === 'string' ? value.replace('-', ':') : value;
}

function nodeFromArgs(args = {}) {
  if (!args.nodeId) {
    return { error: toolResult('nodeId is required: pass the node-id from a Figma URL', true) };
  }
  const fileKey = args.fileKey || design.fileKey;
  if (fileKey !== design.fileKey) {
    return { error: toolResult(`File ${fileKey} not found; expected ${design.fileKey}`, true) };
  }
  const normalized = normalizeNodeId(args.nodeId);
  const node = design.nodes[normalized];
  if (!node) {
    return { error: toolResult(`Node ${normalized} not found in file ${design.fileKey}`, true) };
  }
  return { node };
}

function varCss(name) {
  return `var(--${name.replace('/', '-')}, ${design.variables[name]})`;
}

function nodeVariables(node) {
  if (node.id === '12:30') {
    return { 'color/bg': design.variables['color/bg'] };
  }
  return {
    'color/surface': design.variables['color/surface'],
    'color/border': design.variables['color/border'],
    'color/text-muted': design.variables['color/text-muted'],
    'color/text': design.variables['color/text'],
    'space/4': design.variables['space/4'],
    'radius/2': design.variables['radius/2'],
  };
}

function designContext(node) {
  if (node.id === '12:30') {
    return `Reference for Accounts - desktop (${design.fileKey} ${node.id}). The frame is 1280px wide and contains node 12:34. Use the screenshot as a visual target, not as an asset; adapt the reference to the project's components and tokens.`;
  }
  return `<section class="card summary-card" aria-labelledby="total-balance-title">
  <h2 id="total-balance-title">Total balance</h2>
  <p>$12,345.67</p>
</section>

.card.summary-card {
  display: flex;
  flex-direction: column;
  gap: ${varCss('space/4')};
  padding: ${varCss('space/4')};
  border-radius: ${varCss('radius/2')};
  border: 1px solid ${varCss('color/border')};
  background: ${varCss('color/surface')};
  width: 100%;
}
.card.summary-card h2 {
  margin: 0;
  color: ${varCss('color/text-muted')};
  font-size: 14px;
  line-height: 20px;
  font-weight: 400;
}
.card.summary-card p {
  margin: 0;
  color: ${varCss('color/text')};
  font-size: 24px;
  line-height: 32px;
  font-weight: 600;
}

This is reference code for node ${node.id} (${node.name}). Adapt it to the project's existing components and tokens instead of copying it verbatim.`;
}

function xmlNode(node, indent = '') {
  const attrs = `id="${node.id}" name="${node.name}" type="${node.type}" x="${node.x}" y="${node.y}" width="${node.width}" height="${node.height}"`;
  const children = (node.children || []).map((child) => typeof child === 'string' ? design.nodes[child] : child).filter(Boolean);
  if (!children.length) return `${indent}<node ${attrs} />`;
  return `${indent}<node ${attrs}>\n${children.map((child) => xmlNode(child, indent + '  ')).join('\n')}\n${indent}</node>`;
}

function screenshotResult(node) {
  const stem = node.id.replace(':', '-');
  const data = readFileSync(join(designDir, `${stem}.png`)).toString('base64');
  return { content: [{ type: 'image', data, mimeType: 'image/png' }] };
}

function callTool(name, args) {
  if (!toolNames.includes(name)) return toolResult(`Unknown tool ${name}`, true);
  const resolved = nodeFromArgs(args);
  if (resolved.error) return resolved.error;
  const node = resolved.node;
  if (name === 'get_design_context') return toolResult(designContext(node));
  if (name === 'get_variable_defs') return toolResult(JSON.stringify(nodeVariables(node), null, 2));
  if (name === 'get_metadata') return toolResult(`<file key="${design.fileKey}" name="${design.name}">\n${xmlNode(node, '  ')}\n</file>`);
  if (name === 'get_screenshot') return screenshotResult(node);
  if (name === 'get_code_connect_map') return toolResult('{}');
}

function toolSchema(name) {
  return {
    name,
    description: `TinyLedger Web stand-in for Figma ${name}`,
    inputSchema: {
      type: 'object',
      properties: {
        fileKey: { type: 'string', description: 'Figma file key; TLWEB0001 for this fixture.' },
        nodeId: { type: 'string', description: 'Figma node id such as 12:34 or URL form 12-34.' },
      },
      required: ['nodeId'],
      additionalProperties: true,
    },
  };
}

const rl = createInterface({ input: process.stdin, crlfDelay: Infinity });
rl.on('line', (line) => {
  if (!line.trim()) return;
  let request;
  try {
    request = JSON.parse(line);
  } catch (parseError) {
    error(null, -32700, 'Parse error');
    return;
  }
  logRequest(request);
  const id = request.id;
  const params = request.params || {};
  try {
    if (request.method === 'notifications/initialized') return;
    if (id === undefined || id === null) return;
    if (request.method === 'initialize') {
      respond(id, {
        protocolVersion: params.protocolVersion || fallbackProtocol,
        capabilities: { tools: {}, resources: {} },
        serverInfo: { name: 'figma-stand-in', version: '1.0.0' },
      });
    } else if (request.method === 'ping') {
      respond(id, {});
    } else if (request.method === 'tools/list') {
      respond(id, { tools: toolNames.map(toolSchema) });
    } else if (request.method === 'tools/call') {
      respond(id, callTool(params.name, params.arguments || {}));
    } else if (request.method === 'resources/list') {
      respond(id, { resources: [{ uri: resourceUri, name: 'figma-design-to-code/SKILL.md', mimeType: 'text/markdown' }] });
    } else if (request.method === 'resources/read') {
      if (params.uri !== resourceUri) {
        error(id, -32602, `Unknown resource ${params.uri}`);
      } else {
        respond(id, { contents: [{ uri: resourceUri, mimeType: 'text/markdown', text: guidance }] });
      }
    } else if (request.method === 'prompts/list') {
      respond(id, { prompts: [] });
    } else {
      error(id, -32601, `Method not found: ${request.method}`);
    }
  } catch (caught) {
    error(id, -32603, caught && caught.message ? caught.message : String(caught));
  }
});
