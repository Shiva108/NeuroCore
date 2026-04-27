# Chat Capture Integration

## What it connects

This integration documents the canonical pattern for pushing Slack or Discord
events into NeuroCore through the existing ingest interfaces.

## Prerequisites

- Working NeuroCore setup
- One of the existing ingest surfaces enabled in your operator workflow

## Validation

Send a Slack or Discord payload through the matching ingest command or HTTP
route and confirm the captured content appears in `/dashboard/data` and query
results.
