import { afterEach, describe, expect, it, mock } from 'bun:test';

const JIRA_BASE_URL = 'https://your-company.atlassian.net';
const JIRA_HOST = 'your-company.atlassian.net';

type MockState = {
  requestJson: (url: string, headers: unknown) => Promise<unknown>;
  requestBinaryCalls: string[];
};

const state: MockState = {
  requestJson: async () => ({}),
  requestBinaryCalls: [],
};

mock.module('./http.ts', () => ({
  basicAuth: (value: string) => `Basic ${Buffer.from(value, 'utf8').toString('base64')}`,
  requireEnv: (name: string) => {
    const value = process.env[name];
    if (!value) throw new Error(`Missing required environment variable ${name}.`);
    return value;
  },
  requestJson: (url: string, headers: unknown) => state.requestJson(url, headers),
  requestBinary: async (url: string) => {
    state.requestBinaryCalls.push(url);
    return 0;
  },
}));

const { jiraProvider } = await import('./provider-jira.ts');

function setEnv(): void {
  process.env.JIRA_BASE_URL = JIRA_BASE_URL;
  process.env.JIRA_PAT = 'test-pat';
  process.env.JIRA_EMAIL = 'user@example.com';
}

function attachmentResponse(content: string) {
  return {
    fields: {
      attachment: [
        {
          id: '10001',
          filename: 'evil.png',
          mimeType: 'image/png',
          size: 123,
          content,
        },
      ],
    },
  };
}

describe('downloadJiraAttachments host validation', () => {
  afterEach(() => {
    state.requestJson = async () => ({});
    state.requestBinaryCalls = [];
  });

  it('rejects an off-host attachment content URL before sending credentials', async () => {
    setEnv();
    state.requestJson = async () => attachmentResponse('https://attacker.example.com/steal');

    const download = jiraProvider.actions['attachment-download'];
    await expect(download('PROJ-1', '/tmp/jira-attachments-test')).rejects.toThrow(/unexpected host/i);
    expect(state.requestBinaryCalls).toEqual([]);
  });

  it('rejects a non-HTTPS attachment content URL', async () => {
    setEnv();
    state.requestJson = async () => attachmentResponse(`http://${JIRA_HOST}/secure/attachment/10001/evil.png`);

    const download = jiraProvider.actions['attachment-download'];
    await expect(download('PROJ-1', '/tmp/jira-attachments-test')).rejects.toThrow(/non-HTTPS/i);
    expect(state.requestBinaryCalls).toEqual([]);
  });

  it('allows an on-host HTTPS attachment content URL', async () => {
    setEnv();
    const content = `${JIRA_BASE_URL}/secure/attachment/10001/ok.png`;
    state.requestJson = async () => attachmentResponse(content);

    const download = jiraProvider.actions['attachment-download'];
    const result = (await download('PROJ-1', '/tmp/jira-attachments-test')) as { downloaded: unknown[] };
    expect(state.requestBinaryCalls).toEqual([content]);
    expect(result.downloaded).toHaveLength(1);
  });
});
