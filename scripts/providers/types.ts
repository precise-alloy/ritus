export type RequestHeaders = Record<string, string>;

export type HttpError = Error & {
  statusCode?: number;
  responseBody?: unknown;
};

export type ActionHandler = (target: string, extra?: string) => Promise<unknown>;

export type Provider = {
  name: string;
  label: string;
  requiredEnvKeys: readonly string[];
  actions: Record<string, ActionHandler>;
  usageLines: (scriptCmd: string) => string[];
  exampleLines: (scriptCmd: string) => string[];
};

export type EnvKeyStatus = { name: string; present: boolean };

export type ProviderEnvStatus = {
  name: string;
  label: string;
  keys: EnvKeyStatus[];
  ok: boolean;
};

export type EnvCheckResult = {
  envLocalPath: string;
  envLocalExists: boolean;
  providers: ProviderEnvStatus[];
  keys: EnvKeyStatus[];
  missing: string[];
  ok: boolean;
};
