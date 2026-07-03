import type { Provider } from './types.ts';
import { requestJson } from './http.ts';
import { sanitizeGitHubPr, sanitizeGitHubPrComment, sanitizeGitHubIssueComment } from './sanitize.ts';

const GITHUB_PAGE_SIZE = 100;

type GitHubPullRequestRef = {
  owner: string;
  repo: string;
  pullNumber: string;
};

function getGitHubToken(): string {
  const token = (process.env.GITHUB_TOKEN ?? process.env.GH_TOKEN)?.trim();
  if (!token) {
    throw new Error('Missing GITHUB_TOKEN (or GH_TOKEN). Populate it in .env.local before using this helper.');
  }
  return token;
}

function parseGitHubPrUrl(prUrl: string): GitHubPullRequestRef {
  let parsed: URL;
  try {
    parsed = new URL(prUrl);
  } catch {
    throw new Error(`Invalid GitHub PR URL: ${prUrl}`);
  }
  if (parsed.hostname !== 'github.com') {
    throw new Error(`Unsupported GitHub host: ${parsed.hostname}`);
  }
  const match = parsed.pathname.match(/^\/([^/]+)\/([^/]+)\/pull\/(\d+)\/?$/);

  if (!match) {
    throw new Error(`Could not parse a GitHub PR URL from: ${prUrl}`);
  }
  return { owner: match[1], repo: match[2], pullNumber: match[3] };
}

async function getGitHubPr(target: string): Promise<unknown> {
  const parsed = parseGitHubPrUrl(target);
  const url = `https://api.github.com/repos/${encodeURIComponent(parsed.owner)}/${encodeURIComponent(parsed.repo)}/pulls/${encodeURIComponent(parsed.pullNumber)}`;

  return {
    request: parsed,
    pullRequest: sanitizeGitHubPr(await requestJson(url, gitHubHeaders())),
  };
}

function gitHubHeaders(): Record<string, string> {
  return {
    Authorization: `Bearer ${getGitHubToken()}`,
    Accept: 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
  };
}

function parseLimit(extra?: string): number | undefined {
  if (!extra) return undefined;
  const n = parseInt(extra, 10);
  return Number.isFinite(n) && n > 0 ? n : undefined;
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

async function getGitHubPrComments(target: string, extra?: string): Promise<unknown> {
  const parsed = parseGitHubPrUrl(target);
  const headers = gitHubHeaders();
  const repoBase = `https://api.github.com/repos/${encodeURIComponent(parsed.owner)}/${encodeURIComponent(parsed.repo)}`;
  const limit = parseLimit(extra);

  const reviewUrl = `${repoBase}/pulls/${encodeURIComponent(parsed.pullNumber)}/comments?sort=created&direction=desc`;
  let reviewComments = await fetchAllGitHubPages(reviewUrl, headers, limit);
  reviewComments.reverse();

  const issueUrl = `${repoBase}/issues/${encodeURIComponent(parsed.pullNumber)}/comments`;
  let issueComments = await fetchAllGitHubPages(issueUrl, headers);
  if (limit && issueComments.length > limit) {
    issueComments = issueComments.slice(-limit);
  }

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

export const githubProvider: Provider = {
  name: 'github',
  label: 'GitHub',
  requiredEnvKeys: ['GITHUB_TOKEN'],
  actions: {
    'pr': getGitHubPr,
    'comments': getGitHubPrComments,
  },
  usageLines: () => [
    'bun run .ritus/scripts/remote-api.ts github pr <pull-request-url>',
    'bun run .ritus/scripts/remote-api.ts github comments <pull-request-url> [count]',
  ],
  exampleLines: () => {
    const prUrl = process.env.EXAMPLE_GITHUB_PR_URL || 'https://github.com/owner/repo/pull/123';
    return [
      `bun run .ritus/scripts/remote-api.ts github pr ${prUrl}`,
      `bun run .ritus/scripts/remote-api.ts github comments ${prUrl}`,
      `bun run .ritus/scripts/remote-api.ts github comments ${prUrl} 20`,
    ];
  },
};
