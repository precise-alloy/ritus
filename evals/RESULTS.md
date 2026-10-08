# Ritus evaluation results

## 2.1.2 vs 3.0.0

The `v2-vs-v3` round (`python evals\harness\build.py round --show v2-vs-v3`; iteration 26 in the harness workspace) ran 23 scenarios in 13 groups, Ritus 2.1.2 (`git:fcbd5d5`) against Ritus 3.0.0 (the `plugin/` tree), 3 runs each - 138 runs, graded by scripts and by 17 blind judge bundles that mix both arms. An outcome assertion checks what the developer gets; a process assertion checks a Ritus mechanic, and several of those exist only in 3.0.0. Every number below comes from [`results/v2-vs-v3/scores.md`](results/v2-vs-v3/scores.md), which also has each scenario, and from [`benchmark.json`](results/v2-vs-v3/benchmark.json); [`analyst.json`](results/v2-vs-v3/analyst.json) has the full reading.

### All groups

| Measure | 2.1.2 | 3.0.0 |
| --- | ---: | ---: |
| Runs | 69 | 69 |
| Outcome assertions passed | 359/441 (81.4%) | 427/441 (96.8%) |
| Process assertions passed | 55/111 (49.5%) | 108/111 (97.3%) |
| Mean pass rate per run, all assertions | 76.7% | 96.6% |
| Mean tokens per run | 1,424,158 | 1,000,616 |
| Mean seconds per run | 240.0 | 167.7 |

### Groups

`0/0` means the group has no assertion of that kind.

#### execute (e1, e7)

| Measure | 2.1.2 | 3.0.0 |
| --- | ---: | ---: |
| Outcome | 25/51 | 51/51 |
| Process | 0/0 | 0/0 |
| Mean tokens per run | 750,631 | 668,226 |
| Mean seconds per run | 105.3 | 107.8 |

#### plan-simple (s11, s11r)

| Measure | 2.1.2 | 3.0.0 |
| --- | ---: | ---: |
| Outcome | 24/30 | 30/30 |
| Process | 15/39 | 38/39 |
| Mean tokens per run | 4,821,014 | 1,870,863 |
| Mean seconds per run | 688.4 | 285.4 |

#### plan-standard (s12, r1)

| Measure | 2.1.2 | 3.0.0 |
| --- | ---: | ---: |
| Outcome | 33/42 | 42/42 |
| Process | 15/21 | 20/21 |
| Mean tokens per run | 2,467,299 | 1,206,000 |
| Mean seconds per run | 392.6 | 235.5 |

#### address-feedback (p4)

| Measure | 2.1.2 | 3.0.0 |
| --- | ---: | ---: |
| Outcome | 18/21 | 21/21 |
| Process | 11/12 | 12/12 |
| Mean tokens per run | 3,045,382 | 1,772,582 |
| Mean seconds per run | 439.8 | 267.6 |

#### debug (p5)

| Measure | 2.1.2 | 3.0.0 |
| --- | ---: | ---: |
| Outcome | 21/24 | 23/24 |
| Process | 5/9 | 8/9 |
| Mean tokens per run | 1,666,026 | 2,738,257 |
| Mean seconds per run | 239.7 | 443.4 |

#### setup (f1)

| Measure | 2.1.2 | 3.0.0 |
| --- | ---: | ---: |
| Outcome | 14/21 | 21/21 |
| Process | 3/9 | 9/9 |
| Mean tokens per run | 845,317 | 765,154 |
| Mean seconds per run | 112.6 | 120.4 |

#### wrap-up (f2)

| Measure | 2.1.2 | 3.0.0 |
| --- | ---: | ---: |
| Outcome | 20/27 | 27/27 |
| Process | 3/6 | 6/6 |
| Mean tokens per run | 550,997 | 602,973 |
| Mean seconds per run | 112.5 | 119.2 |

#### test-quality (q1, q2)

| Measure | 2.1.2 | 3.0.0 |
| --- | ---: | ---: |
| Outcome | 59/66 | 63/66 |
| Process | 0/0 | 0/0 |
| Mean tokens per run | 1,011,180 | 688,789 |
| Mean seconds per run | 142.8 | 122.0 |

#### over-engineering (o1, o3)

| Measure | 2.1.2 | 3.0.0 |
| --- | ---: | ---: |
| Outcome | 26/30 | 30/30 |
| Process | 0/0 | 0/0 |
| Mean tokens per run | 880,715 | 670,551 |
| Mean seconds per run | 128.3 | 107.8 |

#### checks-standard (wv3, wr3)

| Measure | 2.1.2 | 3.0.0 |
| --- | ---: | ---: |
| Outcome | 29/33 | 31/33 |
| Process | 0/0 | 0/0 |
| Mean tokens per run | 704,840 | 746,097 |
| Mean seconds per run | 130.2 | 130.4 |

#### checks-epic (lv1, lr1)

| Measure | 2.1.2 | 3.0.0 |
| --- | ---: | ---: |
| Outcome | 35/36 | 33/36 |
| Process | 0/0 | 0/0 |
| Mean tokens per run | 983,233 | 956,963 |
| Mean seconds per run | 142.8 | 162.9 |

#### checks-fixes (fv3, ar1)

| Measure | 2.1.2 | 3.0.0 |
| --- | ---: | ---: |
| Outcome | 29/30 | 30/30 |
| Process | 0/0 | 0/0 |
| Mean tokens per run | 622,168 | 583,127 |
| Mean seconds per run | 98.2 | 109.6 |

#### verify-probes (xa1, xl3, xs2)

| Measure | 2.1.2 | 3.0.0 |
| --- | ---: | ---: |
| Outcome | 26/30 | 25/30 |
| Process | 3/15 | 15/15 |
| Mean tokens per run | 721,918 | 784,659 |
| Mean seconds per run | 319.6 | 127.7 |

### Clean runs

68 runs loaded a skill from outside their arm (see Caveats). Without them:

| Measure | 2.1.2 | 3.0.0 |
| --- | ---: | ---: |
| Runs | 41 | 29 |
| Outcome assertions passed | 221/274 (80.7%) | 207/213 (97.2%) |
| Process assertions passed | 26/53 (49.1%) | 28/29 (96.6%) |
| Mean tokens per run | 1,015,886 | 724,845 |
| Mean seconds per run | 208.1 | 125.7 |

The clean runs point the same way and by about as much. Per group they are too few to read (plan-simple and address-feedback have none), so the group tables above use all runs; `scores.md` has the clean tables too.

### What changed

- **Outcome.** 3.0.0 is ahead in 11 of the 13 groups. The largest gaps: in e1, 2.1.2's execute-task stops BLOCKED on a stale plan step in all 3 runs, and so fails the 8 assertions that need the code; in r1 and s12, 2.1.2's plans miss the rounding rule, the value rules in the task files and the typed-amount conflict; in setup, 2.1.2 asks for values the repository already shows; in wrap-up, its doc entries need the run to make sense and open follow-ups go unflagged. In reviews, 2.1.2's pr-review approved the planted bug in 2 of 3 wr3 runs and its verify-task passed the missing test in 2 of 3 xl3 runs; 3.0.0 gave the right verdict in all six.
- **Where 3.0.0 trails.** checks-epic and verify-probes, by 2 and 1 outcome assertions. Six 3.0.0 reviewer runs in wr3, lr1 and xl3 reported that the CLI accepts unknown flags. 3.0.0's security standard makes that a hard gate for any change that takes CLI flags; these scenarios' ground truth is older than the rule and says nothing else is wrong, so the judges counted false positives. 2.1.2 raised none. Narrowing the standard's flag check, or keeping it and updating those scenarios, is a decision for the maintainer. 3.0.0 also misses the trailing unknown option in xa1 in 1 of 3 runs.
- **Process.** Most process assertions check 3.0.0 mechanics 2.1.2 was not written for - SIMPLE work done inline after one approval, the probe rules, the CLAUDE.md routing block. The gap shows that 3.0.0 follows its own workflow, not that 2.1.2 does worse work; the outcome rows carry that comparison.
- **Cost.** 3.0.0 uses about 30% fewer tokens per run, and less time on average, though part of the time gap is one stalled 2.1.2 run (see Caveats). The saving sits in the main-thread planning flows (plan-simple, plan-standard, address-feedback); debug costs more in 3.0.0.
- **Same in both.** q1's floored-fee mutant survives every run's tests in both arms; o1, wv3, lv1 and ar1 get full marks in both.

### Caveats

- Prompts and the scripted developer replies are in English.
- n = 3 runs per scenario and arm.
- The arms are 2.1.2 at `git:fcbd5d5` and the uncommitted 3.0.0 `plugin/` tree at the time of the round. Executors and judges are gpt-5.5 subagents of Copilot CLI, not Claude.
- 68 of the 138 runs (40 of 69 for 3.0.0, 28 of 69 for 2.1.2) loaded at least one skill from the Ritus build installed in the same Copilot CLI - a 3.0.0 pre-release from 2026-09-29 that still had model routing - through the CLI's skill tool, instead of reading only their arm's copy: 44 in the run agent itself, 24 only in a subagent it started. The runtime tells subagents to invoke a matching skill, and that wins over the run's brief. `harness/contamination.py` lists the runs; "Clean runs" above leaves them out.
- Harness fixes made during the round, so that it measures what it should: p4 reads PR #12 through a stub helper in both arms (its two first launches ran without it and were discarded and rebuilt); the judge bundles take each scenario's latest ground truth; `f1.values` accepts a runtime profile with no routing setting - 3.0.0 removed model routing, and the old check failed 3.0.0 in all 3 runs for that alone (its f1 outcome was 18/21 before the fix).
- One 2.1.2 run (xs2 run 1) includes a 31-minute runtime stall between two tool calls - its model time was 116 seconds - which raises 2.1.2's mean seconds. Three runs had a subagent launch refused by the runtime's limit on concurrent agents: s11 run 3 and p5 run 2 of 3.0.0, r1 run 2 of 2.1.2.

## ritus-frontend 0.2.0 vs 1.0.0

The `frontend-compare` round (`python evals\harness\build.py round --show frontend-compare`; iteration 29 in the harness workspace) ran 11 TinyLedger Web scenarios in 7 groups, ritus-frontend 0.2.0 on Ritus 3.0.0 before D4 (`git:6c03d3a+git:7e57273:plugins/ritus-frontend`; D4 is the core change that adds companion load points at task generation, verify-task, pr-review and wrap-up) against ritus-frontend 1.0.0 on Ritus 3.0.0 with D4, both at the release commit (`git:4aa5e31+git:4aa5e31:plugins/ritus-frontend`), 3 runs each - 66 runs, graded by scripts, by Playwright and axe measurements of each built app, and by 3 blind judge bundles that mix both arms. Run agents and judges were gpt-5.5. All runs went one at a time in one dedicated Copilot app session, where both arms had the Playwright MCP, `playwright-cli`, the Figma stand-in and its `figma-design-to-code` guidance skill. 1.0 was iterated against a 0.2.0 baseline before this round, which reran both arms side by side. Every number below comes from [`results/frontend-compare/scores.md`](results/frontend-compare/scores.md), which also has each scenario, and from [`benchmark.json`](results/frontend-compare/benchmark.json); [`analyst.json`](results/frontend-compare/analyst.json) has the full reading.

### All groups

| Measure | 0.2.0 | 1.0.0 |
| --- | ---: | ---: |
| Runs | 33 | 33 |
| Outcome assertions passed | 191/207 (92.3%) | 205/207 (99.0%) |
| Process assertions passed | 45/48 (93.8%) | 48/48 (100.0%) |
| Mean pass rate per run, all assertions | 92.1% | 99.2% |
| Mean tokens per run | 1,782,166 | 1,901,422 |
| Mean seconds per run | 284.6 | 295.1 |

`contamination.py` flagged no run, so there is no clean-runs table here or in `scores.md`: every table covers all runs.

### Groups

The system-level groups run a whole flow and carry the comparison, because the two versions check UI at different workflow points: 0.2.0 at blocking gates before pr-review, 1.0 through a standard loaded into execute-task, verify-task and pr-review.

#### system-plan (up1)

| Measure | 0.2.0 | 1.0.0 |
| --- | ---: | ---: |
| Outcome | 18/24 | 24/24 |
| Process | 6/6 | 6/6 |
| Mean tokens per run | 2,166,475 | 1,410,100 |
| Mean seconds per run | 431.8 | 273.8 |

#### system-gate (ug1)

| Measure | 0.2.0 | 1.0.0 |
| --- | ---: | ---: |
| Outcome | 26/30 | 30/30 |
| Process | 3/3 | 3/3 |
| Mean tokens per run | 5,197,732 | 5,242,038 |
| Mean seconds per run | 816.1 | 688.9 |

#### system-simple (us1)

| Measure | 0.2.0 | 1.0.0 |
| --- | ---: | ---: |
| Outcome | 25/27 | 26/27 |
| Process | 12/12 | 12/12 |
| Mean tokens per run | 3,957,367 | 3,886,031 |
| Mean seconds per run | 616.1 | 535.5 |

#### system-standalone (uc1)

| Measure | 0.2.0 | 1.0.0 |
| --- | ---: | ---: |
| Outcome | 15/15 | 15/15 |
| Process | 3/3 | 3/3 |
| Mean tokens per run | 998,115 | 663,524 |
| Mean seconds per run | 121.6 | 117.0 |

The step probes start one workflow step from prepared documents and are reported apart.

#### probe-build (ub1)

| Measure | 0.2.0 | 1.0.0 |
| --- | ---: | ---: |
| Outcome | 39/39 | 39/39 |
| Process | 6/6 | 6/6 |
| Mean tokens per run | 1,273,349 | 1,452,316 |
| Mean seconds per run | 217.1 | 253.4 |

#### probe-verify (uv1, uv2, uv3, uv4, uv5)

| Measure | 0.2.0 | 1.0.0 |
| --- | ---: | ---: |
| Outcome | 53/57 | 56/57 |
| Process | 15/15 | 15/15 |
| Mean tokens per run | 1,069,142 | 1,431,983 |
| Mean seconds per run | 163.2 | 242.6 |

#### probe-review (ur1)

| Measure | 0.2.0 | 1.0.0 |
| --- | ---: | ---: |
| Outcome | 15/15 | 15/15 |
| Process | 0/3 | 3/3 |
| Mean tokens per run | 665,076 | 1,101,718 |
| Mean seconds per run | 111.3 | 165.2 |

### What changed

- **Where 1.0 wins.** It is ahead on outcome in 4 of the 7 groups and level in the rest. In up1, 0.2.0's plans left the 640px and 1024px breakpoints and WCAG 2.2 AA contrast out of Acceptance in all 3 runs; 1.0's named both every time. In ug1 runs 1 and 2, 0.2.0 fixed the mobile overflow and the unassociated label without reporting them and first mentioned them at wrap-up; 1.0 showed the developer both defects with a Request Changes before fixing them, in all 3 runs. In uv5, where the UI is correct, 0.2.0's verify-task failed runs 1 and 2 on testing grounds alone (5/9 against 9/9). In us1, 1.0's short plan named a browser check in 2 of 3 runs, 0.2.0's in 1 of 3.
- **Where 1.0 trails.** uv2, by one assertion: in run 3 its verify-task caught the planted overflow but also blocked on the heading's font weight of 700, the browser default for an h2, as not matching a token. 1.0's `verify.md` makes such a value a user note, so the rule was missed once in 3 runs. 0.2.0 raised no false UI defect in uv1-uv4; its uv5 FAIL verdicts (above) count as false defects there.
- **Process.** The only gap is ur1's browser check: both arms requested changes for the 404 and the raw color in every run, but 0.2.0's pr-review read only the code, and 0.2.0 has no browser instruction at pr-review. The gap measures a 1.0 mechanic; the verdicts are the same.
- **Cost.** 1.0 uses about 7% more tokens per run and 4% more time. The extra sits in the probes where 1.0 checks in a browser: verify costs 34% more tokens and review 66% more, with build 14% more. Planning and the standalone check cost about a third less in 1.0; the gate and simple flows cost about the same tokens and less time.
- **Same in both.** uc1 (FAIL naming the overflow and the label, no false defect) and ub1 (every build matches the Figma node and passes the browser checks) are full marks in both arms, as are uv1, uv3 and uv4: every planted defect was named.

### Caveats

- Prompts and the scripted developer replies are in English.
- n = 3 runs per scenario and arm.
- Run agents and judges are gpt-5.5, named explicitly on each launch because the host app's default subagent model changed during the 1.0 work; every run's usage lists gpt-5.5 as its only model.
- Every harness step of this round ran on Python 3.13.13; the switch from 3.13.12 happened in an earlier, unpublished 1.0 round.
- The 0.2.0 arm pins Ritus 3.0.0 at `git:6c03d3a`, before D4, the core change that lets a companion load its standard at task generation and names companion load items for verify-task, pr-review and wrap-up workers. 0.2.0's companion has fewer load points by design.
- probe-review's process gap is ur1's "used a browser" check, which 0.2.0 has no instruction for at pr-review; its 0/3 there says nothing about its review verdicts.
- Both arms had the same environment: the Playwright MCP, `playwright-cli`, the Figma stand-in and the guidance skill. A benchmark where each arm gets its own recommended environment is not part of this comparison. The 12 guidance-skill loads `contamination.py` counted are expected. Four runs (ug1 1.0 run 1, ug1 0.2.0 runs 2 and 3, us1 0.2.0 run 2) called the skill tool for names not installed in the session; the calls failed and nothing loaded.
- Fixture fixes made during the 1.0 iterations apply to both arms in this round: each world's docs carry its allocated dev port, and the new arm's `docs/FRONTEND.md` is committed in the world's history.
- One run was relaunched: ub1 0.2.0 run 3 was in flight during an app restart and was cancelled with no report. Its one added file was deleted, every built file still matched the build snapshot, and a fresh run replaced it.
