---
description: Run a strict Red-Green-Refactor TDD workflow for a feature request or bug fix using the repository's existing conventions.
---

# Test-Driven Development Workflow

Task: `$ARGUMENTS`

If no task is provided, ask the user what feature or bug should be implemented with TDD.

If the request is documentation-only or design-only, stop and recommend `/update` or `/create-ssd-implementation` instead of forcing a test workflow.

## Mode Detection

Parse `$ARGUMENTS` for:

- `--quick` to skip the refactor and coverage phases
- `--dry-run` to stop after planning test cases

Classify the task as either:

- bug fix
- feature work

## Phase 0: Understand the Repo

Before writing tests:

1. identify the target behavior and likely implementation files
2. find existing tests for the same area
3. detect the active language, test framework, and runner from repo files such as `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, `Gemfile`, or `pom.xml`
4. inspect test conventions already used in the repo
5. reuse existing fixtures, helpers, factories, and test data when present

If the repo does not yet contain tests or tooling:

- follow the template structure
- choose the smallest conventional setup that fits the existing language only when implementation work is clearly in scope
- avoid inventing a runtime or framework just to satisfy the TDD ritual when the repo is still planning-only

## Phase 1: RED

### 1.1 Design test cases

For a bug fix:

- write one reproduction test first
- make sure it fails for the correct reason

For a feature:

- design happy-path, edge-case, and error-case tests before implementation

If `--dry-run` is set, print the planned test cases and stop.

### 1.2 Write failing tests

- place tests in the repo's existing test location, or under `tests/` if none exists yet
- keep one behavior per test
- match existing naming and assertion style

### 1.3 Verify failure

Run the narrowest matching test command and confirm the tests fail for the intended reason.

Do not proceed until the red phase is real.

## Phase 2: GREEN

- implement only enough code to make the new tests pass
- work in small batches
- run targeted tests first, then broader regression checks

Do not add untested behavior just because it seems helpful.

## Phase 3: REFACTOR

Skip this phase in `--quick` mode.

- improve naming, duplication, and clarity
- keep behavior unchanged
- rerun tests after each meaningful refactor

## Phase 4: Final Verification

Use repo-native validation where available:

- targeted tests
- full test suite
- lint or typecheck commands already used by the project

If coverage tooling exists, report coverage for the changed area. If not, say so without inventing a coverage workflow.

## Final Summary

Report:

- tests added or updated
- files changed
- validation run
- any remaining gaps or assumptions

## Rules

1. Never write implementation before a failing test.
2. Never change a test just to force green unless the test is genuinely wrong.
3. Keep cycles small.
4. Match existing repo conventions before introducing new ones.
