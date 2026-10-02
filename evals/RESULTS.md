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
