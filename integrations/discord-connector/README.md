# Discord Connector

Runnable Discord bridge for NeuroCore.

What it does:
- ingests real `MESSAGE_CREATE` style payloads
- runs scoped `query`, `report`, and `protocol` flows after ingestion
- provides a repo-local smoke-test path before you attach a live bot gateway

Quick start:

```bash
python integrations/discord-connector/connector.py ingest --request-json '{"t":"MESSAGE_CREATE","d":{"id":"m-1","guild_id":"G123","channel_id":"C123","timestamp":"2026-04-29T10:00:00Z","content":"critical ATT&CK note","author":{"id":"U1","username":"analyst"}},"bucket":"findings"}'
python integrations/discord-connector/connector.py query --request-json '{"namespace":"discord-g123","query_text":"ATT&CK note","allowed_buckets":["findings"],"sensitivity_ceiling":"restricted"}'
```

Smoke test:
1. Ingest a sample Discord payload.
2. Run `query` or `protocol`.
3. Confirm the namespace-scoped memory comes back with sectioned output.
