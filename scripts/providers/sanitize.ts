// Response sanitization for Jira, Azure DevOps, and GitHub API responses.
// Strips noisy fields (avatars, self-links, identity GUIDs, pagination metadata)
// and converts ADF/HTML markup to compact Markdown-flavoured text to reduce agent context token usage.

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

type AnyObject = Record<string, unknown>;

function isObject(v: unknown): v is AnyObject {
  return v !== null && typeof v === 'object' && !Array.isArray(v);
}

function isAdfNode(v: unknown): boolean {
  return isObject(v) && v.type === 'doc' && v.version === 1;
}

function isJiraIdentity(v: unknown): boolean {
  return isObject(v) && ('accountId' in v || 'accountType' in v) && 'displayName' in v;
}

function isAdoIdentity(v: unknown): boolean {
  return isObject(v) && ('uniqueName' in v || 'descriptor' in v) && 'displayName' in v;
}

function flattenJiraIdentity(v: unknown): { displayName: string } | unknown {
  if (!isJiraIdentity(v)) return v;
  return { displayName: (v as AnyObject).displayName as string };
}

function flattenAdoIdentity(v: unknown): { displayName: string } | unknown {
  if (!isAdoIdentity(v)) return v;
  return { displayName: (v as AnyObject).displayName as string };
}

function stripNullish(obj: AnyObject): AnyObject {
  const result: AnyObject = {};
  for (const [key, value] of Object.entries(obj)) {
    if (value === null || value === undefined) continue;
    if (Array.isArray(value) && value.length === 0) continue;
    result[key] = value;
  }
  return result;
}

function hasHtmlTags(v: unknown): boolean {
  return typeof v === 'string' && /<[a-z][\s\S]*>/i.test(v);
}

// Applies a replacement repeatedly until the string stops changing, so that a
// match reintroduced by an earlier replacement (e.g. "<scr<script>ipt>") cannot
// survive the sanitization pass. maxIterations caps the loop so a pathological
// input cannot spin unbounded (O(N^2) DoS guard).
function replaceUntilStable(input: string, pattern: RegExp, replacement: string, maxIterations = 100): string {
  let out = input;
  let prev: string;
  let iterations = 0;
  do {
    prev = out;
    out = out.replace(pattern, replacement);
  } while (out !== prev && ++iterations < maxIterations);
  return out;
}

// ---------------------------------------------------------------------------
// ADF-to-text converter
// ---------------------------------------------------------------------------

export function adfToText(node: unknown, depth = 0): string {
  if (node == null) return '';
  if (Array.isArray(node)) return node.map(n => adfToText(n, depth)).join('');
  if (!isObject(node)) return '';

  const n = node as AnyObject;
  const content = n.content as unknown[] | undefined;
  const attrs = n.attrs as AnyObject | undefined;

  switch (n.type) {
    case 'text':
      return (n.text as string) ?? '';

    case 'hardBreak':
      return '\n';

    case 'paragraph':
      return adfToText(content, depth) + '\n\n';

    case 'heading': {
      const rawLevel = Number(attrs?.level);
      const level = Number.isFinite(rawLevel) ? Math.min(6, Math.max(1, Math.trunc(rawLevel))) : 2;
      return '\n' + '#'.repeat(level) + ' ' + adfToText(content, depth) + '\n\n';
    }

    case 'bulletList':
      return adfToText(content, depth + 1);

    case 'orderedList': {
      const rawStart = Number(attrs?.order);
      const start = Number.isFinite(rawStart) ? Math.max(1, Math.trunc(rawStart)) : 1;
      const items = Array.isArray(content) ? content : [];
      const indent = '  '.repeat(Math.max(0, depth));
      return items.map((child, idx) => {
        if (!isObject(child)) return '';
        const li = child as AnyObject;
        const liContent = li.content as unknown[] | undefined;
        return indent + `${start + idx}. ` + adfToText(liContent, depth + 1).trim() + '\n';
      }).join('');
    }

    case 'listItem': {
      const indent = '  '.repeat(Math.max(0, depth - 1));
      return indent + '- ' + adfToText(content, depth).trim() + '\n';
    }

    case 'codeBlock':
      return '\n```\n' + adfToText(content, depth) + '\n```\n';

    case 'blockquote': {
      const text = adfToText(content, depth).trim();
      return text.split('\n').map(line => '> ' + line).join('\n') + '\n';
    }

    case 'rule':
      return '\n---\n';

    case 'table':
      return '\n' + adfToText(content, depth) + '\n';

    case 'tableRow':
      return adfToText(content, depth) + '|\n';

    case 'tableHeader':
    case 'tableCell':
      return '| ' + adfToText(content, depth).trim() + ' ';

    case 'mediaSingle':
    case 'media': {
      const id = attrs?.id ?? attrs?.alt ?? 'attachment';
      return `[media: ${id}]`;
    }

    case 'inlineCard':
    case 'blockCard':
      return (attrs?.url as string) ?? '';

    case 'mention':
      return (attrs?.text as string) ?? '@user';

    case 'emoji':
      return (attrs?.shortName as string) ?? '';

    case 'status':
      return (attrs?.text as string) ?? '';

    case 'panel': {
      const panelType = (attrs?.panelType as string) ?? 'info';
      return `[${panelType}]: ` + adfToText(content, depth);
    }

    case 'expand': {
      const title = (attrs?.title as string) ?? '';
      return (title ? title + ':\n' : '') + adfToText(content, depth);
    }

    case 'doc':
    default:
      if (content) return adfToText(content, depth);
      return '';
  }
}

// ---------------------------------------------------------------------------
// HTML-to-text converter
// ---------------------------------------------------------------------------

export function htmlToText(html: unknown): string {
  if (typeof html !== 'string') return '';
  const hadHtmlTags = hasHtmlTags(html);
  let text = html;

  if (hadHtmlTags) {
    text = text.replace(/<br\s*\/?>/gi, '\n');
    text = text.replace(/<\/(?:p|div|tr)>/gi, '\n');
    text = text.replace(/<li[^>]*>/gi, '\n- ');
    text = text.replace(/<\/(?:h[1-6])>/gi, '\n');
    text = text.replace(/<h[1-6][^>]*>/gi, '\n');
    text = replaceUntilStable(text, /<[^>]*>/g, '');
  }

  text = text.replace(/&lt;/g, '<');
  text = text.replace(/&gt;/g, '>');
  text = text.replace(/&quot;/g, '"');
  text = text.replace(/&#39;|&apos;/g, "'");
  text = text.replace(/&nbsp;/g, ' ');
  text = text.replace(/&#(\d+);/g, (_, code) => {
    const cp = Number(code);
    return cp >= 0 && cp <= 0x10ffff ? String.fromCodePoint(cp) : '';
  });
  text = text.replace(/&#x([0-9a-fA-F]+);/g, (_, hex) => {
    const cp = parseInt(hex, 16);
    return cp >= 0 && cp <= 0x10ffff ? String.fromCodePoint(cp) : '';
  });
  // Decode the ampersand entity last so an already-decoded value cannot be
  // interpreted as another entity (prevents double-unescaping, e.g. "&amp;lt;").
  text = text.replace(/&amp;/g, '&');

  // Guard against entity-decoding reintroducing tag-shaped sequences (e.g. "&lt;script&gt;").
  text = replaceUntilStable(text, /<\/?[a-z][^>]*>/gi, '');

  text = text.replace(/\n{3,}/g, '\n\n');
  return text.trim();
}

// ---------------------------------------------------------------------------
// Jira sanitizers
// ---------------------------------------------------------------------------

function cleanJiraLinkedIssue(issue: unknown): unknown {
  if (!isObject(issue)) return issue;
  const i = issue as AnyObject;
  const fields = i.fields as AnyObject | undefined;
  const result: AnyObject = { key: i.key };
  if (fields) {
    result.fields = stripNullish({
      summary: fields.summary,
      status: isObject(fields.status) ? { name: (fields.status as AnyObject).name } : fields.status,
    });
  }
  return result;
}

export function sanitizeJiraComment(raw: unknown): unknown {
  if (!isObject(raw)) return raw;
  const c = raw as AnyObject;
  return stripNullish({
    author: flattenJiraIdentity(c.author),
    body: isObject(c.body) ? adfToText(c.body).trim() : c.body,
    created: c.created,
    updated: c.updated,
  });
}

export function sanitizeJiraChangelog(raw: unknown): unknown {
  if (!isObject(raw)) return raw;
  const entry = raw as AnyObject;
  const items = Array.isArray(entry.items)
    ? (entry.items as unknown[])
        .filter(isObject)
        .map(item => stripNullish({
          field: item.field,
          fieldtype: item.fieldtype,
          fromString: item.fromString,
          toString: item.toString,
        }))
    : entry.items;

  return stripNullish({
    author: flattenJiraIdentity(entry.author),
    created: entry.created,
    items,
  });
}

export function sanitizeJiraIssue(raw: unknown): unknown {
  if (!isObject(raw)) return raw;
  const issue = { ...(raw as AnyObject) };

  delete issue.expand;
  delete issue.self;
  delete issue.id;
  delete issue.names;
  delete issue.schema;

  if (!isObject(issue.fields)) return issue;
  const fields = { ...(issue.fields as AnyObject) };

  for (const [key, value] of Object.entries(fields)) {
    if (value === null || value === undefined) {
      delete fields[key];
      continue;
    }

    if (Array.isArray(value)) {
      const cleaned = (value as unknown[])
        .map((item) => {
          if (isAdfNode(item)) return adfToText(item).trim();
          if (isJiraIdentity(item)) return flattenJiraIdentity(item);
          if (isObject(item)) {
            const obj = { ...(item as AnyObject) };
            delete obj.self;
            delete obj.avatarUrls;
            return obj;
          }
          return item;
        })
        .filter((v) => v !== null && v !== undefined);

      if (cleaned.length === 0) delete fields[key];
      else fields[key] = cleaned;
      continue;
    }

    if (isAdfNode(value)) {
      fields[key] = adfToText(value).trim();
      continue;
    }

    if (isJiraIdentity(value)) {
      fields[key] = flattenJiraIdentity(value);
      continue;
    }

    if (isObject(value)) {
      const obj = { ...(value as AnyObject) };
      delete obj.self;
      delete obj.avatarUrls;
      fields[key] = obj;
    }
  }

  if (isObject(fields.status)) {
    const s = fields.status as AnyObject;
    const sc = isObject(s.statusCategory) ? { name: (s.statusCategory as AnyObject).name } : undefined;
    fields.status = stripNullish({ name: s.name, statusCategory: sc });
  }

  if (isObject(fields.issuetype)) {
    const t = fields.issuetype as AnyObject;
    fields.issuetype = stripNullish({ name: t.name, subtask: t.subtask });
  }

  if (isObject(fields.priority)) {
    fields.priority = { name: (fields.priority as AnyObject).name };
  }

  if (isObject(fields.parent)) {
    fields.parent = cleanJiraLinkedIssue(fields.parent);
  }

  if (Array.isArray(fields.subtasks)) {
    fields.subtasks = (fields.subtasks as unknown[]).map(cleanJiraLinkedIssue);
  }

  if (Array.isArray(fields.issuelinks)) {
    fields.issuelinks = (fields.issuelinks as AnyObject[]).map(link => {
      const cleaned: AnyObject = {};
      if (isObject(link.type)) {
        const lt = link.type as AnyObject;
        cleaned.type = stripNullish({ name: lt.name, inward: lt.inward, outward: lt.outward });
      }
      if (link.inwardIssue) cleaned.inwardIssue = cleanJiraLinkedIssue(link.inwardIssue);
      if (link.outwardIssue) cleaned.outwardIssue = cleanJiraLinkedIssue(link.outwardIssue);
      return cleaned;
    });
  }

  if (isObject(fields.comment)) {
    const commentBlock = fields.comment as AnyObject;
    const comments = Array.isArray(commentBlock.comments) ? commentBlock.comments : [];
    const total = typeof commentBlock.total === 'number' ? commentBlock.total : comments.length;
    fields.comment = stripNullish({
      total,
      returned: comments.length,
      comments: (comments as unknown[]).map(sanitizeJiraComment),
    });
  }

  issue.fields = stripNullish(fields);
  return issue;
}

// ---------------------------------------------------------------------------
// GitHub sanitizers
// ---------------------------------------------------------------------------

function isGitHubUser(v: unknown): boolean {
  return isObject(v) && 'login' in v && 'avatar_url' in v;
}

function flattenGitHubUser(v: unknown): { login: string } | unknown {
  if (!isGitHubUser(v)) return v;
  return { login: (v as AnyObject).login as string };
}

const GITHUB_PR_URL_FIELDS = new Set([
  'url', 'html_url', 'diff_url', 'patch_url', 'issue_url',
  'comments_url', 'review_comments_url', 'review_comment_url',
  'commits_url', 'statuses_url',
]);

const GITHUB_PR_DELETE_FIELDS = new Set([
  'node_id', 'id', '_links',
  'author_association', 'active_lock_reason',
  'auto_merge', 'performed_via_github_app',
]);

function cleanGitHubRef(ref: unknown): unknown {
  if (!isObject(ref)) return ref;
  const r = ref as AnyObject;
  const repo = isObject(r.repo) ? stripNullish({ full_name: (r.repo as AnyObject).full_name }) : undefined;
  return stripNullish({ ref: r.ref, sha: r.sha, repo });
}

export function sanitizeGitHubPr(raw: unknown): unknown {
  if (!isObject(raw)) return raw;
  const pr = { ...(raw as AnyObject) };

  for (const key of GITHUB_PR_URL_FIELDS) delete pr[key];
  for (const key of GITHUB_PR_DELETE_FIELDS) delete pr[key];

  if (isGitHubUser(pr.user)) pr.user = flattenGitHubUser(pr.user);
  if (isGitHubUser(pr.merged_by)) pr.merged_by = flattenGitHubUser(pr.merged_by);

  if (Array.isArray(pr.assignees)) {
    pr.assignees = (pr.assignees as unknown[]).map(flattenGitHubUser);
  }
  if (Array.isArray(pr.requested_reviewers)) {
    pr.requested_reviewers = (pr.requested_reviewers as unknown[]).map(flattenGitHubUser);
  }
  if (Array.isArray(pr.requested_teams)) {
    pr.requested_teams = (pr.requested_teams as AnyObject[]).map(t => ({ slug: t.slug }));
  }

  pr.head = cleanGitHubRef(pr.head);
  pr.base = cleanGitHubRef(pr.base);

  if (Array.isArray(pr.labels)) {
    pr.labels = (pr.labels as AnyObject[]).map(l => ({ name: l.name }));
  }

  if (isObject(pr.milestone)) {
    pr.milestone = { title: (pr.milestone as AnyObject).title };
  }

  return stripNullish(pr);
}

export function sanitizeGitHubPrComment(raw: unknown): unknown {
  if (!isObject(raw)) return raw;
  const c = raw as AnyObject;
  return stripNullish({
    user: flattenGitHubUser(c.user),
    body: c.body,
    path: c.path,
    line: c.line,
    original_line: c.original_line,
    diff_hunk: typeof c.diff_hunk === 'string' ? c.diff_hunk.slice(0, 2000) : c.diff_hunk,
    created_at: c.created_at,
    updated_at: c.updated_at,
    in_reply_to_id: c.in_reply_to_id,
  });
}

const GITHUB_ISSUE_URL_FIELDS = new Set([
  'url', 'repository_url', 'labels_url', 'comments_url', 'events_url',
  'html_url', 'timeline_url',
]);

const GITHUB_ISSUE_DELETE_FIELDS = new Set([
  'node_id', 'id', 'author_association', 'active_lock_reason',
  'performed_via_github_app',
]);

export function sanitizeGitHubIssue(raw: unknown): unknown {
  if (!isObject(raw)) return raw;
  const issue = { ...(raw as AnyObject) };

  for (const key of GITHUB_ISSUE_URL_FIELDS) delete issue[key];
  for (const key of GITHUB_ISSUE_DELETE_FIELDS) delete issue[key];

  if (isGitHubUser(issue.user)) issue.user = flattenGitHubUser(issue.user);
  if (isGitHubUser(issue.closed_by)) issue.closed_by = flattenGitHubUser(issue.closed_by);

  if (Array.isArray(issue.assignees)) {
    issue.assignees = (issue.assignees as unknown[]).map(flattenGitHubUser);
  }

  if (Array.isArray(issue.labels)) {
    issue.labels = (issue.labels as AnyObject[]).map(l => ({ name: l.name }));
  }

  if (isObject(issue.milestone)) {
    issue.milestone = { title: (issue.milestone as AnyObject).title };
  }

  // Preserve the signal that this "issue" is actually a PR, then remove the verbose sub-object
  issue.is_pull_request = !!issue.pull_request;
  delete issue.pull_request;

  return stripNullish(issue);
}

export function sanitizeGitHubIssueComment(raw: unknown): unknown {
  if (!isObject(raw)) return raw;
  const c = raw as AnyObject;
  return stripNullish({
    user: flattenGitHubUser(c.user),
    body: c.body,
    created_at: c.created_at,
    updated_at: c.updated_at,
  });
}

// ---------------------------------------------------------------------------
// ADO sanitizers
// ---------------------------------------------------------------------------

const ADO_NOISE_FIELDS = new Set([
  'System.Watermark',
  'System.Rev',
  'System.AuthorizedAs',
  'System.RevisedDate',
  'System.AuthorizedDate',
  'System.PersonId',
  'System.BoardColumn',
  'System.BoardColumnDone',
]);

const ADO_HTML_FIELDS = new Set([
  'System.Description',
  'System.History',
  'Microsoft.VSTS.TCM.ReproSteps',
  'Microsoft.VSTS.Common.AcceptanceCriteria',
]);

export function sanitizeAdoComment(raw: unknown): unknown {
  if (!isObject(raw)) return raw;
  const c = raw as AnyObject;
  return stripNullish({
    text: typeof c.text === 'string' ? htmlToText(c.text) : c.text,
    createdBy: flattenAdoIdentity(c.createdBy),
    createdDate: c.createdDate,
    modifiedDate: c.modifiedDate,
  });
}

export function sanitizeAdoUpdate(raw: unknown): unknown {
  if (!isObject(raw)) return raw;
  const entry = { ...(raw as AnyObject) };

  delete entry._links;
  delete entry.url;
  delete entry.id;
  delete entry.rev;
  delete entry.workItemId;

  if (entry.revisedBy) {
    entry.revisedBy = flattenAdoIdentity(entry.revisedBy);
  }

  if (isObject(entry.fields)) {
    const fields = entry.fields as AnyObject;
    for (const [key, value] of Object.entries(fields)) {
      if (!isObject(value)) continue;
      const change = value as AnyObject;
      if (isAdoIdentity(change.oldValue)) change.oldValue = flattenAdoIdentity(change.oldValue);
      if (isAdoIdentity(change.newValue)) change.newValue = flattenAdoIdentity(change.newValue);
    }
  }

  return stripNullish(entry);
}

export function sanitizeAdoWorkItem(raw: unknown): unknown {
  if (!isObject(raw)) return raw;
  const wi = { ...(raw as AnyObject) };

  delete wi._links;
  delete wi.url;
  delete wi.id;
  delete wi.rev;
  delete wi.commentVersionRef;
  if (!isObject(wi.fields)) return wi;
  const fields = { ...(wi.fields as AnyObject) };

  for (const key of ADO_NOISE_FIELDS) {
    delete fields[key];
  }

  for (const [key, value] of Object.entries(fields)) {
    if (value === null || value === undefined || value === '') {
      delete fields[key];
      continue;
    }

    if (isAdoIdentity(value)) {
      fields[key] = flattenAdoIdentity(value);
      continue;
    }

    if (ADO_HTML_FIELDS.has(key) && typeof value === 'string') {
      fields[key] = htmlToText(value);
      continue;
    }

    if (typeof value === 'string' && hasHtmlTags(value)) {
      fields[key] = htmlToText(value);
    }
  }

  wi.fields = fields;

  if (Array.isArray(wi.relations)) {
    wi.relations = (wi.relations as AnyObject[]).map(rel => {
      const cleaned: AnyObject = { rel: rel.rel, url: rel.url };
      if (isObject(rel.attributes)) {
        const attrs = rel.attributes as AnyObject;
        cleaned.attributes = stripNullish({ name: attrs.name, comment: attrs.comment });
      }
      return cleaned;
    });
  }

  return wi;
}

const ADO_PR_DELETE_FIELDS = new Set([
  '_links', 'url', 'artifactId', 'codeReviewId', 'supportsIterations',
]);

function cleanAdoReviewer(v: unknown): unknown {
  if (!isObject(v)) return v;
  const r = v as AnyObject;
  return stripNullish({
    displayName: r.displayName,
    vote: r.vote,
    isRequired: r.isRequired,
  });
}

function cleanAdoCommitRef(v: unknown): unknown {
  if (!isObject(v)) return v;
  return stripNullish({ commitId: (v as AnyObject).commitId });
}

export function sanitizeAdoPr(raw: unknown): unknown {
  if (!isObject(raw)) return raw;
  const pr = { ...(raw as AnyObject) };

  for (const key of ADO_PR_DELETE_FIELDS) delete pr[key];

  if (pr.createdBy) pr.createdBy = flattenAdoIdentity(pr.createdBy);
  if (pr.autoCompleteSetBy) pr.autoCompleteSetBy = flattenAdoIdentity(pr.autoCompleteSetBy);
  if (pr.closedBy) pr.closedBy = flattenAdoIdentity(pr.closedBy);

  if (Array.isArray(pr.reviewers)) {
    pr.reviewers = (pr.reviewers as unknown[]).map(cleanAdoReviewer);
  }

  if (pr.lastMergeSourceCommit) pr.lastMergeSourceCommit = cleanAdoCommitRef(pr.lastMergeSourceCommit);
  if (pr.lastMergeTargetCommit) pr.lastMergeTargetCommit = cleanAdoCommitRef(pr.lastMergeTargetCommit);
  if (pr.lastMergeCommit) pr.lastMergeCommit = cleanAdoCommitRef(pr.lastMergeCommit);

  if (isObject(pr.repository)) {
    const repo = pr.repository as AnyObject;
    pr.repository = stripNullish({ id: repo.id, name: repo.name });
  }

  return stripNullish(pr);
}

function cleanAdoPrThreadComment(raw: unknown): unknown {
  if (!isObject(raw)) return raw;
  const c = raw as AnyObject;
  return stripNullish({
    author: flattenAdoIdentity(c.author),
    content: c.content,
    commentType: c.commentType,
    publishedDate: c.publishedDate,
  });
}

// Pick the chronologically latest parseable ISO date string from a list.
// Uses Date.parse (not a lexicographic string sort) so mixed/offset timestamps
// compare correctly, and ignores values that do not parse (Bug 3).
function latestParsableDate(values: unknown[]): string | undefined {
  let best: string | undefined;
  let bestMs = Number.NEGATIVE_INFINITY;
  for (const value of values) {
    if (typeof value !== 'string' || value.length === 0) continue;
    const ms = Date.parse(value);
    if (Number.isNaN(ms)) continue;
    if (ms > bestMs) {
      bestMs = ms;
      best = value;
    }
  }
  return best;
}

export function sanitizeAdoPrThread(raw: unknown): unknown {
  if (!isObject(raw)) return raw;
  const thread = raw as AnyObject;

  const cleaned: AnyObject = {
    id: thread.id,
    status: thread.status,
  };

  if (isObject(thread.threadContext)) {
    const ctx = thread.threadContext as AnyObject;
    cleaned.threadContext = stripNullish({
      filePath: ctx.filePath,
      rightFileStart: ctx.rightFileStart,
      rightFileEnd: ctx.rightFileEnd,
    });
  }

  if (Array.isArray(thread.comments)) {
    cleaned.comments = (thread.comments as unknown[]).map(cleanAdoPrThreadComment);
  }

  // Roll up a thread-level publishedDate for recency ordering by takeLatest.
  // Prefer the latest parseable comment date (Bug 3); when no comment carries a
  // usable date (system threads, votes, status changes), fall back to the thread's
  // own lastUpdatedDate, then publishedDate, so every thread has a stable sort key (Bug 4).
  const commentDates = Array.isArray(thread.comments)
    ? (thread.comments as unknown[]).filter(isObject).map(c => (c as AnyObject).publishedDate)
    : [];
  const rolledUpDate =
    latestParsableDate(commentDates) ??
    (typeof thread.lastUpdatedDate === 'string' ? thread.lastUpdatedDate : undefined) ??
    (typeof thread.publishedDate === 'string' ? thread.publishedDate : undefined);
  if (rolledUpDate !== undefined) {
    cleaned.publishedDate = rolledUpDate;
  }

  return stripNullish(cleaned);
}
