# Hosted Stack Quickstart

## What it does

This recipe walks through the blessed hosted NeuroCore profile using the
existing HTTP, MCP, and routed-storage contracts. It is a recommended
first-success path, not a required vendor lock-in.

## Prerequisites

- Follow [docs/hosted-stack.md](../../docs/hosted-stack.md)
- Export the hosted environment variables for your chosen Postgres provider
- Enable the HTTP and MCP adapters

## Steps

1. Start the hosted-profile HTTP surface:

```bash
neurocore serve http --host 127.0.0.1 --port 8000
```

2. Capture a note through the JSON API:

```bash
curl -X POST http://127.0.0.1:8000/capture \
  -H 'Content-Type: application/json' \
  -d '{"bucket":"research","content":"hosted profile note","content_format":"markdown","source_type":"note"}'
```

3. Query it back through the same hosted profile:

```bash
curl -X POST http://127.0.0.1:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"query_text":"hosted profile","namespace":"project-alpha","allowed_buckets":["research"],"sensitivity_ceiling":"standard"}'
```

4. Optionally expose the MCP surface for tool-based clients:

```bash
neurocore serve mcp --transport stdio
```

## Expected Outcome

You can capture and query memory through the hosted profile without changing
the core NeuroCore interfaces, and you can swap the backing Postgres provider
later without rewriting client behavior.
