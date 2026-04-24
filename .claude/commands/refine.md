---
description: Run repeated suggest-then-fix cycles until the current work is polished or the round limit is reached.
---

# Refine

Run iterative suggestion and cleanup rounds for the current session.

## Companion Commands

Use these companion files when available:

- `.claude/commands/suggest.md`
- `.claude/commands/fix.md`

If either file is missing, fall back to equivalent built-in behavior rather than failing the run.

## Arguments

Parse from `$ARGUMENTS`:

- `--rounds <N>` or a bare integer shorthand
- `--dry-run`
- `--scope <comma-separated-paths>`

Defaults:

- rounds: `3`
- max rounds: `10`
- scope: files touched in the current session

If there are no detectable session-touched files and no explicit `--scope`, stop and ask the user to provide scope rather than guessing.

## Workflow

### 1. Initialize

Print:

```text
Refine
──────────────────────────────────────────
Rounds:   <N>
Dry run:  yes | no
Scope:    <session files or explicit list>
```

### 2. Suggestion Round

Run the logic from `.claude/commands/suggest.md` for the current scope.

- collect actionable suggestions
- keep them ordered from smallest effort to largest
- deduplicate repeated suggestions across rounds

If there are zero suggestions, stop with reason `converged`.

### 3. Fix Round

If `--dry-run` is set, describe the intended changes without editing.

Otherwise:

- apply suggestions in order
- skip ambiguous or high-risk items
- run the narrowest relevant validation for touched files
- continue past individual skipped items rather than halting the whole round

For docs and prompt files, prioritize:

- stale paths or commands
- contradictory instructions
- missing repo-reality caveats
- formatting drift that hurts scanability

### 4. Convergence Check

Stop when:

- suggestions reach zero
- the round limit is hit
- the same suggestions repeat without progress

### 5. Final Summary

Print:

```text
Refine Complete
──────────────────────────────────────────
Rounds run:   <n>
Total fixes:  <n>
Stop reason:  converged | round limit | not converging
Files changed: <list>
Skipped fixes: <summary>
```

## Constraints

- Never make changes outside the active scope unless the user explicitly expands it.
- Never run destructive git commands.
- Documentation-only changes do not require tests unless the repo already has doc-specific validation.
