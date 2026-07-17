# Skip Reasons

address-feedback classifies every PR comment before acting on it. A comment is **kept (actionable)** only when it
survives all four challenge tests below; otherwise it is skipped under exactly one category. Each category carries a
definition and a disposition, orthogonal to the comment's author or tone.

## Keep bar - the four challenge tests

Keep a comment only when it passes ALL four. Failing any one test skips it under the matching category.

1. **Concrete** - it requests a specific change, not a musing, a question, or a hypothetical.
2. **Correct** - its premise holds against the actual code, provable at `file:line`.
3. **In scope** - addressing it falls within this PR's stated intent and diff.
4. **Grounded** - it is backed by a correctness issue or a documented project convention, not personal preference.

## Skip categories

| category       | What it catches                                                                          | Disposition       |
|----------------|------------------------------------------------------------------------------------------|-------------------|
| `noise`        | Praise, acknowledgment, LGTM / +1, bot / CI / lint / coverage output, system comments     | auto-skip         |
| `resolved`     | Thread already resolved or closed, or the last reply is the author's own fix              | auto-skip         |
| `incorrect`    | The reviewer misread the diff; the concern's premise is false (cite the proof)            | challenged-skip   |
| `out-of-scope` | A valid point, but outside this PR - belongs in a follow-up ticket                        | challenged-skip   |
| `subjective`   | Style or preference with no correctness impact and no backing convention                  | challenged-skip   |
| `speculative`  | A hypothetical "what if" with no concrete, testable change requested                      | challenged-skip   |
| `question`     | Asks for rationale or discussion and requests no change                                   | challenged-skip   |

## Dispositions

- **auto-skip** - report as a collapsed count in the summary. No reply and no veto are needed; these carry no
  actionable signal.
- **challenged-skip** - surface at the approval gate with the reason and a ready-to-paste PR reply. The developer
  may veto any challenged-skip to move it back into the keep list before fixes start.

## Tie-break

When more than one category fits, the most defensible skip wins:
`incorrect` > `out-of-scope` > `subjective` > `speculative` > `question`.
