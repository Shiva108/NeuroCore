---
description: Analyze an error, failure path, or reliability issue in a target file, module, or workflow and apply focused fixes.
---

# Error Analysis and Fix

Target: `$ARGUMENTS`

If no target is provided, ask the user which file, module, path, or failing workflow should be analyzed.

## Goal

Identify why the target fails, where errors are mishandled or hidden, and apply minimal fixes that improve correctness, visibility, and recovery behavior.

If the target is a prompt, doc, or workflow description rather than executable code, treat the failure as instruction drift or an ambiguous operator path and fix that directly.

## Phase 1: Reproduce and Map

1. Identify the failing behavior from the user request, logs, tests, or code comments.
2. Find the relevant source files, tests, and entry points.
   For docs or prompt failures, also find the neighboring guidance files that define the intended workflow.
3. Map each error surface, including:
   - thrown exceptions
   - ignored return values
   - swallowed errors
   - retry loops with no exit condition
   - missing timeouts
   - missing validation before downstream work
   - state updates that can partially fail

For each issue, capture:

```text
FILE:
LOCATION:
FAILURE TYPE:
CURRENT HANDLING:
IMPACT:
```

## Phase 2: Classify

Prioritize fixes in this order:

1. execution-halting failures with no useful message
2. silent failures or partial success states
3. data-loss or corruption risks
4. weak retry/backoff behavior
5. missing test coverage for known failure cases

## Phase 3: Apply Fixes

Use the smallest safe changes that improve the target behavior.

Prefer:

- explicit error reporting
- guarded fallbacks
- clearer branching around expected failures
- early validation
- targeted tests that pin the failure mode

Avoid:

- unrelated refactors
- speculative abstractions
- broad rewrites unless the current design makes a narrow fix impossible

## Phase 4: Validate

Detect the repo's existing validation path before running checks.

Preferred order:

1. focused test file or test pattern covering the target
2. project test command from repo tooling
3. relevant lint/typecheck command if the change affects syntax or interfaces

If the repo has no defined automation yet, validate with the narrowest available executable check and say what could not be verified.

## Output

Report:

- the root cause
- the files changed
- the fix strategy
- the validation run
- any remaining risk or follow-up work
