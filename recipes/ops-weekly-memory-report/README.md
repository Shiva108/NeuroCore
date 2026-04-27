# Ops Weekly Memory Report

## Purpose

Generate a weekly operations report from NeuroCore memory that highlights
trends, unresolved risks, and next actions.

## Inputs

- Query response JSON filtered to operations buckets and date window
- Weekly objective, for example: "Summarize incidents and follow-ups"
- Optional report section overrides

## Flow

1. Run `neurocore query` for weekly ops scope.
2. Build context with `build_report_context_from_query_response()`.
3. Build prompt with `build_sectioned_report_prompt()`.
4. Generate markdown report via `MultiModelConsensusReporter`.
5. Publish report into ops handoff channel or ticket.

## Expected Output

A markdown report with:

- `## Overview`
- `## Findings`
- `## Risks`
- `## Actions`

## Validation

Run the workflow on a known weekly fixture and verify that the report captures
all major findings and yields actionable next steps.
