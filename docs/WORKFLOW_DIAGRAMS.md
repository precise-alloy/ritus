# Workflow Diagrams

> **AI agents: do NOT read this file during workflow execution.** These diagrams are for human
> onboarding and reference only. The authoritative process lives in the skill files — follow those.

Visual reference for the Ritus workflow process. All diagrams use Mermaid syntax.

## 1. Main Workflow

Entry points, triage branches, and the path to completion.

```mermaid
flowchart TD
    Input([User provides input]) --> InputType{Input type?}

    InputType -->|"Vague idea"| BS["brainstorm"]
    InputType -->|"Clear requirement / ticket"| TR["triage"]
    InputType -->|"Bug report"| DB["debug"]
    InputType -->|"Review changes / PR"| CR["pr-review 🤖 sonnet subagent"]
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

    Class -->|SIMPLE| GT["ticket-review"]
    Class -->|STANDARD| GT
    Class -->|EPIC| GT

    GT --> HumanTasks{"🧑 Human reviews\ntask files?"}
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
    FixTask --> FixExec["execute-task subagent\n→ verify-task subagent"]
    FixExec --> CR

    AF --> AFFilter["Filter actionable comments\n🧑 user approves list"]
    AFFilter --> AFTask["Generate fix task\n(round N)"]
    AFTask --> AFExec["execute-task subagent\n→ verify-task subagent"]
    AFExec --> AFCommit["Local commit\n(no push)"]
    AFCommit --> AFDone(["🧑 Human reviews\n+ pushes"])
    AFDone -->|"More review comments"| AF

    DB --> DBPhases["4-phase investigation\n(see Diagram 3)"]
    DBPhases --> DBFix["Fix applied + tested\nin same session"]
    DBFix --> CR
```

**Legend:** 🧑 = human-in-the-loop gate. 🤖 = runs as a dedicated subagent with specified model.

## 2. Task Execution Loop

The execute → verify cycle with parallel group support and retry on failure.

```mermaid
flowchart TD
    Start(["Execution plan from\nticket-review"]) --> NextGroup["Pick next group"]

    NextGroup --> GroupType{"Group type?"}
    GroupType -->|"Parallel"| ParExec["Dispatch multiple\nexecute-task subagents\nsimultaneously"]
    GroupType -->|"Sequential"| SeqExec["Dispatch single\nexecute-task subagent"]

    ParExec --> ParVerify["verify-task 🤖 haiku\n(fresh subagent per task)"]
    SeqExec --> SeqVerify["verify-task 🤖 haiku\n(fresh subagent per task)"]

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

    Standards -->|"Yes"| P2{"Phase 2:\nAdversarial review?"}
    Standards -->|"Fail"| Fail(["FAIL ❌\nwith specific gaps"])

    P2 -->|"Fault injection\nContract changes\nRegression risk\nSecurity quick check"| P2Result{"Issues found?"}
    P2Result -->|"No"| Pass(["PASS ✅\nwith evidence"])
    P2Result -->|"Yes"| Fail
```

## 3. Debug Investigation Flow

4-phase investigation before any fix attempt.

```mermaid
flowchart TD
    Bug([Bug reported]) --> P1

    subgraph "Phase 1 — Root Cause Investigation (hard gate)"
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

    subgraph "Phase 2 — Pattern Analysis (hard gate)"
        P2["Find working examples\nin same codebase"]
        P2 --> P2b["Compare working vs broken\nline by line"]
        P2b --> P2c["Identify differences\n+ map dependencies"]
    end

    P2c --> P3

    subgraph "Phase 3 — Hypothesis & Testing (hard gate)"
        P3["Form single hypothesis\nclearly stated, specific"]
        P3 --> P3b["Test minimally\none variable at a time"]
        P3b --> P3c{"Hypothesis\nconfirmed?"}
        P3c -->|"Yes"| P4
        P3c -->|"No"| P3d["New hypothesis\ndo NOT layer fixes"]
        P3d --> P3
    end

    subgraph "Phase 4 — Fix & Verify"
        P4["Create failing test\nmust FAIL before fix"]
        P4 --> P4b["Apply single fix\nat root cause"]
        P4b --> P4c["Run test → must PASS\n+ full suite + build"]
    end

    P4c --> Escalation{"3+ fix\nattempts failed?"}
    Escalation -->|"Yes"| Stop(["🧑 STOP\nDocument architectural finding\ndiscuss with user"])
    Escalation -->|"No"| Done(["Report fix\n🧑 user commits"])
    Done --> CR(["→ pr-review\n🤖 sonnet subagent"])
```

## 4. Context and Model Architecture

What runs in which context, with which model.

```mermaid
flowchart LR
    subgraph "Orchestrator Session (inherits user's model)"
        A["CLAUDE.md\n+ start-ritus skill\n+ docs/PROJECT_CONTEXT.md\n(always loaded)"]
        B["brainstorm / triage\n/ ticket-review"]
        C["execute-task\n+ standards skills"]
        D["debug\n(investigation)"]
        E["address-feedback\n(PR comment fixes)"]
    end

    subgraph "Fresh Subagent — haiku"
        V["verify-task skill 🤖\nStandards loaded conditionally by skill"]
    end

    subgraph "Fresh Subagent — sonnet"
        R["pr-review skill 🤖\nStandards loaded conditionally by skill"]
    end

    C -- "dispatch per task" --> V
    V -- "PASS / FAIL" --> C
    C -- "all tasks verified" --> R
    R -- "Approve / Request changes" --> C
    E -- "dispatch fix task" --> C
```

## 5. Standards Loading Matrix

Which standard skills load for which types of work.

```mermaid
flowchart TD
    Task([Task to execute]) --> Check{"What does\nthe task touch?"}

    Check -->|"Any code change"| CC["code-conventions\n+ docs/CODE_CONVENTIONS.md"]
    Check -->|"New service / endpoint\n/ worker / bug fix"| TP["testing-policy\n+ docs/TEST_CONVENTIONS.md"]
    Check -->|"New business logic\nor bug fix"| TDD["tdd\n(red-green-refactor)"]
    Check -->|"Auth / billing / migration\n/ tenant / infra / contracts"| SEC["security"]
    Check -->|"STANDARD or EPIC"| DOD["definition-of-done"]

    CC --> Loaded(["All applicable skills\nloaded before implementation"])
    TP --> Loaded
    TDD --> Loaded
    SEC --> Loaded
    DOD --> Loaded
```

## 6. File Ownership and Loading

What loads when, and who owns each file.

```mermaid
flowchart TD
    subgraph "Always loaded (session start)"
        CL["CLAUDE.md / copilot-instructions.md\n🧑 user-created in target project"]
        AG["start-ritus skill\n📦 workflow plugin"]
        PC["docs/PROJECT_CONTEXT.md\n🔄 rendered from .yml"]
    end

    subgraph "On-demand (skill activation)"
        SK["18 skills\n📦 workflow plugin"]
    end

    subgraph "Subagent dispatch (defined in skills)"
        VT["verify-task subagent\n📦 haiku"]
        CR["pr-review subagent\n📦 sonnet"]
    end

    subgraph "Project data (user-owned, never overwritten)"
        YML["docs/profiles/*.yml\n🧑 filled by setup + repo-scan"]
        COD["docs/CODE_CONVENTIONS.md\n🧑 filled by repo-scan"]
        TST["docs/TEST_CONVENTIONS.md\n🧑 filled by repo-scan"]
        ARCH["docs/ARCHITECTURE.md\n🧑 filled progressively"]
        DEC["docs/DECISIONS.md\n🧑 auto + manual"]
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
```

**Legend:** 🧑 user-owned (preserved on upgrade) · 📦 workflow package (replaced on upgrade) · 🔄 rendered · 📝 work artifacts
