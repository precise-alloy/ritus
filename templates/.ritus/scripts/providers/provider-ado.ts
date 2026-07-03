import type { Provider, RequestHeaders } from './types.ts';
import { basicAuth, requestJson, requireEnv } from './http.ts';
import { sanitizeAdoWorkItem, sanitizeAdoComment, sanitizeAdoUpdate, sanitizeAdoPr, sanitizeAdoPrThread } from './sanitize.ts';

const ADO_API_VERSION = '7.0';
const ADO_COMMENTS_API_VERSION = '7.0-preview.4';
const ADO_PAGE_SIZE = 200;

type AzureDevOpsPullRequestRef = {
  organization: string;
  project: string;
  repository: string;
  pullRequestId: string;
};

type AdoWorkItemRef = {
  organization: string;
  project: string;
  workItemId: string;
};

function adoHeaders(): RequestHeaders {
  const pat = requireEnv('AZURE_DEVOPS_READONLY_PAT');
  return {
    Authorization: basicAuth(`:${pat}`),
    Accept: 'application/json',
  };
}

function adoBaseUrl(org: string, project: string): string {
  return `https://dev.azure.com/${encodeURIComponent(org)}/${encodeURIComponent(project)}`;
}

// ---------------------------------------------------------------------------
// PR URL parsing (existing)
// ---------------------------------------------------------------------------

function parseAzureDevOpsPrUrl(prUrl: string): AzureDevOpsPullRequestRef {
  let parsedUrl: URL;
  try {
    parsedUrl = new URL(prUrl);
  } catch {
    throw new Error(`Invalid Azure DevOps PR URL: ${prUrl}`);
  }

  const host = parsedUrl.hostname.toLowerCase();
  const segments = parsedUrl.pathname
    .split('/')
    .filter(Boolean)
    .map((segment) => decodeURIComponent(segment));

  if (host === 'dev.azure.com') {
    if (segments.length < 6 || segments[2] !== '_git' || segments[4] !== 'pullrequest') {
      throw new Error(`Unsupported Azure DevOps PR URL shape: ${prUrl}`);
    }

    return {
      organization: segments[0],
      project: segments[1],
      repository: segments[3],
      pullRequestId: segments[5],
    };
  }

  if (host.endsWith('.visualstudio.com')) {
    if (segments.length < 5 || segments[1] !== '_git' || segments[3] !== 'pullrequest') {
      throw new Error(`Unsupported Azure DevOps PR URL shape: ${prUrl}`);
    }

    return {
      organization: host.replace('.visualstudio.com', ''),
      project: segments[0],
      repository: segments[2],
      pullRequestId: segments[4],
    };
  }

  throw new Error(`Unsupported Azure DevOps host: ${parsedUrl.hostname}`);
}

// ---------------------------------------------------------------------------
// Work item URL / ID parsing (new)
// ---------------------------------------------------------------------------

function extractWorkItemId(segments: string[], minEditIdx: number, rawUrl: string): string {
  const editIdx = segments.indexOf('_workitems');
  if (editIdx === -1 || editIdx < minEditIdx || segments[editIdx + 1] !== 'edit' || !segments[editIdx + 2]) {
    throw new Error(`Unsupported Azure DevOps work item URL shape: ${rawUrl}`);
  }
  return segments[editIdx + 2];
}

function parseAdoWorkItemUrl(urlOrId: string): AdoWorkItemRef {
  if (/^\d+$/.test(urlOrId)) {
    const org = process.env.AZURE_DEVOPS_ORG?.trim();
    const project = process.env.AZURE_DEVOPS_PROJECT?.trim();
    if (!org || !project) {
      throw new Error(
        `Bare work item ID "${urlOrId}" requires AZURE_DEVOPS_ORG and AZURE_DEVOPS_PROJECT in .env.local. ` +
          'Alternatively, pass the full work item URL.',
      );
    }
    return { organization: org, project, workItemId: urlOrId };
  }

  let parsedUrl: URL;
  try {
    parsedUrl = new URL(urlOrId);
  } catch {
    throw new Error(`Invalid Azure DevOps work item URL or ID: ${urlOrId}`);
  }

  const host = parsedUrl.hostname.toLowerCase();
  const segments = parsedUrl.pathname
    .split('/')
    .filter(Boolean)
    .map((segment) => decodeURIComponent(segment));

  if (host === 'dev.azure.com') {
    return {
      organization: segments[0],
      project: segments[1],
      workItemId: extractWorkItemId(segments, 2, urlOrId),
    };
  }

  if (host.endsWith('.visualstudio.com')) {
    return {
      organization: host.replace('.visualstudio.com', ''),
      project: segments[0],
      workItemId: extractWorkItemId(segments, 1, urlOrId),
    };
  }

  throw new Error(`Unsupported Azure DevOps host: ${parsedUrl.hostname}`);
}

// ---------------------------------------------------------------------------
// PR actions
// ---------------------------------------------------------------------------

async function getAdoPr(target: string): Promise<unknown> {
  const parsed = parseAzureDevOpsPrUrl(target);
  const url = `${adoBaseUrl(parsed.organization, parsed.project)}/_apis/git/repositories/${encodeURIComponent(parsed.repository)}/pullrequests/${encodeURIComponent(parsed.pullRequestId)}?api-version=${ADO_API_VERSION}`;

  return {
    request: parsed,
    pullRequest: sanitizeAdoPr(await requestJson(url, adoHeaders())),
  };
}

function parseLimit(extra?: string): number | undefined {
  if (!extra) return undefined;
  const n = parseInt(extra, 10);
  return Number.isFinite(n) && n > 0 ? n : undefined;
}

function takeLatest<T>(items: T[], limit: number | undefined, dateKey: string): T[] {
  if (!limit || items.length <= limit) return items;
  const sortedDesc = [...items].sort((a, b) => {
    const da = String((a as Record<string, unknown>)[dateKey] ?? '');
    const db = String((b as Record<string, unknown>)[dateKey] ?? '');
    return db.localeCompare(da);
  });
  return sortedDesc.slice(0, limit).reverse();
}

async function getAdoPrThreads(target: string, extra?: string): Promise<unknown> {
  const parsed = parseAzureDevOpsPrUrl(target);
  const limit = parseLimit(extra);
  const url = `${adoBaseUrl(parsed.organization, parsed.project)}/_apis/git/repositories/${encodeURIComponent(parsed.repository)}/pullrequests/${encodeURIComponent(parsed.pullRequestId)}/threads?api-version=${ADO_API_VERSION}`;

  const result = (await requestJson(url, adoHeaders())) as { count?: number; value?: unknown[] };
  const allThreads = (result?.value ?? []).map(sanitizeAdoPrThread);
  const threads = takeLatest(allThreads, limit, 'publishedDate');

  return {
    request: parsed,
    ...(limit ? { limit } : {}),
    threads: {
      total: allThreads.length,
      returned: threads.length,
      threads,
    },
  };
}

// ---------------------------------------------------------------------------
// Work item actions
// ---------------------------------------------------------------------------

async function getAdoWorkItem(target: string, extra?: string): Promise<unknown> {
  const parsed = parseAdoWorkItemUrl(target);
  const expand = extra ? '' : '&$expand=all';
  const fields = extra ? `&fields=${encodeURIComponent(extra)}` : '';
  const url = `${adoBaseUrl(parsed.organization, parsed.project)}/_apis/wit/workitems/${encodeURIComponent(parsed.workItemId)}?api-version=${ADO_API_VERSION}${expand}${fields}`;

  return {
    workItemId: parsed.workItemId,
    ...(extra ? { fields: extra.split(',').map(f => f.trim()).filter(Boolean) } : {}),
    workItem: sanitizeAdoWorkItem(await requestJson(url, adoHeaders())),
  };
}

async function getAdoWorkItemComments(target: string, extra?: string): Promise<unknown> {
  const parsed = parseAdoWorkItemUrl(target);
  const limit = parseLimit(extra);
  const url = `${adoBaseUrl(parsed.organization, parsed.project)}/_apis/wit/workitems/${encodeURIComponent(parsed.workItemId)}/comments?api-version=${ADO_COMMENTS_API_VERSION}`;

  const result = (await requestJson(url, adoHeaders())) as { totalCount?: number; comments?: unknown[] };
  const allComments = (result?.comments ?? []).map(sanitizeAdoComment);
  const comments = takeLatest(allComments, limit, 'createdDate');

  return {
    workItemId: parsed.workItemId,
    ...(limit ? { limit } : {}),
    comments: {
      total: result?.totalCount ?? allComments.length,
      returned: comments.length,
      comments,
    },
  };
}

type AdoUpdatesPage = {
  count?: number;
  value?: unknown[];
};

async function getAdoWorkItemUpdates(target: string): Promise<unknown> {
  const parsed = parseAdoWorkItemUrl(target);
  const base = `${adoBaseUrl(parsed.organization, parsed.project)}/_apis/wit/workitems/${encodeURIComponent(parsed.workItemId)}/updates`;
  const headers = adoHeaders();

  const allUpdates: unknown[] = [];
  let skip = 0;

  for (let i = 0; i < 200; i++) {
    const url = `${base}?api-version=${ADO_API_VERSION}&$skip=${skip}&$top=${ADO_PAGE_SIZE}`;
    const page = (await requestJson(url, headers)) as AdoUpdatesPage;
    const items = page?.value ?? [];
    allUpdates.push(...items);

    if (items.length < ADO_PAGE_SIZE) {
      break;
    }
    skip += items.length;
  }

  return {
    workItemId: parsed.workItemId,
    changelog: {
      total: allUpdates.length,
      updates: allUpdates.map(sanitizeAdoUpdate),
    },
  };
}

// ---------------------------------------------------------------------------
// Provider export
// ---------------------------------------------------------------------------

export const adoProvider: Provider = {
  name: 'ado',
  label: 'Azure DevOps',
  requiredEnvKeys: ['AZURE_DEVOPS_READONLY_PAT'],
  actions: {
    'pr': getAdoPr,
    'pr-threads': getAdoPrThreads,
    'issue': getAdoWorkItem,
    'comments': getAdoWorkItemComments,
    'changelog': getAdoWorkItemUpdates,
  },
  usageLines: () => [
    'bun run .ritus/scripts/remote-api.ts ado pr <pull-request-url>',
    'bun run .ritus/scripts/remote-api.ts ado pr-threads <pull-request-url> [count]',
    'bun run .ritus/scripts/remote-api.ts ado issue <work-item-url-or-id> [fields]',
    'bun run .ritus/scripts/remote-api.ts ado comments <work-item-url-or-id> [count]',
    'bun run .ritus/scripts/remote-api.ts ado changelog <work-item-url-or-id>',
  ],
  exampleLines: () => {
    const prUrl = process.env.EXAMPLE_ADO_PR_URL || 'https://dev.azure.com/your-org/your-project/_git/your-repo/pullrequest/1234';
    const wiUrl = process.env.EXAMPLE_ADO_WORK_ITEM_URL || 'https://dev.azure.com/your-org/your-project/_workitems/edit/12345';
    return [
      `bun run .ritus/scripts/remote-api.ts ado pr ${prUrl}`,
      `bun run .ritus/scripts/remote-api.ts ado pr-threads ${prUrl}`,
      `bun run .ritus/scripts/remote-api.ts ado pr-threads ${prUrl} 20`,
      `bun run .ritus/scripts/remote-api.ts ado issue ${wiUrl}`,
      `bun run .ritus/scripts/remote-api.ts ado issue ${wiUrl} System.Title,System.State,System.Description`,
      `bun run .ritus/scripts/remote-api.ts ado comments ${wiUrl}`,
      `bun run .ritus/scripts/remote-api.ts ado changelog ${wiUrl}`,
    ];
  },
};
