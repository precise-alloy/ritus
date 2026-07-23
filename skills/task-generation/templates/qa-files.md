# QA File Templates

Check QA mode in docs/PROJECT_CONTEXT.md section `## Team conventions` before generating QA files.

| QA mode     | STANDARD task                          | EPIC task                        | EPIC close                           |
|-------------|----------------------------------------|----------------------------------|--------------------------------------|
| `task`      | Generate `{name}.qa.md` alongside task | Generate `{name}.qa.md` per task | Generate `docs/qa/{epic-slug}.qa.md` |
| `epic-only` | No `.qa.md`                            | No `.qa.md`                      | Generate `docs/qa/{epic-slug}.qa.md` |
| `off`       | No QA docs                             | No QA docs                       | No QA docs                           |

**TRIVIAL and SIMPLE tasks never get `.qa.md` files regardless of QA mode.**

## Per-task `.qa.md` (STANDARD / EPIC - same name as task file)

```markdown
# QA - {task title}

Task: {relative task file path}
Generated: {YYYY-MM-DD}
Risk: low | medium | high - {one-line reason}

## Affected features

- {user-facing feature that could be impacted}

## Test scenarios

### Happy path

- [ ] {what should work normally after this change}

### Edge cases

- [ ] {boundary condition or error path to verify}

### Regression checks

- [ ] {existing feature to re-verify - not changed but at risk}

## Not affected (skip these)

{features or areas testers can safely skip - be explicit}

## Status

- [ ] Executor verified: QA IMPACT matches actual changes made
- [ ] Tester sign-off
```

## EPIC QA summary (`docs/qa/{epic-slug}.qa.md`) - generated at EPIC close

```markdown
# QA Summary - {EPIC name}

Branch: {git branch}
Closed: {YYYY-MM-DD}
Tasks: {N completed}

## Risk overview

| Task | Affected features | Risk |
| --- | --- | --- |
| {task name} | {features} | low \| medium \| high |

## Test first (high risk areas)

1. {feature} - {reason it's high risk}

## Full affected feature list

- {feature}

## Recommended test order

1. {highest risk}
2. {next}

## Known gaps / not covered

- {area not tested by this EPIC}
```
