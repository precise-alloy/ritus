import type { EnvMapping, Provider, RequestHeaders } from './types.ts';
import { basicAuth, requestJson, resolveEnv, safeDecode } from './http.ts';
import { sanitizeAdoWorkItem, sanitizeAdoComment, sanitizeAdoUpdate, sanitizeAdoPr } from './sanitize.ts';

const ADO_API_VERSION = '7.0';
const ADO_COMMENTS_API_VERSION = '7.0-preview.4';
const ADO_PAGE_SIZE = 200;

const ADO_DEFAULT_ENV: EnvMapping = {
  pat: 'AZURE_DEVOPS_READONLY_PAT',
  org: 'AZURE_DEVOPS_ORG',
  project: 'AZURE_DEVOPS_PROJECT',
};

type AzureDevOpsPullRequestRef = {
  organization: string;
  project: string;
  repository?: string;
  pullRequestId: string;
};

type AdoWorkItemRef = {
  organization: string;
  project: string;
  workItemId: string;
};

function adoHeaders(env: EnvMapping): RequestHeaders {
  const pat = resolveEnv(env, 'pat');
  return {
    Authorization: basicAuth(`:${pat}`),
    Accept: 'application/json',
  };
}

function normalizeAdoOrg(raw: string): string {
  try {
    const url = new URL(raw);
    const host = url.hostname.toLowerCase();
    if (host === 'dev.azure.com') {
      const firstSegment = url.pathname.split('/').filter(Boolean)[0];
      return firstSegment ? safeDecode(firstSegment) : raw;
    }
    if (host.endsWith('.visualstudio.com')) {
      return host.replace('.visualstudio.com', '');
    }
  } catch { /* not a URL, use as-is */ }
  return raw;
}

export { normalizeAdoOrg };

function adoBaseUrl(org: string, project: string): string {
  return `https://dev.azure.com/${encodeURIComponent(normalizeAdoOrg(org))}/${encodeURIComponent(safeDecode(project))}`;
}

// ---------------------------------------------------------------------------
// PR URL parsing (existing)
// ---------------------------------------------------------------------------

function parseAzureDevOpsPrUrl(prUrl: string, envMapping?: EnvMapping): AzureDevOpsPullRequestRef {
  if (/^\d+$/.test(prUrl)) {
    const env = envMapping ?? ADO_DEFAULT_ENV;
    const orgEnvVar = env.org;
    const projectEnvVar = env.project;
    const org = process.env[orgEnvVar]?.trim();
    const project = process.env[projectEnvVar]?.trim();
    if (!org || !project) {
      throw new Error(
        `Bare PR ID "${prUrl}" requires ${orgEnvVar} and ${projectEnvVar} in .env.local. ` +
          'Alternatively, pass the full PR URL.',
      );
    }
    return { organization: normalizeAdoOrg(org), project: safeDecode(project), pullRequestId: prUrl };
  }

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
    .map(safeDecode);

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

function parseAdoWorkItemUrl(urlOrId: string, envMapping?: EnvMapping): AdoWorkItemRef {
  if (/^\d+$/.test(urlOrId)) {
    const env = envMapping ?? ADO_DEFAULT_ENV;
    const orgEnvVar = env.org;
    const projectEnvVar = env.project;
    const org = process.env[orgEnvVar]?.trim();
    const project = process.env[projectEnvVar]?.trim();
    if (!org || !project) {
      throw new Error(
        `Bare work item ID "${urlOrId}" requires ${orgEnvVar} and ${projectEnvVar} in .env.local. ` +
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
    .map(safeDecode);

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

function adoPrUrl(parsed: AzureDevOpsPullRequestRef): string {
  const base = adoBaseUrl(parsed.organization, parsed.project);
  if (parsed.repository) {
    return `${base}/_apis/git/repositories/${encodeURIComponent(parsed.repository)}/pullrequests/${encodeURIComponent(parsed.pullRequestId)}`;
  }
  return `${base}/_apis/git/pullrequests/${encodeURIComponent(parsed.pullRequestId)}`;
}

async function getAdoPr(target: string, extra?: string, envMapping?: EnvMapping): Promise<unknown> {
  const env = envMapping ?? ADO_DEFAULT_ENV;
  const parsed = parseAzureDevOpsPrUrl(target, env);
  const url = `${adoPrUrl(parsed)}?api-version=${ADO_API_VERSION}`;

  return {
    request: parsed,
    pullRequest: sanitizeAdoPr(await requestJson(url, adoHeaders(env))),
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

// ---------------------------------------------------------------------------
// Work item actions
// ---------------------------------------------------------------------------

async function getAdoWorkItem(target: string, extra?: string, envMapping?: EnvMapping): Promise<unknown> {
  const env = envMapping ?? ADO_DEFAULT_ENV;
  const parsed = parseAdoWorkItemUrl(target, env);
  const expand = extra ? '' : '&$expand=all';
  const fields = extra ? `&fields=${encodeURIComponent(extra)}` : '';
  const url = `${adoBaseUrl(parsed.organization, parsed.project)}/_apis/wit/workitems/${encodeURIComponent(parsed.workItemId)}?api-version=${ADO_API_VERSION}${expand}${fields}`;

  return {
    workItemId: parsed.workItemId,
    ...(extra ? { fields: extra.split(',').map(f => f.trim()).filter(Boolean) } : {}),
    workItem: sanitizeAdoWorkItem(await requestJson(url, adoHeaders(env))),
  };
}

async function getAdoWorkItemComments(target: string, extra?: string, envMapping?: EnvMapping): Promise<unknown> {
  const env = envMapping ?? ADO_DEFAULT_ENV;
  const parsed = parseAdoWorkItemUrl(target, env);
  const limit = parseLimit(extra);
  const url = `${adoBaseUrl(parsed.organization, parsed.project)}/_apis/wit/workitems/${encodeURIComponent(parsed.workItemId)}/comments?api-version=${ADO_COMMENTS_API_VERSION}`;

  const result = (await requestJson(url, adoHeaders(env))) as { totalCount?: number; comments?: unknown[] };
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

async function getAdoWorkItemUpdates(target: string, extra?: string, envMapping?: EnvMapping): Promise<unknown> {
  const env = envMapping ?? ADO_DEFAULT_ENV;
  const parsed = parseAdoWorkItemUrl(target, env);
  const base = `${adoBaseUrl(parsed.organization, parsed.project)}/_apis/wit/workitems/${encodeURIComponent(parsed.workItemId)}/updates`;
  const headers = adoHeaders(env);

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

function isAdoHost(hostname: string): boolean {
  const h = hostname.toLowerCase();
  return h === 'dev.azure.com' || h.endsWith('.visualstudio.com');
}

export const adoProvider: Provider = {
  name: 'ado',
  label: 'Azure DevOps',
  requiredEnvKeys: ['AZURE_DEVOPS_READONLY_PAT'],
  defaultEnvMapping: ADO_DEFAULT_ENV,
  actions: {
    'pr': getAdoPr,
    'issue': getAdoWorkItem,
    'comments': getAdoWorkItemComments,
    'changelog': getAdoWorkItemUpdates,
  },
  canHandleTarget(action: string, target: string): boolean {
    if (!Object.hasOwn(this.actions, action)) return false;

    if (action === 'pr') {
      if (/^\d+$/.test(target)) return true;
      try {
        const url = new URL(target);
        return isAdoHost(url.hostname) && /\/_git\/[^/]+\/pullrequest\/\d+\/?$/i.test(url.pathname);
      } catch {
        return false;
      }
    }

    const workItemActions = new Set(['issue', 'comments', 'changelog']);
    if (workItemActions.has(action)) {
      if (/^\d+$/.test(target)) return true;
      try {
        const url = new URL(target);
        return isAdoHost(url.hostname) && /\/_workitems\/edit\/\d+\/?$/i.test(url.pathname);
      } catch {
        return false;
      }
    }

    return false;
  },
  usageLines: (cmd) => [
    `${cmd} ado pr <pull-request-url>`,
    `${cmd} ado issue <work-item-url-or-id> [fields]`,
    `${cmd} ado comments <work-item-url-or-id> [count]`,
    `${cmd} ado changelog <work-item-url-or-id>`,
  ],
  exampleLines: (cmd) => {
    const prUrl = process.env.EXAMPLE_ADO_PR_URL || 'https://dev.azure.com/your-org/your-project/_git/your-repo/pullrequest/1234';
    const wiUrl = process.env.EXAMPLE_ADO_WORK_ITEM_URL || 'https://dev.azure.com/your-org/your-project/_workitems/edit/12345';
    return [
      `${cmd} ado pr ${prUrl}`,
      `${cmd} ado issue ${wiUrl}`,
      `${cmd} ado issue ${wiUrl} System.Title,System.State,System.Description`,
      `${cmd} ado comments ${wiUrl}`,
      `${cmd} ado changelog ${wiUrl}`,
    ];
  },
};
