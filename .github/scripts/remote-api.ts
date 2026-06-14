#!/usr/bin/env bun

// =============================================================================
// PROJECT CONFIG — UPDATE THESE WHEN COPYING THIS SCRIPT TO ANOTHER PROJECT.
// Everything below this block is generic and should not need changes.
// =============================================================================
const PROJECT_CONFIG = {
    // Jira Cloud site, e.g. https://your-company.atlassian.net (no trailing slash).
    jiraBaseUrl: 'https://episerver-services.atlassian.net',
    // Jira REST API path. Stable for Jira Cloud v3.
    jiraApiPath: '/rest/api/3',
    // Azure DevOps REST API version used for PR metadata calls.
    adoApiVersion: '7.0',
    // Examples shown in `printUsage`. Update so copy/pasters see your own URLs.
    examples: {
        jiraTicketKey: 'FMI-942',
        jiraTicketUrl: 'https://episerver-services.atlassian.net/browse/FMI-942',
        adoPrUrl: 'https://episerveremea-expertservices.visualstudio.com/First%20Mile/_git/FirstMile/pullrequest/8577',
    },
} as const;
// =============================================================================

type RequestHeaders = Record<string, string>;

type AzureDevOpsPullRequestRef = {
    organization: string;
    project: string;
    repository: string;
    pullRequestId: string;
};

type HttpError = Error & {
    statusCode?: number;
    responseBody?: unknown;
};

const HELP_FLAGS = new Set(['-h', '--help', 'help']);
const REQUEST_TIMEOUT_MS = 30_000;
const MAX_RETRIES = 3;
const RETRY_BASE_DELAY_MS = 500;
const JIRA_PAGE_SIZE = 100;

function printUsage(): void {
    const { jiraTicketKey, jiraTicketUrl, adoPrUrl } = PROJECT_CONFIG.examples;
    console.error(`Usage:
  bun run .github/scripts/remote-api.ts check-env
  bun run .github/scripts/remote-api.ts jira issue <ticket-key-or-url> [fields]
  bun run .github/scripts/remote-api.ts jira comments <ticket-key-or-url>
  bun run .github/scripts/remote-api.ts jira changelog <ticket-key-or-url>
  bun run .github/scripts/remote-api.ts ado pr <pull-request-url>

Examples:
  bun run .github/scripts/remote-api.ts check-env
  bun run .github/scripts/remote-api.ts jira issue ${jiraTicketKey}
  bun run .github/scripts/remote-api.ts jira issue ${jiraTicketUrl} summary,description,status,issuetype,comment
  bun run .github/scripts/remote-api.ts jira comments ${jiraTicketKey}
  bun run .github/scripts/remote-api.ts ado pr ${adoPrUrl}`);
}

async function readEnvFile(filePath: string): Promise<void> {
    const file = Bun.file(filePath);
    if (!(await file.exists())) {
        return;
    }

    const content = await file.text();
    for (const rawLine of content.split(/\r?\n/)) {
        const line = rawLine.trim();
        if (!line || line.startsWith('#')) {
            continue;
        }

        const separatorIndex = line.indexOf('=');
        if (separatorIndex === -1) {
            continue;
        }

        const key = line.slice(0, separatorIndex).trim();
        let value = line.slice(separatorIndex + 1).trim();
        if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
            value = value.slice(1, -1);
        }

        if (!(key in process.env)) {
            process.env[key] = value;
        }
    }
}

async function loadLocalEnv(): Promise<void> {
    await readEnvFile(`${process.cwd()}/.env.local`);
}

function basicAuth(value: string): string {
    return `Basic ${Buffer.from(value, 'utf8').toString('base64')}`;
}

function requireEnv(name: string): string {
    const value = process.env[name];
    if (!value) {
        throw new Error(`Missing required environment variable ${name}. Populate it in .env.local before using this helper.`);
    }

    return value;
}

function parseJson(text: string): unknown {
    if (!text) {
        return null;
    }

    try {
        return JSON.parse(text);
    } catch {
        return text;
    }
}

function buildErrorMessage(url: string, statusCode: number, responseBody: unknown): string {
    const responseText = typeof responseBody === 'string' ? responseBody : JSON.stringify(responseBody);

    let detail = responseText;
    if (responseBody && typeof responseBody === 'object') {
        if ('errorMessages' in responseBody && Array.isArray(responseBody.errorMessages) && responseBody.errorMessages.length > 0) {
            detail = responseBody.errorMessages.join(' | ');
        } else if ('message' in responseBody && typeof responseBody.message === 'string') {
            detail = responseBody.message;
        } else if ('error_description' in responseBody && typeof responseBody.error_description === 'string') {
            detail = responseBody.error_description;
        }
    }

    return `Request failed with ${statusCode} for ${url}: ${detail}`;
}

function sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

function isTransientStatus(status: number): boolean {
    // Retry on rate limits and server-side errors. Auth failures (401/403) are
    // hard stops per the skill contract — never retry those.
    return status === 408 || status === 429 || (status >= 500 && status <= 599);
}

async function requestJson(url: string, headers: RequestHeaders): Promise<unknown> {
    let lastError: HttpError | null = null;

    for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

        let response: Response;
        try {
            response = await fetch(url, {
                method: 'GET',
                headers,
                signal: controller.signal,
            });
        } catch (err) {
            clearTimeout(timer);
            const reason = err instanceof Error ? err.message : String(err);
            const aborted = err instanceof Error && err.name === 'AbortError';
            const wrapped: HttpError = new Error(aborted ? `Request to ${url} timed out after ${REQUEST_TIMEOUT_MS}ms` : `Network error calling ${url}: ${reason}`);
            lastError = wrapped;
            if (attempt < MAX_RETRIES) {
                await sleep(RETRY_BASE_DELAY_MS * 2 ** (attempt - 1));
                continue;
            }
            throw wrapped;
        }
        clearTimeout(timer);

        const bodyText = await response.text();
        const parsedBody = parseJson(bodyText);

        if (response.ok) {
            return parsedBody;
        }

        const error: HttpError = new Error(buildErrorMessage(url, response.status, parsedBody));
        error.statusCode = response.status;
        error.responseBody = parsedBody;

        if (attempt < MAX_RETRIES && isTransientStatus(response.status)) {
            lastError = error;
            const retryAfter = Number(response.headers.get('retry-after'));
            const delay = Number.isFinite(retryAfter) && retryAfter > 0 ? retryAfter * 1000 : RETRY_BASE_DELAY_MS * 2 ** (attempt - 1);
            await sleep(delay);
            continue;
        }

        throw error;
    }

    // Should never reach here, but satisfy the type checker.
    throw lastError ?? new Error(`Request to ${url} failed after ${MAX_RETRIES} attempts`);
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

async function getJiraIssue(ticketKeyOrUrl: string, fields?: string): Promise<unknown> {
    const jiraPat = requireEnv('JIRA_PAT');
    const jiraEmail = requireEnv('JIRA_EMAIL');
    const ticketKey = parseJiraKey(ticketKeyOrUrl);
    const requestedFields = fields || 'summary,description,status,issuetype,comment';
    const url = `${PROJECT_CONFIG.jiraBaseUrl}${PROJECT_CONFIG.jiraApiPath}/issue/${encodeURIComponent(ticketKey)}?fields=${encodeURIComponent(requestedFields)}`;

    return {
        ticketKey,
        fields: requestedFields.split(','),
        issue: await requestJson(url, {
            Authorization: basicAuth(`${jiraEmail}:${jiraPat}`),
            Accept: 'application/json',
        }),
    };
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
    // Safety cap to avoid infinite loops if the API behaves unexpectedly.
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

async function getJiraComments(ticketKeyOrUrl: string): Promise<unknown> {
    const jiraPat = requireEnv('JIRA_PAT');
    const jiraEmail = requireEnv('JIRA_EMAIL');
    const ticketKey = parseJiraKey(ticketKeyOrUrl);
    const baseUrl = `${PROJECT_CONFIG.jiraBaseUrl}${PROJECT_CONFIG.jiraApiPath}/issue/${encodeURIComponent(ticketKey)}/comment`;
    const headers: RequestHeaders = {
        Authorization: basicAuth(`${jiraEmail}:${jiraPat}`),
        Accept: 'application/json',
    };

    const { items } = await fetchAllJiraPages(baseUrl, headers, 'comments');

    return {
        ticketKey,
        comments: {
            total: items.length,
            comments: items,
        },
    };
}

async function getJiraChangelog(ticketKeyOrUrl: string): Promise<unknown> {
    const jiraPat = requireEnv('JIRA_PAT');
    const jiraEmail = requireEnv('JIRA_EMAIL');
    const ticketKey = parseJiraKey(ticketKeyOrUrl);
    const baseUrl = `${PROJECT_CONFIG.jiraBaseUrl}${PROJECT_CONFIG.jiraApiPath}/issue/${encodeURIComponent(ticketKey)}/changelog`;
    const headers: RequestHeaders = {
        Authorization: basicAuth(`${jiraEmail}:${jiraPat}`),
        Accept: 'application/json',
    };

    const { items } = await fetchAllJiraPages(baseUrl, headers, 'values');

    return {
        ticketKey,
        changelog: {
            total: items.length,
            values: items,
        },
    };
}

async function getAzureDevOpsPr(prUrl: string): Promise<unknown> {
    const pat = requireEnv('AZURE_DEVOPS_READONLY_PAT');
    const parsedPr = parseAzureDevOpsPrUrl(prUrl);
    const url = `https://dev.azure.com/${encodeURIComponent(parsedPr.organization)}/${encodeURIComponent(parsedPr.project)}/_apis/git/repositories/${encodeURIComponent(parsedPr.repository)}/pullrequests/${encodeURIComponent(parsedPr.pullRequestId)}?api-version=${PROJECT_CONFIG.adoApiVersion}`;

    return {
        request: parsedPr,
        pullRequest: await requestJson(url, {
            Authorization: basicAuth(`:${pat}`),
            Accept: 'application/json',
        }),
    };
}

const REQUIRED_ENV_KEYS = ['JIRA_PAT', 'JIRA_EMAIL', 'AZURE_DEVOPS_READONLY_PAT', 'AZURE_DEVOPS_EMAILS'] as const;

type EnvCheckResult = {
    envLocalPath: string;
    envLocalExists: boolean;
    keys: { name: string; present: boolean }[];
    missing: string[];
    ok: boolean;
};

async function checkEnv(): Promise<EnvCheckResult> {
    const envLocalPath = `${process.cwd()}/.env.local`;
    const envLocalExists = await Bun.file(envLocalPath).exists();

    const keys = REQUIRED_ENV_KEYS.map((name) => ({
        name,
        present: !!process.env[name] && process.env[name]!.trim().length > 0,
    }));
    const missing = keys.filter((k) => !k.present).map((k) => k.name);

    return {
        envLocalPath,
        envLocalExists,
        keys,
        missing,
        ok: envLocalExists && missing.length === 0,
    };
}

async function runCheckEnv(): Promise<void> {
    const result = await checkEnv();
    console.log(JSON.stringify(result, null, 2));

    if (!result.envLocalExists) {
        console.error(`\n.env.local is missing at ${result.envLocalPath}.`);
        console.error('Create it with these keys (empty values are fine, then fill them):');
        for (const key of REQUIRED_ENV_KEYS) {
            console.error(`  ${key}=`);
        }
        process.exit(1);
    }

    if (result.missing.length > 0) {
        console.error(`\nMissing or empty required keys in .env.local: ${result.missing.join(', ')}`);
        console.error('Fill them in and re-run.');
        process.exit(1);
    }

    process.exit(0);
}

async function main(): Promise<void> {
    await loadLocalEnv();

    const [, , system, action, target, extra] = Bun.argv;
    if (!system) {
        printUsage();
        process.exit(2);
    }

    if (HELP_FLAGS.has(system)) {
        printUsage();
        process.exit(0);
    }

    if (system === 'check-env') {
        await runCheckEnv();
    }

    if (!action || !target) {
        printUsage();
        process.exit(2);
    }

    // Fail fast with a clear, consistent message if .env.local is missing/incomplete
    // before any remote call is attempted.
    const envCheck = await checkEnv();
    if (!envCheck.ok) {
        console.error('Pre-flight check failed. Run: bun run .github/scripts/remote-api.ts check-env');
        if (!envCheck.envLocalExists) {
            console.error(`.env.local missing at ${envCheck.envLocalPath}`);
        }
        if (envCheck.missing.length > 0) {
            console.error(`Missing or empty keys: ${envCheck.missing.join(', ')}`);
        }
        process.exit(1);
    }

    let result: unknown;
    if (system === 'jira' && action === 'issue') {
        result = await getJiraIssue(target, extra);
    } else if (system === 'jira' && action === 'comments') {
        result = await getJiraComments(target);
    } else if (system === 'jira' && action === 'changelog') {
        result = await getJiraChangelog(target);
    } else if (system === 'ado' && action === 'pr') {
        result = await getAzureDevOpsPr(target);
    } else {
        printUsage();
        process.exit(2);
    }

    console.log(JSON.stringify(result, null, 2));
}

main().catch((error: unknown) => {
    if (error instanceof Error) {
        console.error(error.message);
    } else {
        console.error(String(error));
    }
    process.exit(1);
});
