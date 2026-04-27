# Discord Starter Integration

## What it connects

This starter integration shows how to connect Discord message and slash-command
style flows to NeuroCore using existing ingest, query, and admin interfaces.

## Prerequisites

- NeuroCore runtime with HTTP or CLI access
- Discord bot gateway that can forward message payloads to your operator workflow

## Slash Flow Example

Suggested flow for `/memory-ops-report`:

1. Receive slash command context in your Discord bot service.
2. Capture surrounding channel activity with `neurocore ingest discord`.
3. Query scoped memory with `neurocore query`.
4. Build report context and run multi-model consensus reporter.
5. Post the report summary back to the Discord thread.

## Validation

Send a sample `MESSAGE_CREATE` payload through `/ingest/discord` and confirm it
is retrievable via `/query` with expected namespace and bucket constraints.
