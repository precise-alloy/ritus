import { card } from './components/card.js';
import { accountById } from './lib/accounts.js';
import { transferFee } from './lib/fees.js';
import { formatAmount } from './lib/money.js';

const app = document.querySelector('#app');

function element(tag, options = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(options)) {
    if (key === 'className') {
      node.className = value;
    } else if (key === 'text') {
      node.textContent = value;
    } else {
      node.setAttribute(key, value);
    }
  }
  node.append(...children);
  return node;
}

async function loadAccounts() {
  const response = await fetch('/api/accounts');
  if (!response.ok) {
    throw new Error('Accounts could not be loaded.');
  }
  return response.json();
}

function renderShell(currentPath, main) {
  const accountsCurrent = currentPath.startsWith('/accounts');
  const transferCurrent = currentPath === '/transfer';
  const accountsLink = accountsCurrent
    ? { href: '/accounts', 'aria-current': 'page', text: 'Accounts' }
    : { href: '/accounts', text: 'Accounts' };
  const transferLink = transferCurrent
    ? { href: '/transfer', 'aria-current': 'page', text: 'Transfer' }
    : { href: '/transfer', text: 'Transfer' };
  app.replaceChildren(
    element('header', { className: 'site-header' }, [
      element('div', { className: 'site-header__inner' }, [
        element('a', { className: 'site-name', href: '/accounts', text: 'TinyLedger Web' }),
        element('nav', { 'aria-label': 'Primary' }, [
          element('a', accountsLink),
          element('a', transferLink),
        ]),
      ]),
    ]),
    main,
  );
}

function renderAccounts(accounts) {
  const grid = element('div', { className: 'account-grid' });
  for (const account of accounts) {
    const meta = element('div', { className: 'account-meta' }, [
      element('p', { className: 'label', text: 'Current balance' }),
      element('p', { className: 'amount', text: formatAmount(account.balance) }),
    ]);
    grid.append(card({ heading: account.name, headingLevel: 2, body: meta, href: `/accounts/${account.id}` }));
  }
  renderShell('/accounts', element('main', { className: 'content' }, [element('h1', { text: 'Accounts' }), grid]));
}

function renderAccount(account) {
  const rows = account.transactions.map((transaction) => element('tr', {}, [
    element('td', { text: transaction.date }),
    element('td', { text: transaction.description }),
    element('td', { text: formatAmount(transaction.amount) }),
  ]));
  const table = element('div', { className: 'table-wrap' }, [
    element('table', {}, [
      element('caption', { text: `${account.name} transactions` }),
      element('thead', {}, [element('tr', {}, [
        element('th', { scope: 'col', text: 'Date' }),
        element('th', { scope: 'col', text: 'Description' }),
        element('th', { scope: 'col', text: 'Amount' }),
      ])]),
      element('tbody', {}, rows),
    ]),
  ]);
  renderShell('/accounts', element('main', { className: 'content' }, [
    element('h1', { text: account.name }),
    element('p', { className: 'label', text: 'Current balance' }),
    element('p', { className: 'amount', text: formatAmount(account.balance) }),
    table,
  ]));
}

function renderTransfer(accounts) {
  const status = element('p', { className: 'status', role: 'status', 'aria-live': 'polite' });
  const from = accountSelect('from-account', accounts);
  const to = accountSelect('to-account', accounts);
  const amount = element('input', { id: 'amount', name: 'amount', type: 'text', inputmode: 'decimal', autocomplete: 'off' });
  const note = element('input', { id: 'note', name: 'note', type: 'text', maxlength: '140', autocomplete: 'off' });
  const feeValue = element('dd', { text: '—' });
  const totalValue = element('dd', { text: '—' });
  const panel = element('aside', { className: 'fee-panel', 'aria-labelledby': 'fee-preview-heading' }, [
    element('h2', { id: 'fee-preview-heading', text: 'Fee preview' }),
    element('dl', { className: 'fee-list' }, [
      element('div', {}, [element('dt', { text: 'Fee' }), feeValue]),
      element('div', {}, [element('dt', { text: 'Total' }), totalValue]),
    ]),
  ]);
  const form = element('form', { className: 'form-panel' }, [
    element('div', { className: 'field' }, [element('label', { for: 'from-account', text: 'From' }), from]),
    element('div', { className: 'field' }, [element('label', { for: 'to-account', text: 'To' }), to]),
    element('div', { className: 'field' }, [element('label', { for: 'amount', text: 'Amount' }), amount]),
    element('div', { className: 'field' }, [element('label', { for: 'transfer-note', text: 'Note (optional)' }), note]),
    element('button', { type: 'submit', text: 'Review transfer' }),
    status,
  ]);
  function updatePreview() {
    const cents = Math.round(Number(amount.value.trim()) * 100);
    if (!Number.isInteger(cents) || cents <= 0) {
      feeValue.textContent = '—';
      totalValue.textContent = '—';
      return;
    }
    const fee = transferFee(cents);
    feeValue.textContent = formatAmount(fee);
    totalValue.textContent = formatAmount(cents + fee);
  }
  amount.addEventListener('input', updatePreview);
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    status.className = 'status';
    const value = Number(amount.value.trim());
    if (!Number.isFinite(value) || value <= 0) {
      status.classList.add('status--error');
      status.textContent = 'Enter an amount greater than zero.';
      return;
    }
    if (from.value === to.value) {
      status.classList.add('status--error');
      status.textContent = 'Choose two different accounts.';
      return;
    }
    const fromAccount = accountById(accounts, from.value);
    const toAccount = accountById(accounts, to.value);
    status.classList.add('status--success');
    status.textContent = `Ready to review ${formatAmount(Math.round(value * 100))} from ${fromAccount.name} to ${toAccount.name}.`;
  });
  renderShell('/transfer', element('main', { className: 'content' }, [
    element('h1', { text: 'Transfer' }),
    element('div', { className: 'transfer-layout' }, [form, panel]),
  ]));
}

function accountSelect(id, accounts) {
  return element('select', { id, name: id }, accounts.map((account) => element('option', { value: account.id, text: account.name })));
}

async function start() {
  const path = window.location.pathname;
  const accounts = await loadAccounts();
  if (path === '/accounts') {
    renderAccounts(accounts);
    return;
  }
  if (path.startsWith('/accounts/')) {
    const account = accountById(accounts, path.split('/').pop());
    if (account) {
      renderAccount(account);
    }
    return;
  }
  if (path === '/transfer') {
    renderTransfer(accounts);
  }
}

start();
