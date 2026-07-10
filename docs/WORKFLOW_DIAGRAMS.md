# Workflow Diagrams

> **AI agents: do NOT read this file during workflow execution.** These diagrams are for human
> onboarding and reference only. The authoritative process lives in the skill files - follow those.

Visual reference for the Ritus workflow process. All diagrams use Mermaid syntax.

## 1. Main Workflow

Entry points, triage branches, and the path to completion.

```mermaid
flowchart TD
    Input([User provides input]) --> InputType{Input type?}

    InputType -->|"Vague idea"| BS["brainstorm"]
    InputType -->|"Clear requirement / ticket"| TR["triage"]
    InputType -->|"Bug report"| DB["debug"]
    InputType -->|"Review changes / PR"| CR["pr-review 🤖 standard-model subagent"]
    InputType -->|"Fix PR review comments"| AF["address-feedback"]

    BS --> UserPicks{"User picks\napproach?"}
    UserPicks -->|"Explore more"| BS
    UserPicks -->|"Approved"| TR

    TR --> Class{Classification}

    Class -->|TRIVIAL| Direct["Implement directly\n(no task file)"]
    Direct --> SelfVerify["Build + test ✅"]
    SelfVerify --> Report{"Report to user"}
    Report -->|"Done"| TrivialDone(["🧑 human commits"])
    Report -->|"Follow-up changes"| InputType

    Class -->|SIMPLE| GT["ticket-review\n(STANDARD/EPIC → requirement-analysis 🤖)"]
    Class -->|STANDARD| GT
    Class -->|EPIC| GT

    GT --> HumanReview{"🧑 Human reviews\nreview document?"}
    HumanReview -->|"Adjust"| GT
    HumanReview -->|"Approve"| HumanTasks{"🧑 Human reviews\ntask files?"}
    HumanTasks -->|"Adjust"| GT
    HumanTasks -->|"Approve"| Loop["Task execution loop\n(see Diagram 2)"]

    Loop --> AllDone(["All tasks verified"])
    AllDone --> CR

    CR --> Verdict{Verdict?}
    Verdict -->|"Approve ✅"| WrapUp["wrap-up\n(promote exploration, verify docs)"]
    WrapUp --> HumanFinal{"🧑 Human reviews diff"}
    HumanFinal -->|"Finalize"| Done(["Commits + pushes"])
    Done -->|"PR has review comments"| AF
    HumanFinal -->|"Follow-up changes"| InputType
    Verdict -->|"Request changes"| FixTask["Create SIMPLE fix task\nfrom review findings"]
    FixTask --> FixExec["main thread walks fix TODO:\ndispatch execute-task, then verify-task"]
    FixExec --> CR

    AF --> AFRound["Address-feedback round\n(see Diagram 4)"]
    AFRound --> AFDone(["🧑 Human reviews\n+ pushes"])
    AFDone -->|"More review comments"| AF

    DB --> DBPhases["4-phase investigation\n(see Diagram 3)"]
    DBPhases --> DBInvestigationApproval{"🧑 User approves\ninvestigation + fix?"}
    DBInvestigationApproval -->|"Adjust"| DBPhases
    DBInvestigationApproval -->|"Approve · TRIVIAL"| DBTriv["Apply inline + self-verify\n🧑 user commits"]
    DBInvestigationApproval -->|"Approve · SIMPLE+"| DBFix["Apply the fix\n🤖 execute-task subagent\n(case file = task artifact)"]
    DBFix --> DBVerify["verify-task 🤖 cheap model\n(fresh subagent)"]
    DBVerify --> CR
```

**Legend:** 🧑 = human-in-the-loop gate. 🤖 = runs as a dedicated subagent with specified model.

## 2. Task Execution Loop

The execute → verify cycle with parallel group support and retry on failure.

```mermaid
flowchart TD
    Start(["Execution plan from\nticket-review"]) --> NextGroup["Pick next group"]

    NextGroup --> GroupType{"Group type?"}
    GroupType -->|"Parallel"| ParExec["Main thread dispatches\nmultiple execute-task subagents\nsimultaneously"]
    GroupType -->|"Sequential"| SeqExec["Main thread dispatches\nsingle execute-task subagent"]

    ParExec --> ParVerify["dispatch verify-task 🤖\nfresh subagent per task"]
    SeqExec --> SeqVerify["dispatch verify-task 🤖\nfresh subagent per task"]

    ParVerify --> Check{"All tasks\nin group PASS?"}
    SeqVerify --> Check

    Check -->|"PASS ✅"| MoreGroups{"More groups\nin plan?"}
    Check -->|"FAIL ❌"| Fix["Fix gaps → re-verify\nfailed tasks only"]
    Fix --> Check

    MoreGroups -->|"Yes"| NextGroup
    MoreGroups -->|"No"| Done(["All tasks verified\n→ pr-review"])
```

### Verify-task detail (per task)

```mermaid
flowchart TD
    Task(["Single task"]) --> DoneWhen{"DONE WHEN\nconditions?"}

    DoneWhen -->|"Diff-checkable"| DiffCheck["Verify at file:line"]
    DoneWhen -->|"Command-checkable"| CmdCheck["Run build/test/lint"]

    DiffCheck --> Scope{"Scope clean?\nCONTEXT + DOC UPDATE\n+ test files"}
    CmdCheck --> Scope

    Scope -->|"Yes"| Standards{"Standards\ngates pass?"}
    Scope -->|"Violation"| Fail

    Standards -->|"Yes"| QA{"QA file\nchecks pass?"}
    Standards -->|"Fail"| Fail(["FAIL ❌\nwith specific gaps"])

    QA -->|"Yes"| P2{"Phase 2:\nAdversarial review?"}
    QA -->|"Fail"| Fail

    P2 -->|"Fault injection\nImplicit contract changes\nRegression risk\nSecurity quick check"| P2Result{"Issues found?"}
    P2Result -->|"No"| Pass(["PASS ✅\nwith evidence"])
    P2Result -->|"Yes"| Fail
```

## 3. Debug Investigation Flow

4-phase investigation before any fix attempt.

```mermaid
flowchart TD
    Bug([Bug reported]) --> P1

    subgraph "Phase 1 - Root Cause Investigation (hard gate)"
        P1["Read error messages\nstack traces, line numbers"]
        P1 --> P1b["Reproduce the bug\nconfirm exact conditions"]
        P1b --> P1c["Check recent changes\ngit log + git diff"]
        P1c --> P1d["Gather evidence at\ncomponent boundaries"]
        P1d --> P1e["Trace data flow\nbackward from bad value"]
        P1e --> RCGrade{"Root cause\nconfidence?"}
        RCGrade -->|"Confirmed"| P2
        RCGrade -->|"Deduced"| P2
        RCGrade -->|"Hypothesized"| P1f["Gather more evidence\nbefore proceeding"]
        P1f --> P1
    end

    subgraph "Phase 2 - Pattern Analysis (hard gate)"
        P2["Find working examples\nin same codebase"]
        P2 --> P2b["Compare working vs broken\nline by line"]
        P2b --> P2c["Identify differences\n+ map dependencies"]
    end

    P2c --> P3

    subgraph "Phase 3 - Hypothesis & Testing (hard gate)"
        P3["Form single hypothesis\nclearly stated, specific"]
        P3 --> P3b["Test minimally\none variable at a time"]
        P3b --> P3c{"Hypothesis\nconfirmed?"}
        P3c -->|"Yes"| ProposedFix["Proposed fix + regression test\n(root cause confirmed)"]
        P3c -->|"No"| P3d["New hypothesis\ndo NOT layer fixes"]
        P3d --> P3
    end

    ProposedFix --> DBInvestigationApproval{"🧑 User approves\nproposed fix?"}
    DBInvestigationApproval -->|"Adjust"| P3
    DBInvestigationApproval -->|"Approve"| Size{"Fix size?\n(triage criteria)"}
    Size -->|"TRIVIAL"| Inline["Apply inline + self-verify\n(build + test)"]
    Inline --> TrivDone(["Report - 🧑 user commits\n(commit message = root cause)"])
    Size -->|"SIMPLE+"| P4

    subgraph "Phase 4 - SIMPLE+: case file, then dispatch the fix"
        P4["Write investigation case file\nProposed Fix = STEPS · Regression Test = DONE WHEN"]
        P4 --> P4b["Apply the fix\n🤖 execute-task subagent (tdd red-green)"]
        P4b --> P4c["Verify\n🤖 verify-task subagent (fresh, independent)"]
        P4c --> P4d{"PASS?"}
        P4d -->|"FAIL"| Escalation{"Circuit breaker\ntripped?"}
        Escalation -->|"No"| P4b
        Escalation -->|"Yes"| Stop(["🧑 STOP - architectural problem\nwrite DECISION, discuss with user"])
    end

    P4d -->|"PASS"| CR(["→ pr-review\n🤖 standard-model subagent"])
```

## 4. Address-Feedback Round

The PR-feedback fix round: filter comments, fix, verify, optionally re-review, then report the fixes for the user to review and commit locally.

```mermaid
flowchart TD
    Start(["PR review comments\n(from address-feedback)"]) --> AFFilter["Filter actionable comments\n🧑 user approves list"]
    AFFilter --> AFTask["Generate fix task\n(round N)"]
    AFTask --> AFExec["main thread walks fix TODO:\ndispatch execute-task, then verify-task"]
    AFExec --> AFRecheck{"pr-review\nre-check?"}
    AFRecheck -->|"Yes"| AFReview["pr-review 🤖 standard-model subagent"]
    AFReview --> AFVerdict{"Verdict?"}
    AFVerdict -->|"Approve"| AFWrapUp["wrap-up\n(promote exploration, verify docs)"]
    AFVerdict -->|"Request changes"| AFExec
    AFRecheck -->|"No / Skip"| AFCommit["Report fixes\n+ suggested commit message"]
    AFWrapUp --> AFCommit
    AFCommit --> AFDone(["🧑 Human reviews, commits + pushes\nmore comments → re-run address-feedback"])
```

**Legend:** 🧑 = human-in-the-loop gate. 🤖 = runs as a dedicated subagent with specified model.

## 5. Context and Model Architecture

What runs in which context, with which model.

```mermaid
flowchart LR
    subgraph "Orchestrator Session (inherits user's model)"
        A["CLAUDE.md\n+ start-ritus skill\n+ docs/PROJECT_CONTEXT.md\n(always loaded)"]
        B["brainstorm / triage\n/ ticket-review"]
        D["debug\n(investigation)"]
        E["address-feedback\n(PR comment fixes)"]
    end

    subgraph "Fresh Subagent - per triage model/effort"
        C["execute-task skill 🤖\n+ standards skills"]
    end

    subgraph "Fresh Subagent - cheap model"
        V["verify-task skill 🤖\nStandards loaded conditionally by skill"]
    end

    subgraph "Fresh Subagent - standard model"
        R["pr-review skill 🤖\nStandards loaded conditionally by skill"]
    end

    subgraph "Fresh Subagent - per triage"
        RA["requirement-analysis skill 🤖\nread-heavy analysis, drafts review doc"]
    end

    B -- "STANDARD/EPIC: dispatch analysis" --> RA
    RA -- "review doc + findings" --> B
    B -- "dispatch per task" --> C
    C -- "dispatch per task" --> V
    V -- "PASS / FAIL" --> B
    B -- "all tasks verified" --> R
    R -- "Approve / Request changes" --> B
    E -- "dispatch fix task" --> C
```

## 6. Standards Loading Matrix

Which standard skills load for which types of work.

```mermaid
flowchart TD
    Task([Task to execute]) --> Check{"What does\nthe task touch?"}

    Check -->|"Any code change"| CC["code-conventions\n+ docs/CODE_CONVENTIONS.md"]
    Check -->|"New service / endpoint\n/ worker / bug fix"| TP["testing-policy\n+ docs/TEST_CONVENTIONS.md"]
    Check -->|"New business logic\n/ API endpoint / bug fix"| TDD["tdd\n(red-green-refactor)"]
    Check -->|"Auth / billing / migration\n/ tenant / infra / contracts"| SEC["security"]
    Check -->|"STANDARD or EPIC"| DOD["definition-of-done"]

    CC --> Loaded(["All applicable skills\nloaded before implementation"])
    TP --> Loaded
    TDD --> Loaded
    SEC --> Loaded
    DOD --> Loaded
```

## 7. File Ownership and Loading

What loads when, and who owns each file.

```mermaid
flowchart TD
    subgraph "Always loaded (session start)"
        CL["CLAUDE.md / copilot-instructions.md\n🧑 user-created in target project"]
        AG["start-ritus skill\n📦 workflow plugin"]
        PC["docs/PROJECT_CONTEXT.md\n🔄 rendered from .yml"]
    end

    subgraph "On-demand (skill activation)"
        SK["19 on-demand skills\n📦 workflow plugin"]
    end

    subgraph "Subagent dispatch (defined in skills)"
        VT["verify-task subagent\n📦 cheap model"]
        CR["pr-review subagent\n📦 standard model"]
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

    CL -->|"highest priority"| AG
    CL -->|"instructs read"| PC
    AG -->|"auto-routes to"| SK
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
