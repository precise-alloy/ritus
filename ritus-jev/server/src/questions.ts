// Every question sent to Jev. Keep each one a single, literal, atomic judgment (see TypeSafe
// "Jev 1.13 jaggedness"): name the state field it judges in backticks and put boundary cases in criteria.
import { choice, noul, type ChoiceQuestion, type Description, type NoulQuestion } from "@typesafe-ai/sdk";

type Options = Record<string, Description>;

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
  /** What kind of statement a claim is, so exact and mechanical checks run in code instead of the model. */
  kind(id: string): ChoiceQuestion<Options> {
    return choice(
      { question: `What kind of statement is \`claims.${id}\`?`, focus: "Classify what would make the statement true, not its topic." },
      {
        semantic: {
          what: "Whether it holds depends on what code or text means, says or does.",
          examples: [
            "`parseConfig` returns null for an empty file",
            "The dispatch contract resumes the producer for correction cycles",
            "No leftover wording such as \"fresh subagent\" contradicts the new rule",
          ],
        },
        literal: {
          what: "It asserts only that an exact quoted or backticked phrase appears, or does not appear, in files - nothing about what the text means.",
          not_for: "Statements about meaning, intent or contradiction that quote example phrases.",
          examples: ["The phrase \"spawn a fresh subagent\" is absent from dispatch.md", "`## Resume vs fresh` appears in dispatch.md"],
        },
        count: {
          what: "It asserts how many times something occurs or how many items exist.",
          examples: ["dispatch.md has exactly one `## Resume vs fresh` heading", "Three tests cover the parser"],
        },
        files: {
          what: "It asserts which files were changed, added or removed, or that changes are limited to certain files.",
          examples: ["Changes are limited to README.md and skills/debug/SKILL.md", "skills/debug/SKILL.md was modified"],
        },
        format: {
          what: "It asserts formatting or characters, such as list markers, casing, line length, or a character never appearing.",
          examples: ["The new text uses no em dash character", "Lists use hyphen markers"],
        },
      },
    );
  },
  compound(id: string): NoulQuestion {
    return noul(`Does \`claims.${id}\` combine two or more independent assertions that could each be true or false on its own?`, {
      true: "It joins separate conditions that could be checked one at a time, for example with 'and' or a list.",
      false: "It states one condition, even if that condition mentions several words or files.",
    });
  },
  polarity(id: string): ChoiceQuestion<Options> {
    return choice(`Does \`claims.${id}\` assert that the quoted phrase appears, or that it does not appear?`, {
      present: "The phrase appears, is included, is added, or exists.",
      absent: "The phrase does not appear, is removed, has no matches, or is gone.",
    });
  },
  fileForm(id: string): ChoiceQuestion<Options> {
    return choice(`What does \`claims.${id}\` assert about the files it names?`, {
      only_these: "Changes are limited to the named files; no other file changed.",
      includes: "The named files were changed, added or modified.",
      excludes: "The named files were not changed.",
    });
  },
  /** Citation-check shape: how one passage (named by its backticked state path) relates to `claim`. */
  relation(passage: string): ChoiceQuestion<Options> {
    return choice(`How does \`${passage}\` relate to \`claim\`?`, {
      supports: "The passage states the claim or directly implies that it is true.",
      contradicts: "The passage states the opposite of the claim or implies that it is false.",
      says_nothing: "The passage does not address what the claim asserts, either way.",
    });
  },
};

const SWEEP_MATCH = {
  true: "The passage itself states, describes or implements what `query` describes, in any wording.",
  false: "The passage only mentions, imports, calls or links to it, shares words with `query`, or describes something similar but different.",
};

export const sweepQuestions = {
  block(id: string): NoulQuestion {
    return noul(`Does \`blocks.${id}\` itself state or implement what \`query\` describes?`, SWEEP_MATCH);
  },
  passage(): NoulQuestion {
    return noul("Does `passage` itself state or implement what `query` describes?", SWEEP_MATCH);
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
  return choice(question, { ...labels } as Options);
}

export function classifyNoul(question: string): NoulQuestion {
  return noul(question);
}
