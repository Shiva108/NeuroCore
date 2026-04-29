# Claude Desktop MCP Connector

Repo-local connector package for attaching NeuroCore to Claude Desktop over MCP.

What it does:
- exposes tool discovery for the current NeuroCore MCP server
- runs briefing and protocol flows with the same repo-local config used by `neurocore serve mcp`
- emits a Claude Desktop MCP config snippet you can adapt into your local client settings

Quick start:

```bash
python integrations/claude-desktop-mcp/connector.py describe-tools
python integrations/claude-desktop-mcp/connector.py protocol --request-json '{"name":"cti-review-v1","namespace":"project-alpha","query_text":"critical CTI"}'
```

Smoke test:
1. Run `describe-tools` and confirm `run_protocol`, `query_memory`, and `generate_briefing` are present.
2. Run the bundled protocol against a seeded namespace.
3. Confirm the response includes the required CTI sections.
