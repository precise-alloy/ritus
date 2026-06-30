import type { Provider, RequestHeaders } from './types.ts';
import { basicAuth, requestBinary, requestJson, requireEnv } from './http.ts';

const JIRA_PAGE_SIZE = 100;

function jiraBaseUrl(): string {
  return requireEnv('JIRA_BASE_URL').replace(/\/+$/, '');
}

function jiraHeaders(): RequestHeaders {
  const pat = requireEnv('JIRA_PAT');
  const email = requireEnv('JIRA_EMAIL');
  return {
    Authorization: basicAuth(`${email}:${pat}`),
    Accept: 'application/json',
  };
}

function parseJiraKey(ticketKeyOrUrl: string): string {
  if (/^[A-Z][A-Z0-9]+-\d+$/i.test(ticketKeyOrUrl)) {
    return ticketKeyOrUrl.toUpperCase();
  }

  const match = ticketKeyOrUrl.match(/\/browse\/([A-Z][A-Z0-9]+-\d+)/i);
  if (!match) {
    throw new Error(`Could not parse a Jira ticket key from: ${ticketKeyOrUrl}`);
  }

  return match[1].toUpperCase();
}

type JiraPage = {
  startAt?: number;
  maxResults?: number;
  total?: number;
  isLast?: boolean;
  values?: unknown[];
  comments?: unknown[];
  histories?: unknown[];
};

async function fetchAllJiraPages(baseUrl: string, headers: RequestHeaders, itemsKey: 'comments' | 'values' | 'histories'): Promise<{ pages: JiraPage[]; items: unknown[] }> {
  const pages: JiraPage[] = [];
  const items: unknown[] = [];
  let startAt = 0;

  for (let i = 0; i < 200; i++) {
    const separator = baseUrl.includes('?') ? '&' : '?';
    const pagedUrl = `${baseUrl}${separator}startAt=${startAt}&maxResults=${JIRA_PAGE_SIZE}`;
    const page = (await requestJson(pagedUrl, headers)) as JiraPage;
    pages.push(page);

    const pageItems = (page?.[itemsKey] ?? []) as unknown[];
    items.push(...pageItems);

    const fetched = pageItems.length;
    const total = typeof page?.total === 'number' ? page.total : undefined;
    const maxResults = typeof page?.maxResults === 'number' ? page.maxResults : JIRA_PAGE_SIZE;
    const isLastFlag = page?.isLast === true;
    const reachedTotal = typeof total === 'number' && startAt + fetched >= total;

    if (isLastFlag || reachedTotal || fetched === 0 || fetched < maxResults) {
      break;
    }
    startAt += fetched;
  }
  return { pages, items };
}

async function getJiraIssue(target: string, extra?: string): Promise<unknown> {
  const ticketKey = parseJiraKey(target);
  const requestedFields = extra || 'summary,description,status,issuetype,comment';
  const url = `${jiraBaseUrl()}/rest/api/3/issue/${encodeURIComponent(ticketKey)}?fields=${encodeURIComponent(requestedFields)}`;

  return {
    ticketKey,
    fields: requestedFields.split(','),
    issue: await requestJson(url, jiraHeaders()),
  };
}

async function getJiraComments(target: string): Promise<unknown> {
  const ticketKey = parseJiraKey(target);
  const baseUrl = `${jiraBaseUrl()}/rest/api/3/issue/${encodeURIComponent(ticketKey)}/comment`;
  const { items } = await fetchAllJiraPages(baseUrl, jiraHeaders(), 'comments');

  return {
    ticketKey,
    comments: {
      total: items.length,
      comments: items,
    },
  };
}

async function getJiraChangelog(target: string): Promise<unknown> {
  const ticketKey = parseJiraKey(target);
  const baseUrl = `${jiraBaseUrl()}/rest/api/3/issue/${encodeURIComponent(ticketKey)}/changelog`;
  const { items } = await fetchAllJiraPages(baseUrl, jiraHeaders(), 'values');

  return {
    ticketKey,
    changelog: {
      total: items.length,
      values: items,
    },
  };
}

type JiraAttachment = {
  id: string;
  filename: string;
  mimeType: string;
  size: number;
  content: string;
};

const IMAGE_MIME_TYPES = new Set([
  'image/png',
  'image/jpeg',
  'image/gif',
  'image/webp',
  'image/svg+xml',
]);

async function getJiraAttachments(target: string): Promise<{ ticketKey: string; attachments: JiraAttachment[] }> {
  const ticketKey = parseJiraKey(target);
  const url = `${jiraBaseUrl()}/rest/api/3/issue/${encodeURIComponent(ticketKey)}?fields=attachment`;

  const issue = (await requestJson(url, jiraHeaders())) as { fields?: { attachment?: JiraAttachment[] } };

  const attachments = (issue?.fields?.attachment ?? []).map((a) => ({
    id: a.id,
    filename: a.filename,
    mimeType: a.mimeType,
    size: a.size,
    content: a.content,
  }));

  return { ticketKey, attachments };
}

async function downloadJiraAttachments(target: string, extra?: string): Promise<unknown> {
  if (!extra) {
    console.error('Missing output directory. Usage: jira attachment-download <ticket-key> <output-dir>');
    process.exit(2);
  }

  const outputDir = extra;
  const { ticketKey, attachments } = await getJiraAttachments(target);
  const images = attachments.filter((a) => IMAGE_MIME_TYPES.has(a.mimeType));

  if (images.length === 0) {
    return { ticketKey, outputDir, downloaded: [], message: 'No image attachments found' };
  }

  const { mkdirSync } = await import('node:fs');
  mkdirSync(outputDir, { recursive: true });

  const pat = requireEnv('JIRA_PAT');
  const email = requireEnv('JIRA_EMAIL');
  const headers: RequestHeaders = {
    Authorization: basicAuth(`${email}:${pat}`),
  };

  const downloaded: { filename: string; path: string; mimeType: string; size: number }[] = [];

  for (const attachment of images) {
    const outputPath = `${outputDir}/${attachment.filename}`;
    const bytesWritten = await requestBinary(attachment.content, headers, outputPath);
    downloaded.push({
      filename: attachment.filename,
      path: outputPath,
      mimeType: attachment.mimeType,
      size: bytesWritten,
    });
  }

  return { ticketKey, outputDir, downloaded };
}

export const jiraProvider: Provider = {
  name: 'jira',
  label: 'Jira Cloud',
  requiredEnvKeys: ['JIRA_BASE_URL', 'JIRA_PAT', 'JIRA_EMAIL'],
  actions: {
    'issue': getJiraIssue,
    'comments': getJiraComments,
    'changelog': getJiraChangelog,
    'attachments': getJiraAttachments,
    'attachment-download': downloadJiraAttachments,
  },
  usageLines: () => [
    'bun run .ritus/scripts/remote-api.ts jira issue <ticket-key-or-url> [fields]',
    'bun run .ritus/scripts/remote-api.ts jira comments <ticket-key-or-url>',
    'bun run .ritus/scripts/remote-api.ts jira changelog <ticket-key-or-url>',
    'bun run .ritus/scripts/remote-api.ts jira attachments <ticket-key-or-url>',
    'bun run .ritus/scripts/remote-api.ts jira attachment-download <ticket-key-or-url> <output-dir>',
  ],
  exampleLines: () => {
    const key = process.env.EXAMPLE_JIRA_TICKET_KEY || 'PROJ-123';
    const url = process.env.EXAMPLE_JIRA_TICKET_URL || 'https://your-company.atlassian.net/browse/PROJ-123';
    return [
      `bun run .ritus/scripts/remote-api.ts jira issue ${key}`,
      `bun run .ritus/scripts/remote-api.ts jira issue ${url} summary,description,status,issuetype,comment`,
      `bun run .ritus/scripts/remote-api.ts jira comments ${key}`,
      `bun run .ritus/scripts/remote-api.ts jira attachments ${key}`,
      `bun run .ritus/scripts/remote-api.ts jira attachment-download ${key} .jira-attachments/${key}`,
    ];
  },
};
