# Quickstart Memory Capture

## What it does

This recipe walks through the smallest useful NeuroCore workflow: capture one
memory, query it back, and review the result in the reference app.

## Prerequisites

- Follow [docs/reference-stack.md](../../docs/reference-stack.md)
- Start the reference app with `neurocore serve http`

## Steps

1. Capture a note:

```bash
neurocore capture --request-json '{"bucket":"research","content":"reference stack note","content_format":"markdown","source_type":"note"}'
```

2. Query it back:

```bash
neurocore query --request-json '{"query_text":"reference stack","namespace":"security-lab","allowed_buckets":["research"],"sensitivity_ceiling":"standard"}'
```

3. Open `/dashboard` and confirm the note appears in recent activity.

## Expected Outcome

You can store and retrieve a record through the same core interfaces used by
the CLI and reference app.
