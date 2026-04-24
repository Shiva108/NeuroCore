---
description: Audit the repository for obsolete, misplaced, or unnecessary files and produce a ranked cleanup report.
---

# Project Cleanup Audit

Audit this repository for files and directories that are likely safe to remove, archive, or relocate.

Scope: `$ARGUMENTS` if provided, otherwise the entire repository.

Do not delete, move, or edit anything during the audit phase. Cleanup actions require explicit user approval after the report is presented.

## Protected Paths

Never recommend deleting or relocating these unless the user explicitly asks:

- `.git/`
- `.claude/`
- `docs/ssd/` when it is the active design source of truth
- `AGENTS.md`
- root `README*`
- top-level task trackers such as `todo.lst`
- `.env`, `.env.*`, and secret-bearing config files
- lockfiles that match the active package manager

If the workspace is not a Git repository, do not treat the absence of Git metadata as evidence that files are disposable.

## Goals

Prioritize:

1. Clearly disposable files
2. Files that are misplaced relative to the project template
3. Stale or unreferenced artifacts that deserve review
4. Large or unusual files that merit attention

If the repo is large, focus first on the root, `docs/`, `assets/`, `tests/`, and any top-level scripts or scratch files.

If the repo is still mostly documentation, prioritize stale planning notes, duplicate docs, temporary exports, and misplaced draft files over theoretical source-code cleanup.

## Phase 1: Gather Evidence

Use read-only inspection to collect findings.

### 1. Temp and generated artifacts

Look for patterns such as:

- `*.tmp`, `*.bak`, `*.orig`, `*.swp`, `*~`
- `.DS_Store`, `Thumbs.db`
- `__pycache__/`, `*.pyc`
- build output directories such as `dist/`, `build/`, `.coverage`, `htmlcov/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`
- `*.log` outside an intentional log directory

### 2. Misplaced project files

Flag files that would fit better elsewhere, for example:

- docs-like markdown files sitting at the repo root that belong in `docs/`
- sample data or images outside `assets/`
- tests outside `tests/`
- ad hoc scripts at the root that should move into a future `scripts/` folder

### 3. Empty or placeholder directories

Flag directories that are:

- empty
- contain only `.gitkeep`
- contain only placeholder files with no clear purpose

### 4. Stale or weakly connected files

Where possible, identify files that are:

- old relative to recent project activity
- referenced nowhere else in the repository
- clearly superseded by newer files

If the repo is a Git repository, prefer `git log` and `git ls-files` for age and tracked-state checks. If not, fall back to filesystem timestamps and reference analysis.
Do not recommend removing current planning artifacts only because no code has been created yet.

### 5. Large or unusual files

Call out:

- unexpectedly large binaries
- archives committed into source control
- generated outputs that do not belong in a template repository

## Phase 2: Classify Findings

Use these severity levels:

- `HIGH`: clearly disposable or clearly misplaced
- `MEDIUM`: likely unnecessary but worth a quick review
- `LOW`: optional cleanup or relocation
- `INFO`: notable observations only

## Phase 3: Report

Use this format:

```markdown
## Project Cleanup Audit Report

**Project**: [name] | **Date**: [today] | **Scope**: [path or repo]

### Summary

| Severity | Count |
| :------- | ----: |
| HIGH     |     X |
| MEDIUM   |     X |
| LOW      |     X |
| INFO     |     X |

### HIGH — Recommended for Action

1. `path/to/file`
   Reason: <why this is a strong cleanup candidate>

### MEDIUM — Review Before Acting

1. `path/to/file`
   Reason: <why it may be obsolete or misplaced>

### LOW — Optional Cleanup

1. `path/to/file`
   Reason: <why cleanup may be worthwhile>

### INFO — Notable Observations

1. `path/to/file`
   Note: <observation>

### Recommendations

1. <highest-value cleanup action>
2. <second action>
3. <third action>
```

Keep each finding short and evidence-based.
Call out when an item is a relocation candidate rather than a deletion candidate.

## Phase 4: Offer Actions

After reporting, offer a small set of next steps such as:

1. Remove only `HIGH` items
2. Remove `HIGH` and selected `MEDIUM` items
3. Export the report to `docs/cleanup-audit.md`
4. Keep the report only

Do not perform any cleanup without explicit approval, and show the exact file list before deleting or moving anything.
