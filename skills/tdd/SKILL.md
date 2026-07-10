---
name: tdd
description: Loaded automatically by execute-task for new business logic or bug fixes - enforces red-green-refactor cycle. Do not invoke standalone
argument-hint: Provide the behavior or bug being implemented and the expected failing test scenario
user-invocable: false
---

# Test-Driven Development

## When to use

Load this skill alongside `execute-task` when the task involves:

- New business logic (services, helpers, domain functions)
- Bug fixes (regression test must exist before fix)
- New API endpoints (auth + validation tests)

**Do NOT load** for: refactors with no behavior change, config-only changes, documentation, or pure UI layout changes
without logic.

## Iron law

**NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.**

Wrote code before the test? Delete it. Start over. This is not optional.

## The cycle

### Red - write a failing test

1. Write the simplest test that describes the expected behavior.
2. Run it. It MUST fail.
3. If it passes, the test is wrong - it's not testing anything new. Rewrite it.

Load `testing-policy` for what type of test to write and project-specific conventions (framework, naming, mocking
strategy). If a framework-specific testing skill is installed, load it for concrete patterns and examples.

### Green - make it pass

1. Write the **minimal** code to make the test pass.
2. Run the test. It MUST pass.
3. Do not add features, handle edge cases, or refactor yet. Just make the test green.

### Refactor - clean up

1. Improve the code without changing behavior.
2. Run tests after each change. They must stay green.
3. Extract helpers, rename for clarity, remove duplication - but only if tests still pass.

### Repeat

Add the next test for the next behavior. One test per red-green-refactor cycle, one behavior at a time.

## For bug fixes

1. Write a test that **reproduces the bug** - it must fail with the current code.
2. Verify it fails for the right reason (the bug, not a typo in the test).
3. Fix the bug - the test turns green.
4. This test is now a permanent regression guard.

## Anti-patterns

| Trap | Reality |
|---|---|
| "I'll write the tests after" | You'll write tests that confirm your code, not tests that verify behavior |
| "This test can't fail" | Then it's not testing anything. Make it test a specific behavior. |
| "I need to implement first to know what to test" | You need to know the BEHAVIOR first. That's the test. |
| "Let me write all the tests upfront" | Write ONE test. Make it pass. Then the next. |
| "The test is too simple" | Simple tests catch real bugs. Complex tests catch complex bugs and create complex maintenance. |
| "I'll test the integration, not the unit" | Test the unit first. Integration tests don't pinpoint failures. |

## Hard rules

1. Every new function/method has at least one test written BEFORE the implementation.
2. Every bug fix has a regression test written BEFORE the fix.
3. Tests must fail before the implementation proves they test something real.
4. One test per red-green-refactor cycle - do not batch.
5. Run tests after every change - red, green, refactor, all require a test run.

## Handoff

- **Report:** the standard applied to the parent skill's work.

