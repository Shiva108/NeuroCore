# Slack Connector

Runnable Slack bridge for NeuroCore.

What it does:
- ingests real Slack `event_callback` message payloads
- runs scoped `query`, `report`, and `protocol` flows against the same namespace
- stays repo-local so you can smoke-test without external Slack infrastructure

Quick start:

```bash
python integrations/slack-connector/connector.py ingest --request-json '{"type":"event_callback","team_id":"T123","event":{"type":"message","channel":"C123","user":"U123","text":"critical CTI note","ts":"1713897900.000100"},"bucket":"reports"}'
python integrations/slack-connector/connector.py protocol --request-json '{"name":"cti-review-v1","namespace":"slack-t123","query_text":"critical CTI"}'
```

Environment:
- copy `.env.example` values into your repo `.env` if you need a dedicated namespace or bucket override

Smoke test:
1. Ingest a real or sample Slack event payload.
2. Run `query` or `protocol`.
3. Confirm the captured memory is retrievable and the protocol returns sectioned markdown.
