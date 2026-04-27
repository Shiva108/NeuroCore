# Security Memory Review Report

## Purpose

Generate a security-focused memory review report from recent NeuroCore query
results using sectioned consensus reporting.

## Inputs

- Query response JSON with candidate security findings
- Review objective, for example: "Summarize highest-risk memory indicators"
- Optional section overrides

## Flow

1. Run `neurocore query` with security-scoped filters.
2. Build context using `build_report_context_from_query_response()`.
3. Build prompt with `build_sectioned_report_prompt()`.
4. Generate report using `MultiModelConsensusReporter`.
5. Post-process output for ticketing or analyst handoff.

## Expected Output

A markdown report with:

- `## Overview`
- `## Findings`
- `## Risks`
- `## Actions`

## Validation

Use a fixed fixture query response and verify that the generated report includes
all required sections and consistent action-oriented recommendations.
