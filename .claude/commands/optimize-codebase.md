---
description: Reduce duplication, dead code, and unnecessary complexity while preserving behavior and following the repo's existing tooling.
---

# Optimize Codebase

Optimize the repository with a discovery-first workflow.

## Arguments

Parse `$ARGUMENTS` for:

- an optional path scope
- `--phase <N>` to run one phase only
- `--dry-run` for analysis only

If no arguments are provided, analyze the full in-scope codebase.

## Objectives

Prioritize in this order:

1. remove dead code and stale artifacts
2. reduce obvious duplication
3. simplify high-friction code paths
4. preserve readability and behavior

## Phase 0: Detect Repo Reality

Before proposing or applying changes:

- identify the active languages and frameworks from files such as `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Gemfile`, or `pom.xml`
- identify the main source and test directories
- identify the project's existing lint, format, and test commands
- identify whether the repo is minimal or already has an established app structure

If the repo is still mostly a template with little or no source code, scale the work down to high-value structural and documentation improvements.
For a docs-first repo, include prompt drift, stale planning notes, duplicated guidance, and TODO hygiene in the analysis.

## Phase 1: Analysis

Look for:

- dead or unused code
- duplicate logic or repeated boilerplate
- oversized files or modules
- obsolete comments, debug output, or stale TODOs
- validation gaps that make future changes risky

Use the smallest set of tools needed to support the findings. Prefer repo-native checks where available.

If `--dry-run` is set, stop after this phase and report findings only.

## Phase 2: Safe Improvements

Apply only high-confidence changes first, such as:

- removing unused imports or obviously dead code
- deleting stale comments or debug statements
- tightening repetitive validation or error-handling code
- consolidating duplicated helper logic when the shared abstraction is clear

Do not make broad architectural changes unless the requested scope explicitly calls for them.

## Phase 3: Validation

After changes:

- run the narrowest relevant tests first
- run the repo's standard lint or typecheck commands if they exist
- report what was validated and what remains unverified

## Output

Summarize:

- what was optimized
- what was intentionally skipped
- evidence that behavior was preserved
- follow-up opportunities, if any
