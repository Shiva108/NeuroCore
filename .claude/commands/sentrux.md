---
description: Run Sentrux architectural analysis when the tool and configuration are available, then explain violations, regressions, and likely fixes.
---

# Sentrux Analysis

Run Sentrux against the current repository if it is actually configured here.

## Preconditions

Before running any scan:

1. Check whether `sentrux` is available on `PATH`.
2. Check whether the repo contains Sentrux configuration such as `.sentrux/` or other project-specific rules files.

If either prerequisite is missing, stop gracefully and report that Sentrux analysis is unavailable for this repository right now.
Do not install Sentrux, generate default config, or create a baseline unless the user explicitly asks.

## Scan Steps

If available, run:

- `sentrux check .` for rule violations
- `sentrux gate .` for regression or baseline comparison

If the project has no saved baseline yet, report that clearly instead of mutating repo state automatically. Offer guidance, but do not create or overwrite a baseline unless the user explicitly asks.

## Analysis

For each violation:

- identify the file and relevant import or dependency
- explain why it violates the configured rule
- trace the likely root cause
- propose the smallest fix that resolves the architectural issue

For gate metrics, report any regressions or concerning signals across:

- overall quality
- coupling
- cycles
- god files
- distance from main sequence

## Summary

If violations exist, provide a compact table:

| File | Violation | Root Cause | Recommended Fix |
|------|-----------|------------|-----------------|

Then give an overall assessment of whether the architecture issues look isolated or systemic.
