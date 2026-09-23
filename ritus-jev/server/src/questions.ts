// Every question sent to Jev. Keep each one a single, literal, atomic judgment (see TypeSafe
// "Jev 1.13 jaggedness"): name the state field it judges in backticks and put boundary cases in criteria.
import { choice, noul, type ChoiceQuestion, type NoulQuestion } from "@typesafe-ai/sdk";

type Options = Record<string, string | null>;

function withNone(ids: readonly string[], none: string): Options {
  const options: Options = {};
  for (const id of ids) options[id] = null;
  options.none = none;
  return options;
}

const MATCH = {
  true: "It implements, defines, configures, tests, documents, or reports exactly what `query` asks about.",
  false: "It is unrelated, or it only mentions similar names or words without addressing `query`.",
};

export const locateQuestions = {
  best(ids: readonly string[]): ChoiceQuestion<Options> {
    return choice(
      "Which block in `blocks` most directly addresses `query` - the place a developer would open first?",
      withNone(ids, "No block in `blocks` addresses `query`."),
    );
  },
  block(id: string): NoulQuestion {
    return noul(`Does \`blocks.${id}\` directly address \`query\`?`, MATCH);
  },
  candidate(): NoulQuestion {
    return noul("Does `candidate` directly address `query`?", MATCH);
  },
};

export const checkQuestions = {
  where(claim: string, ids: readonly string[]): ChoiceQuestion<Options> {
    return choice(
      { claim, question: "Which item in `evidence` is the strongest evidence for or against `claim`?" },
      withNone(ids, "No item in `evidence` relates to `claim`."),
    );
  },
  supported(claim: string): NoulQuestion {
    return noul(
      { claim, question: "Does the code or text in `evidence` show that `claim` is true?" },
      {
        true: "`evidence` explicitly implements or states what `claim` says.",
        false: "`evidence` does not show it, shows only part of it, or shows something different.",
      },
    );
  },
  contradicted(claim: string): NoulQuestion {
    return noul(
      { claim, question: "Does the code or text in `evidence` show something that conflicts with `claim`?" },
      {
        true: "`evidence` implements or states behavior that is incompatible with `claim`.",
        false: "Nothing in `evidence` conflicts with `claim`.",
      },
    );
  },
};

export type PresetName = "failure_kind" | "review_comment" | "change_risk" | "change_scope";

export interface Preset {
  mode: "single" | "multi";
  /** `{item}` becomes the backticked item path; `{label}` becomes a multi-label predicate. */
  question: string;
  labels: Record<string, string>;
  needsContext?: boolean;
}

export const PRESETS: Record<PresetName, Preset> = {
  failure_kind: {
    mode: "single",
    question: "What kind of failure does the command output in {item} show?",
    labels: {
      assertion_mismatch: "A test ran and an expectation or assertion failed (expected versus actual values).",
      compile_or_type_error: "Code failed to compile, type-check, transpile, or parse.",
      runtime_exception: "An uncaught exception, crash, panic, or stack trace during execution.",
      timeout_or_hang: "A test or process exceeded a time limit, hung, or was killed for taking too long.",
      environment_or_config: "A missing tool, file, environment variable, permission, or port, or a misconfiguration.",
      dependency_or_network: "Package installation or resolution, a version conflict, or a network or registry failure.",
      lint_or_format: "Linter, formatter, or style-check violations.",
      other: "None of the other categories describes the output, or the output shows no failure.",
    },
  },
  review_comment: {
    mode: "single",
    question:
      "Which category best describes the pull-request review comment in {item}? When `context` is present it states the pull request's intent.",
    labels: {
      requests_change: "Asks for a specific, concrete change to code, tests, or docs, backed by a correctness issue or a stated convention.",
      question: "Asks for rationale, clarification, or discussion and requests no change.",
      subjective: "Suggests a style or preference change with no correctness issue and no cited convention.",
      speculative: "Raises a hypothetical 'what if' concern without a concrete, testable change.",
      out_of_scope: "Makes a valid request that falls outside the pull request's stated intent.",
      noise: "Praise, acknowledgement, LGTM or +1, bot, CI, lint, or coverage output, or a system message.",
    },
  },
  change_risk: {
    mode: "multi",
    question: "Does the change or text in {item} {label}?",
    labels: {
      auth_session_token: "touch authentication, sessions, tokens, or credential verification",
      payment_billing: "touch payment, billing, pricing, or invoicing logic",
      db_migration: "add or change a database migration or schema",
      tenant_isolation: "touch tenant, workspace, or per-user data isolation or access scoping",
      infra_runtime_config: "change infrastructure, deployment, CI, runtime, or environment configuration",
      shared_contract: "change a type, interface, API, or schema that other modules or services consume",
      secrets_handling: "add, read, log, or transmit secrets or credentials",
    },
  },
  change_scope: {
    mode: "single",
    needsContext: true,
    question: "How does the change in {item} relate to the task described in `context`?",
    labels: {
      in_scope: "It directly implements what `context` asks for.",
      supporting: "It is a test, documentation, or configuration change needed for what `context` asks for.",
      out_of_scope: "It is unrelated to `context`, such as a refactor, a drive-by fix, or an unrelated feature.",
    },
  },
};

export const CUSTOM_QUESTION = {
  single: "Which label best describes {item}?",
  multi: "Does {item} match this description: {label}?",
};

export function renderQuestion(template: string, itemRef: string, label?: string): string {
  const withItem = template.includes("{item}") ? template.replaceAll("{item}", itemRef) : `${template} Judge ${itemRef}.`;
  return label === undefined ? withItem : withItem.replaceAll("{label}", label);
}

export function classifyChoice(question: string, labels: Record<string, string>): ChoiceQuestion<Options> {
  return choice(question, { ...labels });
}

export function classifyNoul(question: string): NoulQuestion {
  return noul(question);
}
