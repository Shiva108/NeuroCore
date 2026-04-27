# Slack Starter Integration

## What it connects

This starter integration shows how to connect Slack message and slash-command
style flows to NeuroCore using existing ingest, query, and admin interfaces.

## Prerequisites

- NeuroCore runtime with HTTP or CLI access
- Slack app capable of posting events/webhooks into your operator workflow

## Slash Flow Example

Suggested flow for `/memory-review`:

1. Receive slash command payload in your Slack bridge service.
2. Capture command context with `neurocore ingest slack`.
3. Query recent scoped memory with `neurocore query`.
4. Build a report prompt from query output and pass to reporting extension.
5. Return report summary into the Slack thread.

## Validation

Send a sample `event_callback` Slack payload through `/ingest/slack` and confirm
it appears in `/query` and `/dashboard/data`.
