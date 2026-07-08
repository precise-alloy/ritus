import type { EnvMapping, Provider } from './types.ts';
import { requestJson, requestJsonWithHeaders } from './http.ts';
import { sanitizeGitHubPr, sanitizeGitHubPrComment, sanitizeGitHubIssueComment, sanitizeGitHubIssue } from './sanitize.ts';

const GITHUB_PAGE_SIZE = 100;

const GITHUB_DEFAULT_ENV: EnvMapping = {
  token: 'GITHUB_TOKEN',
  repo_url: 'GITHUB_REPO_URL',
};

type GitHubPullRequestRef = {
  owner: string;
  repo: string;
  pullNumber: string;
};

function getApiBaseUrl(env: EnvMapping): string {
  if (env.api_base_url) {
    const url = process.env[env.api_base_url]?.trim();
    if (url) return url.replace(/\/+$/, '');
  }
  return 'https://api.github.com';
}

function getExpectedHostname(env: EnvMapping): string {
  if (env.api_base_url) {
    const apiUrl = process.env[env.api_base_url]?.trim();
    if (apiUrl) {
      try {
        return new URL(apiUrl).hostname;
      } catch { /* fall through */ }
    }
  }
  return 'github.com';
}

function getGitHubToken(env: EnvMapping): string {
  const tokenEnvVar = env.token;
  const token = process.env[tokenEnvVar]?.trim();
  if (!token) {
    // GH_TOKEN fallback only for the default GITHUB_TOKEN mapping
    if (tokenEnvVar === 'GITHUB_TOKEN') {
      const ghToken = process.env.GH_TOKEN?.trim();
      if (ghToken) return ghToken;
    }
    throw new Error(`Missing ${tokenEnvVar}. Populate it in .env.local before using this helper.`);
  }
  return token;
}

function resolveGitHubRef(target: string, env: EnvMapping, pathSegment: 'pull' | 'issues'): string {
  const match = target.trim().match(/^#(\d+)$/);
  if (!match) return target;

  const number = match[1];
  if (number.startsWith('0') && number.length > 1) {
    throw new Error(
      `Invalid ${pathSegment === 'pull' ? 'PR' : 'issue'} number "#${number}". Leading zeros are not allowed. Did you mean "#${parseInt(number, 10)}"?`,
    );
  }

  const num = parseInt(number, 10);
  if (!Number.isFinite(num) || num <= 0) {
    throw new Error(
      `Invalid ${pathSegment === 'pull' ? 'PR' : 'issue'} number "#${number}". Must be a positive integer.`,
    );
  }

  const repoUrlEnvVar = env.repo_url;
  if (!repoUrlEnvVar) {
    throw new Error(`GitHub ref "#${number}" requires a repo_url mapping in the provider's env configuration.`);
  }

  const repoUrl = process.env[repoUrlEnvVar]?.trim();
  if (!repoUrl) {
    throw new Error(
      `GitHub ${pathSegment === 'pull' ? 'PR' : 'issue'} ref "#${number}" requires ${repoUrlEnvVar} in .env.local. ` +
        'Alternatively, pass the full URL.',
    );
  }

  let parsedUrl: URL;
  try {
    parsedUrl = new URL(repoUrl);
  } catch {
    throw new Error(
      `Invalid ${repoUrlEnvVar} value "${repoUrl}". Must be a valid repository URL (e.g., https://github.com/owner/repo).`,
    );
  }

  if (parsedUrl.protocol !== 'https:') {
    throw new Error(
      `Invalid ${repoUrlEnvVar} value "${repoUrl}". Must use https:// protocol for security.`,
    );
  }

  const pathSegments = parsedUrl.pathname.split('/').filter(Boolean).map(decodeURIComponent);
  if (pathSegments.length !== 2) {
    throw new Error(
      `Invalid ${repoUrlEnvVar} value "${repoUrl}". Must be a repository URL with owner and repo (e.g., https://github.com/owner/repo), not a root URL or subpath.`,
    );
  }

  const [owner, repo] = pathSegments;
  return `${parsedUrl.protocol}//${parsedUrl.hostname}/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/${pathSegment}/${number}`;
}

function parseGitHubPrUrl(prUrl: string, expectedHostname = 'github.com'): GitHubPullRequestRef {
  let parsed: URL;
  try {
    parsed = new URL(prUrl);
  } catch {
    throw new Error(`Invalid GitHub PR URL: ${prUrl}`);
  }
  if (parsed.hostname.toLowerCase() !== expectedHostname.toLowerCase()) {
    throw new Error(`Unsupported GitHub host: ${parsed.hostname}`);
  }
  const match = parsed.pathname.match(/^\/([^/]+)\/([^/]+)\/pull\/(\d+)\/?$/);

  if (!match) {
    throw new Error(`Could not parse a GitHub PR URL from: ${prUrl}`);
  }
  return { owner: match[1], repo: match[2], pullNumber: match[3] };
}

type GitHubIssueRef = {
  owner: string;
  repo: string;
  issueNumber: string;
};

function parseGitHubIssueUrl(issueUrl: string, expectedHostname = 'github.com'): GitHubIssueRef {
  let parsed: URL;
  try {
    parsed = new URL(issueUrl);
  } catch {
    throw new Error(`Invalid GitHub Issue URL: ${issueUrl}`);
  }
  if (parsed.hostname.toLowerCase() !== expectedHostname.toLowerCase()) {
    throw new Error(`Unsupported GitHub host: ${parsed.hostname}`);
  }
  const match = parsed.pathname.match(/^\/([^/]+)\/([^/]+)\/issues\/(\d+)\/?$/);

  if (!match) {
    throw new Error(`Could not parse a GitHub Issue URL from: ${issueUrl}`);
  }
  return { owner: match[1], repo: match[2], issueNumber: match[3] };
}

async function getGitHubPr(target: string, extra?: string, envMapping?: EnvMapping): Promise<unknown> {
  const env = envMapping ?? GITHUB_DEFAULT_ENV;
  const resolvedTarget = resolveGitHubRef(target, env, 'pull');
  const hostname = getExpectedHostname(env);
  const apiBase = getApiBaseUrl(env);
  const parsed = parseGitHubPrUrl(resolvedTarget, hostname);
  const url = `${apiBase}/repos/${encodeURIComponent(parsed.owner)}/${encodeURIComponent(parsed.repo)}/pulls/${encodeURIComponent(parsed.pullNumber)}`;

  return {
    request: parsed,
    pullRequest: sanitizeGitHubPr(await requestJson(url, gitHubHeaders(env))),
  };
}

function gitHubHeaders(env: EnvMapping): Record<string, string> {
  return {
    Authorization: `Bearer ${getGitHubToken(env)}`,
    Accept: 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
  };
}

function parseLimit(extra?: string): number | undefined {
  if (!extra) return undefined;
  const n = parseInt(extra, 10);
  if (!Number.isFinite(n) || n <= 0) return undefined;
  const maxLimit = 200 * GITHUB_PAGE_SIZE;
  return Math.min(n, maxLimit);
}

async function fetchAllGitHubPages(baseUrl: string, headers: Record<string, string>, limit?: number): Promise<unknown[]> {
  const items: unknown[] = [];
  const perPage = limit && limit <= GITHUB_PAGE_SIZE ? limit : GITHUB_PAGE_SIZE;
  for (let page = 1; page <= 200; page++) {
    const separator = baseUrl.includes('?') ? '&' : '?';
    const url = `${baseUrl}${separator}per_page=${perPage}&page=${page}`;
    const result = await requestJson(url, headers);
    const pageItems = Array.isArray(result) ? result : [];
    items.push(...pageItems);
    if (limit && items.length >= limit) break;
    if (pageItems.length < perPage) break;
  }
  if (limit && items.length > limit) return items.slice(0, limit);
  return items;
}

function parseLinkHeaderLastPage(linkHeader: string | null): number | undefined {
  if (!linkHeader) return undefined;
  const lastMatch = linkHeader.match(/<([^>]+)>;\s*rel="last"/);
  if (!lastMatch) return undefined;
  try {
    const url = new URL(lastMatch[1]);
    const page = url.searchParams.get('page');
    if (!page) return undefined;
    const parsed = parseInt(page, 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : undefined;
  } catch {
    return undefined;
  }
}

async function fetchGitHubLatestIssueComments(baseUrl: string, headers: Record<string, string>, limit: number): Promise<unknown[]> {
  // Make a probe request with per_page=1 to discover total via Link header
  const separator = baseUrl.includes('?') ? '&' : '?';
  const probeUrl = `${baseUrl}${separator}per_page=1&page=1`;
  const { body, headers: responseHeaders } = await requestJsonWithHeaders(probeUrl, headers);

  const linkHeader = responseHeaders.get('link');
  const lastPage = parseLinkHeaderLastPage(linkHeader);

  if (lastPage === undefined) {
    // No Link header means there are 0–1 total items; the probe response already contains all results.
    const items = Array.isArray(body) ? body : [];
    return items.slice(-limit);
  }

  // lastPage with per_page=1 equals total item count
  const totalItems = lastPage;
  const totalPages = Math.ceil(totalItems / GITHUB_PAGE_SIZE);
  const startIndex = Math.max(1, totalItems - limit + 1);
  const startPage = Math.ceil(startIndex / GITHUB_PAGE_SIZE);
  const items: unknown[] = [];
  for (let page = startPage; page <= totalPages; page++) {
    const url = `${baseUrl}${separator}per_page=${GITHUB_PAGE_SIZE}&page=${page}`;
    const result = await requestJson(url, headers);
    const pageItems = Array.isArray(result) ? result : [];
    items.push(...pageItems);
  }

  return items.slice(-limit);
}

async function getGitHubPrComments(target: string, extra?: string, envMapping?: EnvMapping): Promise<unknown> {
  const env = envMapping ?? GITHUB_DEFAULT_ENV;
  const resolvedTarget = resolveGitHubRef(target, env, 'pull');
  const hostname = getExpectedHostname(env);
  const apiBase = getApiBaseUrl(env);
  const parsed = parseGitHubPrUrl(resolvedTarget, hostname);
  const headers = gitHubHeaders(env);
  const repoBase = `${apiBase}/repos/${encodeURIComponent(parsed.owner)}/${encodeURIComponent(parsed.repo)}`;
  const limit = parseLimit(extra);

  const reviewUrl = `${repoBase}/pulls/${encodeURIComponent(parsed.pullNumber)}/comments?sort=created&direction=desc`;
  let reviewComments = await fetchAllGitHubPages(reviewUrl, headers, limit);
  reviewComments.reverse();

  const issueUrl = `${repoBase}/issues/${encodeURIComponent(parsed.pullNumber)}/comments?sort=created&direction=asc`;
  let issueComments = limit
    ? await fetchGitHubLatestIssueComments(issueUrl, headers, limit)
    : await fetchAllGitHubPages(issueUrl, headers);

  return {
    request: parsed,
    ...(limit ? { limit } : {}),
    reviewComments: {
      returned: reviewComments.length,
      comments: reviewComments.map(sanitizeGitHubPrComment),
    },
    issueComments: {
      returned: issueComments.length,
      comments: issueComments.map(sanitizeGitHubIssueComment),
    },
  };
}

async function getGitHubIssue(target: string, extra?: string, envMapping?: EnvMapping): Promise<unknown> {
  const env = envMapping ?? GITHUB_DEFAULT_ENV;
  const resolvedTarget = resolveGitHubRef(target, env, 'issues');
  const hostname = getExpectedHostname(env);
  const apiBase = getApiBaseUrl(env);
  const parsed = parseGitHubIssueUrl(resolvedTarget, hostname);
  const url = `${apiBase}/repos/${encodeURIComponent(parsed.owner)}/${encodeURIComponent(parsed.repo)}/issues/${encodeURIComponent(parsed.issueNumber)}`;

  return {
    request: parsed,
    issue: sanitizeGitHubIssue(await requestJson(url, gitHubHeaders(env))),
  };
}

async function getGitHubIssueComments(target: string, extra?: string, envMapping?: EnvMapping): Promise<unknown> {
  const env = envMapping ?? GITHUB_DEFAULT_ENV;
  const resolvedTarget = resolveGitHubRef(target, env, 'issues');
  const hostname = getExpectedHostname(env);
  const apiBase = getApiBaseUrl(env);
  const parsed = parseGitHubIssueUrl(resolvedTarget, hostname);
  const headers = gitHubHeaders(env);
  const limit = parseLimit(extra);
  const baseUrl = `${apiBase}/repos/${encodeURIComponent(parsed.owner)}/${encodeURIComponent(parsed.repo)}/issues/${encodeURIComponent(parsed.issueNumber)}/comments?sort=created&direction=asc`;

  const comments = limit
    ? await fetchGitHubLatestIssueComments(baseUrl, headers, limit)
    : await fetchAllGitHubPages(baseUrl, headers);

  return {
    request: parsed,
    ...(limit ? { limit } : {}),
    comments: {
      returned: comments.length,
      comments: comments.map(sanitizeGitHubIssueComment),
    },
  };
}

export const githubProvider: Provider = {
  name: 'github',
  label: 'GitHub',
  requiredEnvKeys: ['GITHUB_TOKEN'],
  defaultEnvMapping: GITHUB_DEFAULT_ENV,
  actions: {
    'pr': getGitHubPr,
    'comments': getGitHubPrComments,
    'issue': getGitHubIssue,
    'issue-comments': getGitHubIssueComments,
  },
  canHandleTarget(action: string, target: string): boolean {
    if (!Object.hasOwn(this.actions, action)) return false;
    if (/^#\d+$/.test(target)) return true;

    let url: URL;
    try {
      url = new URL(target);
    } catch {
      return false;
    }

    // Path-pattern matching only; hostname filtering is handled at the instance level
    // to support both github.com and GitHub Enterprise hosts
    const prActions = new Set(['pr', 'comments']);
    const issueActions = new Set(['issue', 'issue-comments']);

    if (prActions.has(action)) {
      return /\/[^/]+\/[^/]+\/pull\/\d+\/?$/.test(url.pathname);
    }
    if (issueActions.has(action)) {
      return /\/[^/]+\/[^/]+\/issues\/\d+\/?$/.test(url.pathname);
    }

    return false;
  },
  usageLines: (cmd) => [
    `${cmd} github pr <pull-request-url|#number>`,
    `${cmd} github comments <pull-request-url|#number> [count]`,
    `${cmd} github issue <issue-url|#number>`,
    `${cmd} github issue-comments <issue-url|#number> [count]`,
  ],
  exampleLines: (cmd) => {
    const prUrl = process.env.EXAMPLE_GITHUB_PR_URL || 'https://github.com/owner/repo/pull/123';
    const issueUrl = process.env.EXAMPLE_GITHUB_ISSUE_URL || 'https://github.com/owner/repo/issues/456';
    return [
      `${cmd} github pr ${prUrl}`,
      `${cmd} github pr '#18'  # requires GITHUB_REPO_URL=https://github.com/owner/repo in .env.local`,
      `${cmd} github comments ${prUrl}`,
      `${cmd} github comments ${prUrl} 20`,
      `${cmd} github comments '#18'  # short ref`,
      `${cmd} github issue ${issueUrl}`,
      `${cmd} github issue '#1'  # short ref`,
      `${cmd} github issue-comments ${issueUrl}`,
      `${cmd} github issue-comments ${issueUrl} 20`,
    ];
  },
};
