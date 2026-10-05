# Case file template

The fix's task file. The executor treats Proposed Fix as the decision already made and Regression Test as the
acceptance; the verifier and the reviewer check against both. Write it for someone who wasn't in the investigation.
Drop sections that would only say "none".

Path: `docs/tasks/{branch-slug}/investigation-{slug}.md`

```markdown
# Investigation: <issue summary>

Level: SIMPLE | STANDARD | EPIC - Date: <YYYY-MM-DD> - Ticket: <key or URL | none>
Status: todo <!-- the main thread sets implemented, then verified, as the fix goes; escalated if it can't converge -->

## Symptom

<The exact error, output, or behavior, and how to trigger it.>

## Root cause

Grade: Confirmed | Deduced | Hypothesized

<What is wrong and why, at `file:line`.>

## Evidence

- <finding> - Confirmed - `file:line` or the command and its output
- <finding> - Deduced - follows from <finding>

## Affected paths

<!-- Every caller or entry point that goes through the fault, including the ones the report didn't name. -->

- <path> - `file:line` - <how it is affected>

## Attempted fixes

| # | Tried | Result |
|---|---|---|

## Proposed Fix

<What changes and where: the one place the affected paths meet.>

## Regression Test

<The test that fails now and passes after the fix, one per affected path, and the command that runs it.>
```
