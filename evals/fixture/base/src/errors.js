// Domain errors carry a stable `code`; the CLI prints `Error: <message>` and exits 1.
export class LedgerError extends Error {
  constructor(code, message) {
    super(message);
    this.name = new.target.name;
    this.code = code;
  }
}

export class AccountNotFoundError extends LedgerError {
  constructor(accountId) {
    super('ACCOUNT_NOT_FOUND', `Account ${accountId} not found`);
    this.accountId = accountId;
  }
}

export class InsufficientFundsError extends LedgerError {
  constructor(accountId, balanceCents, requiredCents) {
    super('INSUFFICIENT_FUNDS', `Account ${accountId} has ${balanceCents} cents, needs ${requiredCents}`);
    this.accountId = accountId;
    this.balanceCents = balanceCents;
    this.requiredCents = requiredCents;
  }
}

export class InvalidAmountError extends LedgerError {
  constructor(input, reason) {
    super('INVALID_AMOUNT', `Invalid amount ${JSON.stringify(input)}: ${reason}`);
    this.input = input;
  }
}
