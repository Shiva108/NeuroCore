---
description: Generate actionable suggestions for files touched in the current session or for explicitly provided paths.
---

# Suggest

Generate practical, scoped suggestions for improving the current work.

## Scope

- default: files edited in this session
- optional: paths passed in `$ARGUMENTS`
- never suggest changes outside the active scope

If there are no detectable session-edited files and no explicit paths were provided, stop and ask the user to supply scope instead of guessing.

## Suggestion Rules

- prioritize correctness and reliability over style
- prefer small, high-impact changes first
- avoid speculative refactors unless there is concrete evidence
- return an empty list if nothing actionable is found
- for docs and prompt files, prioritize stale paths, outdated repo assumptions, unsafe instructions, and missing cross-file alignment

## Output Format

```text
Suggestions
──────────────────────────────────────────
1. <title> [Effort: small|medium|large]
   File: <path>
   Why: <short reason>
2. ...

Total: <n> suggestions
```

## Validation Hints

- for source changes, prefer suggestions that can be verified with focused tests or existing checks
- for docs-only files, avoid unnecessary test recommendations
- avoid suggesting new files unless they are clearly justified
