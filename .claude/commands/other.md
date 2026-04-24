---
description: Analyze the repository and recommend the highest-value next improvements, with an optional quick-win apply mode.
---

# Recommendations and Next Steps

Analyze the current repository and recommend practical improvements.

Focus area: `$ARGUMENTS` if provided.

## Argument Parsing

Support:

- free-form focus scope
- `--apply` to implement up to three high-confidence quick wins

If `--apply` is set, prefer small, low-risk fixes over broad refactors.
If the repo has no source tree yet, treat docs, prompt files, and task trackers as the primary quick-win surface.

## Analysis Steps

1. Inspect the current repository structure and recent activity when available.
2. Identify obvious gaps in:
   - tests
   - docs accuracy
   - configuration hygiene
   - project structure
   - developer workflow
3. Search for TODO-like markers only in directories that actually exist, such as `src/`, `tests/`, `docs/`, `.claude/commands/`, and future config or script folders.
4. Avoid recommending work that is already clearly in progress or already documented as intentional.
5. If `--apply` is set, implement only the safest validated quick wins within scope.
   In docs-first repos, that usually means wording fixes, path corrections, or consistency updates rather than new tooling.

## Output Format

Use these sections:

### 1. Quick Wins

Safe, high-confidence improvements that should take less than 30 minutes each.

### 2. Important Improvements

Higher-value changes that may take longer or need more care.

### 3. Nice-to-Have

Lower-priority or exploratory improvements.

For each item include:

- `What`
- `Where`
- `Why`

If `--apply` is set, append an `Applied` section listing:

- what was implemented
- what was skipped
- what validation ran
