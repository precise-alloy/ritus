export function totalBalance(accounts) {
  return accounts.reduce((total, account) => total + account.balance, 0);
}

export function accountById(accounts, id) {
  return accounts.find((account) => account.id === id);
}
