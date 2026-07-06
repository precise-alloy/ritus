export type RequestHeaders = Record<string, string>;

export type HttpError = Error & {
  statusCode?: number;
  responseBody?: unknown;
};

export type EnvMapping = Record<string, string>;

export type ProviderInstanceConfig = {
  type: string;
  name: string;
  keyPrefixes?: string[];
  env?: EnvMapping;
};

export type ProviderInstance = {
  provider: Provider;
  config: ProviderInstanceConfig;
  envMapping: EnvMapping;
};

export type ActionHandler = (target: string, extra?: string, envMapping?: EnvMapping) => Promise<unknown>;

export type Provider = {
  name: string;
  label: string;
  requiredEnvKeys: readonly string[];
  defaultEnvMapping: EnvMapping;
  actions: Record<string, ActionHandler>;
  canHandleTarget: (action: string, target: string) => boolean;
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
