# Review Document Template

**File path:**

- If ticket URL provided → `<ticket-reviews-path>/<TICKET_ID>-review.md` (per docs/PROJECT_CONTEXT.md `## Documentation layout`)
- If plain requirement → `<ticket-reviews-path>/<branch-slug>-review.md`

````markdown
# <TICKET_ID or Branch Slug>: <Summary>

> Last Reviewed: <YYYY-MM-DD HH:mm UTC>
> Status: <ticket status or "In Progress">
> Type: <issue type or "Feature / Bugfix / Refactor">

## 1. Questions, Assumptions & Decisions

### Open Questions (Needs Answer)

Items below may need product owner confirmation before the dev team can provide estimation.

- [ ] <Clear question that needs PO/stakeholder answer>
- [ ] <Another question>

### Assumptions

- <Assumption made and reasoning>

### Decisions

- <Decision made based on ticket comments or user input>

## 2. Proposed Implementation

### Approach

<Brief description of the overall technical approach and rationale.>

### Solution Details

<Detailed explanation of how the implementation will work, including:>

- Architecture decisions
- Data flow (use Mermaid diagrams when visual representation aids understanding)
- Integration points
- Error handling strategy

### Diagrams (if applicable)

When the implementation involves complex flows, component interactions, or state transitions, include Mermaid diagrams
to visualize them. Use ```mermaid fenced code blocks.

Examples of when to include diagrams:

- Sequence diagrams for multi-step API/service interactions
- Flowcharts for complex decision logic
- State diagrams for status/workflow transitions
- Class diagrams for new model relationships

## 3. Detailed Task List

### 3.1 Models & Configuration

| #   | File Path         | Action          | Description                  |
| --- | ----------------- | --------------- | ---------------------------- |
| 1   | `path/to/file.cs` | Modify / Create | What needs to change and why |

### 3.2 Services & Business Logic

| #   | File Path | Action | Description |
| --- | --------- | ------ | ----------- |

### 3.3 Integration

| #   | File Path | Action | Description |
| --- | --------- | ------ | ----------- |

### 3.4 Controllers & Endpoints

| #   | File Path | Action | Description |
| --- | --------- | ------ | ----------- |

### 3.5 UI & Frontend

| #   | File Path | Action | Description |
| --- | --------- | ------ | ----------- |

### 3.6 Wiring & DI

| #   | File Path | Action | Description |
| --- | --------- | ------ | ----------- |

### 3.7 Unit Tests

| #   | Test File Path                   | Tests to Add                         | Covers            |
| --- | -------------------------------- | ------------------------------------ | ----------------- |
| 1   | `Project.Tests/path/TestFile.cs` | `MethodName_Scenario_ExpectedResult` | Brief description |

Test file location convention: see docs/PROJECT_CONTEXT.md section `## Test location conventions`.

### 3.8 Documentation

| #   | Doc File Path          | Action          | Description      |
| --- | ---------------------- | --------------- | ---------------- |
| 1   | `docs/feature-name.md` | Create / Update | What to document |

Guidelines:

- Existing docs are intentionally brief - **expand them** with implementation details, usage examples, and architecture
  notes when touching related features.
- Create new docs for entirely new features or workflows.
- Include: purpose, how it works, configuration, edge cases, and troubleshooting tips.

## 4. QA Verification Notes

### Test Scenarios

| #   | Scenario        | Steps                       | Expected Result      |
| --- | --------------- | --------------------------- | -------------------- |
| 1   | <Scenario name> | <Steps to reproduce/verify> | <What QA should see> |

### Edge Cases to Verify

- <Edge case 1>
- <Edge case 2>

### Regression Areas

- <Area that might be affected and should be regression-tested>

### Test Data Requirements

- <Any specific data setup needed for QA>

## 5. Risks & Concerns

### Security

- <Security concern if any, or "None identified">

### Compliance

- <Compliance concern if any, or "None identified">

### Performance

- <Performance concern if any, or "None identified">

### Breaking Changes

- <Breaking change risk if any, or "None identified">

## 6. Visual References

<!-- Only include this section if the ticket has image attachments analyzed in Step 3.4 (requirement-analysis) -->

| # | Image | What I see | What ticket expects | Gap |
|---|---|---|---|---|
| 1 | <image description or filename> | <specific elements observed> | <expected behavior from ticket> | <difference> |
````
