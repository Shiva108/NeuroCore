---
description: Audit a file for drift against the current repository state and suggest or apply focused updates.
---

# Update

Audit one or more files against the current repository state and determine what needs to change.

Files: `$ARGUMENTS`

If no path is provided, ask the user for one or more paths.

## Step 0: Parse Arguments

Support:

- one or more `<path>` values required
- `--apply` to apply safe non-source-file updates after reporting them
- `--tdd-only` to output only follow-up `/tdd` prompts for source files

Resolve all provided paths before auditing:

- If a path is a directory, list relevant files and ask the user to narrow it down unless the request is clearly a batch refresh of that directory. In that case, audit the high-signal files within it and avoid duplicate work.
- If a path contains glob characters such as `*` or `?`, resolve the matches first. If there is exactly one match, continue. If there are multiple matches, present them and ask the user to choose.
- If multiple explicit file paths are provided, audit them one by one and keep the report grouped by file.
- If both a directory and files inside it are provided, prefer the explicit file list and use the directory only to discover missed high-signal peers.

## Step 1: Classify Each File

Detect one of:

- `command` for files under `.claude/commands/`
- `doc` for markdown or docs content outside the command folder
- `asset` for config, manifest, JSON, YAML, or TOML files
- `source` for code under `src/`, `tests/`, or another established source directory
- `other` for anything else

Print `File type detected: <type>` for each file.

## Step 2: Gather Current Context

Read only the files needed to audit each target accurately.

Examples:

- nearby docs or index files for documentation
- related command files for prompt structure
- referenced config or source files
- relevant tests for source files

Prefer repo reality over assumptions. If Git metadata is available, use it; otherwise rely on current filesystem context.

## Step 3: Look for Drift

Check for:

### A. Factual errors

- wrong paths
- wrong command names
- outdated file names
- stale counts, versions, or dates

### B. Missing coverage

- current behavior or files that the target does not mention

### C. Obsolete content

- references to removed or nonexistent files, workflows, or tools

### D. Structural drift

- missing sections or inconsistent layout relative to nearby peers

### E. Stale markers

- outdated "as of" notes, versions, or dated statements

## Step 4: Branch by Type

### 4a. Command

Produce a compact staleness report with exact replacements where possible.

When checking structure, compare against nearby command files under `.claude/commands/`, not external repos.

If `--apply` is set, apply safe command-file updates after reporting them.
Safe command-file updates include wording corrections, path fixes, structural alignment, missing repo-reality caveats, and removal of stale assumptions.

### 4b. Doc

Use the same report format and verify that linked paths and example commands still make sense for the current repo.

If `--apply` is set, apply safe documentation updates.
Safe documentation updates include correcting paths, clarifying current repo state, reconciling overlapping docs, and cleaning up malformed task notes.

### 4c. Asset

Use a precise staleness report and prefer minimal edits.

For critical manifests or config files, show exact proposed changes and ask for confirmation before writing if the edit could break project setup.

### 4d. Source

Do not auto-edit source files from this command. Instead produce:

1. a short staleness analysis
2. one or more ready-to-use `/tdd` prompts

Each `/tdd` prompt must include:

- the target file path
- the function, class, or behavior to change
- at least one concrete "should do X" statement

If `--tdd-only` is set, output only the `/tdd` prompt content.

### 4e. Other

Provide a best-effort report and do not auto-apply changes.

## Step 5: Summary

For multi-file runs, include a per-file summary first, then a short aggregate summary.

End with:

```text
Summary
─────────────────────────────────────────
File:     <path>
Type:     <type>
Findings: <total count>
Action:   <changes applied | review required | run /tdd>
Next step: <one concrete recommendation>
```

For multi-file runs, append:

```text
Batch Summary
─────────────────────────────────────────
Files audited: <n>
Files updated: <n>
Files requiring manual review: <n>
```

## Constraints

- Never guess corrections without evidence from the current repo
- Never auto-edit source files from this command
- If no staleness is found, say so explicitly
