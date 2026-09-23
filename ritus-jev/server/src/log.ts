// stdout carries the MCP protocol, so every diagnostic goes to stderr.
const DEBUG = process.env.RITUS_JEV_DEBUG === "1";

export function logError(message: string): void {
  process.stderr.write(`ritus-jev: ${message}\n`);
}

export function logDebug(message: string): void {
  if (DEBUG) process.stderr.write(`ritus-jev[debug]: ${message}\n`);
}
