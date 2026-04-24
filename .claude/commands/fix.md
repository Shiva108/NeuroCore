---
description: Apply selected suggestions with minimal, safe edits and run the narrowest relevant validation.
---

# Fix

Apply the selected suggestion or suggestions from `$ARGUMENTS`.

## Rules

- Keep edits tightly scoped to the requested suggestions.
- Preserve existing behavior unless the suggestion explicitly changes behavior.
- Skip ambiguous items and report why.
- Do not run destructive git commands.
- For docs and prompt files, prefer wording, structure, and path fixes over broad rewrites unless the suggestion explicitly calls for one.

## Validation Strategy

Choose validation based on repo reality, not hardcoded assumptions.

### Docs-only changes

- skip tests
- optionally run a markdown or link check if the repo already has one

### Source or config changes

Detect the narrowest existing validation command, for example:

- targeted test files when a matching test framework exists
- the repo's standard test command from `Makefile`, `package.json`, `pyproject.toml`, `justfile`, or documented scripts
- focused lint or typecheck commands when they are already part of the project

If no formal automation exists yet, run the smallest practical syntax or execution check and say what remains unverified.
For docs or prompt-only edits, a careful consistency reread is an acceptable validation step when no markdown tooling exists.

## Output Format

```text
Fix Result
──────────────────────────────────────────
Applied: <n>
Skipped: <n>
Files: <comma-separated file list>
Validation: <what was run or why it was skipped>
```
