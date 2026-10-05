# Workflow Diagrams

> **AI agents: do NOT read this file during workflow execution.** These diagrams are for human
> onboarding and reference only. The authoritative process lives in the skill files - follow those.

Visual reference for the Ritus workflow process. All diagrams use Mermaid syntax.

## 1. Main Workflow

Entry points, levels, and the path to completion.

```mermaid
flowchart TD
    Input([User provides input]) --> InputType{Input type?}

    InputType -->|"New user / unsure / resuming"| SR["start-ritus\n(setup check, resume, orient)"]
    SR -->|"hands off"| InputType
    InputType -->|"Vague idea"| BS["brainstorm"]
    InputType -->|"Clear requirement / ticket"| TR["ticket-review\nsizes the work\n(plugins/ritus/skills/shared/levels.md)"]
    InputType -->|"Bug report"| DB["debug"]
    InputType -->|"Review changes / PR"| CR["pr-review 🤖 standard model subagent"]
    InputType -->|"Fix PR review comments"| AF["address-feedback"]

    BS --> UserPicks{"User picks\napproach?"}
    UserPicks -->|"Explore more"| BS
    UserPicks -->|"Approved"| TR

    TR --> Class{Level}

    Class -->|TRIVIAL| Direct["Implement directly\n(no plan, no task file)"]
    Direct --> SelfVerify["Build + test ✅"]
    SelfVerify --> Report{"Report to user"}
    Report -->|"Done"| TrivialDone(["🧑 human commits"])
    Report -->|"Follow-up changes"| InputType

    Class -->|SIMPLE| GT["ticket-review plans\nSIMPLE: reads the code inline\nSTANDARD/EPIC: analysis subagent 🤖 (read-only)\nmain thread writes plan + task files"]
    Class -->|STANDARD| GT
    Class -->|EPIC| GT

    GT --> HumanReview{"🧑 Human approves\nplan + breakdown?"}
    HumanReview -->|"Adjust"| GT
    HumanReview -->|"Approve · SIMPLE / STANDARD"| Loop["Task execution loop\n(see Diagram 2)"]
    HumanReview -->|"Approve · EPIC"| HumanTasks{"🧑 EPIC: human reviews\ntask files?"}
    HumanTasks -->|"Adjust"| GT
    HumanTasks -->|"Approve"| Loop

    Loop --> AllDone(["All tasks done"])
    AllDone --> CR

    CR --> Verdict{Verdict?}
    Verdict -->|"Approve ✅"| WrapUp["wrap-up\n(promote exploration, check docs,\ndraft PR description)"]
    WrapUp --> Comp["comprehension\n(advisory quiz before commit)"]
    Comp --> HumanFinal{"🧑 Human reviews diff"}
    HumanFinal -->|"Finalize"| Done(["Commits + pushes"])
    Done -->|"PR has review comments"| AF
    HumanFinal -->|"Follow-up changes"| InputType
    Verdict -->|"Request changes"| FixTask["Fix the findings\nmain thread if it implemented,\nelse fix task → execute-task 🤖"]
    FixTask -->|"re-review"| CR

    AF --> AFRound["Address-feedback round\n(see Diagram 4)"]
    AFRound --> AFDone(["🧑 Human reviews\n+ pushes"])
    AFDone -->|"More review comments"| AF

    DB --> DBInv["Investigate: reproduce, trace,\nevery caller, graded evidence\n(see Diagram 3)"]
    DBInv --> DBLogic{"Fix changes logic?"}
    DBLogic -->|"No · TRIVIAL"| DBTriv["Apply + self-check\n🧑 user commits"]
    DBLogic -->|"Yes"| DBApproval{"🧑 User approves\nroot cause + fix?"}
    DBApproval -->|"Adjust"| DBInv
    DBApproval -->|"Approve · SIMPLE"| DBInline["Main thread applies the fix\n(case file = task artifact)"]
    DBInline --> CR
    DBApproval -->|"Approve · STANDARD+"| DBFix["execute-task 🤖 subagent\n(case file = task artifact)"]
    DBFix --> DBVerify["verify-task 🤖\n(fresh subagent)"]
    DBVerify --> CR
```

**Legend:** 🧑 = human-in-the-loop gate. 🤖 = runs as a dedicated subagent.

## 2. Task Execution Loop

The execute → verify cycle: one task at a time, with a bounded fix loop.

```mermaid
flowchart TD
    Start(["Approved task files\nfrom ticket-review"]) --> Level{"Level?"}

    Level -->|"SIMPLE"| Inline["Main thread invokes execute-task\n(inline)"]
    Inline --> ToReview(["→ pr-review 🤖\nre-runs Acceptance + build/test"])

    Level -->|"STANDARD / EPIC"| Next["Next task, in plan order"]
    Next --> Exec["dispatch execute-task 🤖\nfresh subagent"]
    Exec --> Verify["dispatch verify-task 🤖\nfresh subagent"]
    Verify --> Check{"PASS?"}

    Check -->|"FAIL ❌"| Breaker{"Circuit breaker\ntripped?"}
    Breaker -->|"No"| Fix["Continue the task's executor\nwith the findings"]
    Fix --> Verify
    Breaker -->|"Yes"| Stop(["🧑 STOP - take it to the user"])

    Check -->|"PASS ✅"| More{"More tasks?"}
    More -->|"Yes"| Next
    More -->|"No"| Done(["All tasks verified\n→ pr-review"])
```

### Verify-task detail (per task)

```mermaid
flowchart TD
    Task(["Single task\n(fresh context, did not write it)"]) --> Acc{"Every Acceptance line\nproven by file:line\nor a command it ran?"}

    Acc -->|"Yes"| Contract{"Contract held?\nconstraints · non-goals\n· Produces / Consumes"}
    Acc -->|"No"| Fail(["FAIL ❌\nwith specific gaps"])

    Contract -->|"Yes"| Scope{"Every change accounted for\nby this task or an earlier one?"}
    Contract -->|"No"| Fail

    Scope -->|"Yes"| Bar{"Done bar?\nbuild · test · lint · standards"}
    Scope -->|"No"| Fail

    Bar -->|"Yes"| Docs{"Named docs\n(and QA file) updated?"}
    Bar -->|"No"| Fail

    Docs -->|"Yes"| Pass(["PASS ✅\nwith evidence"])
    Docs -->|"No"| Fail
```

## 3. Debug Investigation Flow

Find the cause before changing anything, then size the fix: a fix that adds no logic goes straight in, anything else
waits for the user.

```mermaid
flowchart TD
    Bug([Bug reported]) --> Read

    subgraph "Investigate"
        Read["Read the error exactly\nreproduce it"] --> Changed["Check what changed\ngit log + git diff"]
        Changed --> Trace["Trace the value back\nto the first broken contract"]
        Trace --> Callers["Grep every caller\nfind all paths through the fault"]
        Callers --> Hyp["Test one hypothesis at a time\n(competing hypotheses when unclear)"]
        Hyp --> Grade{"Root cause\nConfirmed?"}
        Grade -->|"Not yet"| Read
    end

    Grade -->|"Yes, or say what would confirm it"| Propose["Propose: root cause, affected paths,\nfix, regression test, level"]
    Propose --> Logic{"Fix changes logic?"}
    Logic -->|"No · TRIVIAL"| Triv(["Apply + build/test/lint\nreport - 🧑 user commits"])
    Logic -->|"Yes"| Gate{"🧑 User approves\nthe fix?"}
    Gate -->|"Adjust"| Propose
    Gate -->|"Approve"| Case["Write case file\nProposed Fix = decision · Regression Test = acceptance"]
    Case --> Level{"Level?"}
    Level -->|"SIMPLE"| Main["Main thread applies the fix\n(execute-task, inline)"]
    Main --> CR(["→ pr-review 🤖\nre-runs the regression test + build/test"])
    Level -->|"STANDARD / EPIC"| Exec["execute-task 🤖 subagent\n(failing test first)"]
    Exec --> Verify["verify-task 🤖 subagent\n(fresh, independent)"]
    Verify --> Pass{"PASS?"}
    Pass -->|"FAIL"| Breaker{"Circuit breaker\ntripped?"}
    Breaker -->|"No"| Exec
    Breaker -->|"Yes"| Esc(["🧑 STOP - a design problem\ncase file escalated, decided with the user"])
    Pass -->|"PASS"| CR2(["→ pr-review 🤖"])
```

## 4. Address-Feedback Round

Weigh each review comment against the code, get one approval for the fixes and the skips, fix, check independently,
then hand the user the diff, the reply drafts, and a commit message.

```mermaid
flowchart TD
    Start(["PR URL"]) --> Fetch["Fetch the PR and its open\nreview comments (remote-api helper)"]
    Fetch --> Weigh["Weigh each comment: check its premise\nat file:line, apply the keep bar"]
    Weigh --> Gate{"🧑 Approve fixes,\nskips + reply drafts"}
    Gate -->|"Veto a skip"| Weigh
    Gate -->|"Approve"| Task["Write fix task\nfix-review-round-N.md"]
    Task --> Level{"Level?"}
    Level -->|"SIMPLE"| Inline["Main thread fixes\n(execute-task, inline)"]
    Inline -->|"no re-review asked"| SVerify["verify-task 🤖"]
    Inline -->|"re-review asked"| Review["pr-review 🤖\n(re-runs the checks)"]
    Level -->|"STANDARD"| Exec["execute-task 🤖 subagent"]
    Exec --> Verify["verify-task 🤖"]
    Verify -->|"re-review asked"| Review
    SVerify --> Report["Report: fixes, check results,\nreply drafts, commit message"]
    Verify -->|"no re-review asked"| Report
    Review -->|"Approve"| WrapUp["wrap-up → comprehension"]
    WrapUp --> Report
    Report --> Done(["🧑 Human reviews, commits, posts replies\nnew comments → next round"])
```

**Legend:** 🧑 = human-in-the-loop gate. 🤖 = runs as a dedicated subagent.

## 5. Context Architecture

What runs in which context. Every subagent runs on the model the platform gives it - the session model unless the user
configured subagents otherwise; Ritus doesn't pick models (`plugins/ritus/skills/shared/dispatch.md` "Models").

```mermaid
flowchart LR
    subgraph "Main session (user's model)"
        A["CLAUDE.md\n+ docs/PROJECT_CONTEXT.md\n(always loaded)"]
        B["start-ritus / brainstorm\n/ ticket-review"]
        D["debug\n(investigation)"]
        E["address-feedback\n(PR comment fixes)"]
    end

    subgraph "Fresh Subagent - analysis, read-only"
        AN["analysis agent 🤖 (read-only)\nreads the ticket + code, reports;\nwrites no plan"]
    end

    subgraph "Fresh Subagent - one per task"
        C["execute-task skill 🤖\n+ shared standards\n(SIMPLE: main thread, inline)"]
    end

    subgraph "Fresh Subagent - after each task"
        V["verify-task skill 🤖\nStandards loaded conditionally by skill"]
    end

    subgraph "Fresh Subagent - whole change"
        R["pr-review skill 🤖\nStandards loaded conditionally by skill"]
    end

    B -- "STANDARD/EPIC: dispatch analysis" --> AN
    AN -- "ANALYSIS report" --> B
    B -- "writes plan + task files,\nthen dispatch per task" --> C
    C -- "DONE report" --> B
    B -- "dispatch verify per task" --> V
    V -- "PASS / FAIL" --> B
    B -- "all tasks verified" --> R
    R -- "Approve / Request changes" --> B
    E -- "fix task: inline at SIMPLE,\ndispatched at STANDARD" --> C
```

## 6. Standards Loading Matrix

Which shared standards (`plugins/ritus/skills/shared/standards/`) apply to which work. They are plain docs the workers
read, not skills.

```mermaid
flowchart TD
    Task([Task to execute or verify]) --> Check{"What does\nthe change touch?"}

    Check -->|"Any code change"| ENG["engineering.md\n+ docs/CODE_CONVENTIONS.md"]
    Check -->|"Any code change"| TST["testing.md\n+ docs/TEST_CONVENTIONS.md"]
    Check -->|"Auth / user data / outside input\n/ rendering / URL fetch / secrets\n/ billing / migration / contracts"| SEC["security.md"]

    ENG --> Loaded(["Read before implementing,\nre-applied by verify-task and pr-review"])
    TST --> Loaded
    SEC --> Loaded
```

## 7. File Ownership and Loading

What loads when, and who owns each file.

```mermaid
flowchart TD
    subgraph "Always loaded (session start)"
        CL["CLAUDE.md / AGENTS.md / copilot-instructions.md\n🧑 user-owned; setup adds\nthe Ritus routing block"]
        PC["docs/PROJECT_CONTEXT.md\n🔄 rendered from .yml"]
        DS["Skill names + descriptions\n📦 workflow plugin"]
    end

    subgraph "On-demand (skill activation)"
        AG["start-ritus - front door\n📦 workflow plugin"]
        SK["the other 13 skills\n📦 workflow plugin"]
    end

    subgraph "Subagent dispatch (defined in plugins/ritus/skills)"
        AN["analysis agent (ticket-review)\n📦 read-only"]
        VT["verify-task subagent\n📦 fresh after each task"]
        CR["pr-review subagent\n📦 fresh, whole change"]
    end

    subgraph "Project data (user-owned, never overwritten)"
        YML["docs/profiles/*.yml\n🧑 filled by setup + repo-scan"]
        COD["docs/CODE_CONVENTIONS.md\n🧑 filled by repo-scan"]
        TST["docs/TEST_CONVENTIONS.md\n🧑 filled by repo-scan"]
        ARCH["docs/ARCHITECTURE.md\n🧑 filled progressively"]
        DEC["docs/DECISIONS.md\n🧑 auto + manual"]
        LES["docs/LESSONS.md\n🧑 auto + manual"]
        CUT["docs/CUTOFF.md\n🧑 filled by repo-scan"]
        STK["docs/STAKEHOLDERS.md\n🧑 manual"]
        CHG["docs/CHANGELOG.md\n🧑 auto + manual"]
    end

    subgraph "Work artifacts (never touched by upgrades)"
        TASKS["docs/tasks/*\n📝 task files"]
        MEM["docs/memory/*\n📝 EPIC context"]
    end

    CL -->|"highest priority"| SK
    CL -->|"instructs read"| PC
    DS -->|"matched to the request"| AG
    DS -->|"matched to the request"| SK
    AG -->|"hands off to"| SK
    SK -->|"dispatches"| AN
    SK -->|"dispatches"| VT
    SK -->|"dispatches"| CR
    YML -->|"renders"| PC
    SK -->|"references"| COD
    SK -->|"references"| TST
    SK -->|"references"| LES
    SK -->|"references"| CUT
    SK -->|"references"| STK
    SK -->|"references"| CHG
```

**Legend:** 🧑 user-owned (preserved on upgrade) · 📦 workflow package (replaced on upgrade) · 🔄 rendered · 📝 work artifacts
