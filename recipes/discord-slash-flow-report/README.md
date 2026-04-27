# Discord Slash Flow Report

## What it does

This recipe provides an end-to-end slash-style workflow for generating a memory
review report from Discord activity captured in NeuroCore.

## Prerequisites

- [Discord starter integration](../../integrations/discord-starter/README.md)
- NeuroCore runtime with ingest and query access
- Reporting extension module under `src/neurocore/reporting/`

## Flow

1. Capture Discord activity with `neurocore ingest discord`.
2. Run scoped retrieval with `neurocore query`.
3. Build context via `build_report_context_from_query_response()`.
4. Generate a sectioned prompt via `build_sectioned_report_prompt()`.
5. Produce consensus report via `MultiModelConsensusReporter`.
6. Return the report summary to the slash command thread.

## Validation

Run the flow with a test slash payload and verify that generated output includes
`Overview`, `Findings`, `Risks`, and `Actions` sections.
