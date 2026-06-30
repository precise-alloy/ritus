import type { Provider } from './types.ts';
import { requestJson } from './http.ts';

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
  const match = prUrl.match(/github\.com\/([^/]+)\/([^/]+)\/pull\/(\d+)/);
  if (!match) {
    throw new Error(`Could not parse a GitHub PR URL from: ${prUrl}`);
  }
  return { owner: match[1], repo: match[2], pullNumber: match[3] };
}

async function getGitHubPr(target: string): Promise<unknown> {
  const parsed = parseGitHubPrUrl(target);
  const token = getGitHubToken();
  const url = `https://api.github.com/repos/${encodeURIComponent(parsed.owner)}/${encodeURIComponent(parsed.repo)}/pulls/${encodeURIComponent(parsed.pullNumber)}`;

  return {
    request: parsed,
    pullRequest: await requestJson(url, {
      Authorization: `Bearer ${token}`,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
    }),
  };
}

export const githubProvider: Provider = {
  name: 'github',
  label: 'GitHub',
  requiredEnvKeys: ['GITHUB_TOKEN'],
  actions: {
    'pr': getGitHubPr,
  },
  usageLines: () => [
    'bun run .ritus/scripts/remote-api.ts github pr <pull-request-url>',
  ],
  exampleLines: () => {
    const prUrl = process.env.EXAMPLE_GITHUB_PR_URL || 'https://github.com/owner/repo/pull/123';
    return [
      `bun run .ritus/scripts/remote-api.ts github pr ${prUrl}`,
    ];
  },
};
