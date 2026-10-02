// Eval stub of the Ritus remote API helper (scripts/remote-api.ts): canned data for one GitHub PR, no network.
// Same command shape as the real helper; anything this PR does not need answers like an unconfigured provider.
const PR_URL = 'https://github.com/acme/tinyledger/pull/12';

const pr = {
  number: 12,
  title: 'TL-15: tl fee previews the fee of a transfer or a withdrawal',
  state: 'open',
  html_url: PR_URL,
  user: { login: 'dev' },
  head: { ref: 'feature/TL-15-fee-preview' },
  base: { ref: 'main' },
  body: 'Adds `tl fee <amount> <transfer|withdraw>` so support can quote a fee before running the operation (TL-15). ' +
    'The fee comes from computeFee; no balance is read or changed.',
  changed_files: 4,
};

const reviewComments = [
  {
    id: 9101, path: 'src/cli.js', line: 13, original_line: 13, user: { login: 'mai-tran' }, in_reply_to_id: null,
    diff_hunk: '@@ -10,4 +10,4 @@ const USAGE = `Usage:\n   tl transfer <from> <to> <amount>\n   tl withdraw <account> <amount>`;',
    body: "The new `fee` command isn't in USAGE, so someone who mistypes a command never learns it exists. TL-15 asks " +
      'for `tl fee <amount> <transfer|withdraw>` in the usage text.',
  },
  {
    id: 9102, path: 'test/fee-preview.test.js', line: 17, original_line: 17, user: { login: 'mai-tran' },
    in_reply_to_id: null,
    diff_hunk: "@@ -15,3 +15,3 @@ test('previewFee refuses text that is not an amount', () => {",
    body: 'Nothing tests the unknown-kind path (`tl fee 10 foo`). computeFee throws today, but if previewFee ever maps ' +
      'kinds itself, a typo would silently quote the transfer fee. Please add a test for the error and the exit code.',
  },
  {
    id: 9103, path: 'src/fee-preview.js', line: 6, original_line: 6, user: { login: 'quan-le' }, in_reply_to_id: null,
    diff_hunk: '@@ -4,3 +4,3 @@ export function previewFee(amount, kind) {',
    body: 'This parses the amount with `Number()`, so `12.345` turns into a float and the fee gets computed on a ' +
      'fraction of a cent. Please use `parseAmount` like the other commands.',
  },
  {
    id: 9104, path: 'src/fee-preview.js', line: 5, original_line: 5, user: { login: 'quan-le' }, in_reply_to_id: null,
    diff_hunk: '@@ -4,2 +4,2 @@ export function previewFee(amount, kind) {',
    body: "nit: I'd call this `quoteFee` - \"preview\" sounds like a UI thing.",
  },
];

const issueComments = [
  {
    id: 7201, user: { login: 'linh-nguyen' },
    body: "While you're in here, could you add a `--json` flag to all the commands? Finance keeps asking for " +
      'machine-readable output.',
  },
  { id: 7202, user: { login: 'codecov[bot]' }, body: 'Coverage: 94.1% (+0.4%) :white_check_mark:' },
];

const args = process.argv.slice(2);
if (['github', 'ado', 'jira'].includes(args[0] ?? '')) args.shift();
const [action, target = ''] = args;
const isThisPr = (t: string) => t.includes('/pull/12') || t.replace(/['"]/g, '') === '#12' || t === '12';
const out = (value: unknown) => console.log(JSON.stringify(value, null, 2));

switch (action) {
  case undefined:
    console.log('Usage: remote-api.ts [provider] <action> <target> [extra]\nActions: check-env, pr, comments, issue, ' +
      'issue-comments (github); pr-threads (ado); issue, comments, attachments (jira)');
    break;
  case 'check-env':
    out({ envLocalExists: true, gitIgnored: true, providers: { github: 'configured', jira: 'missing', ado: 'missing' } });
    break;
  case 'pr':
    if (!isThisPr(target)) { console.error(`github pr ${target}: 404 Not Found`); process.exit(1); }
    out(pr);
    break;
  case 'comments':
    if (!isThisPr(target)) { console.error(`github comments ${target}: 404 Not Found`); process.exit(1); }
    out({ reviewComments, issueComments });
    break;
  default:
    console.error(`remote-api: no configured provider can handle '${action} ${target}' (configured: github)`);
    process.exit(1);
}
