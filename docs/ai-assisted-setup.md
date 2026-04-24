# AI-Assisted Setup

This repository is designed for spec-driven implementation with AI pair
programming. The fastest reliable onboarding flow is:

1. Read `AGENTS.md` and the SSD package in `docs/ssd/`.
2. Install the project in editable mode with dev dependencies.
3. Copy `.env.example` values into a local environment file or shell session.
4. Run `pytest` to confirm the workspace is healthy before changing behavior.
5. Run `python -m neurocore.governance.validation` before finalizing repo-facing changes.

For a full local bootstrap sequence, see [docs/setup.md](./setup.md). For
publication safety guidance, see [docs/security.md](./security.md).

## Working Agreement

- Treat the SSD docs as the implementation contract.
- Use `docs/ssd/source-matrix.md` when you need to answer whether SSD or source guidance has been implemented.
- Use test-first changes for behavior work.
- Keep the current local reference stack accurate in docs: Python, `pytest`, SQLite, Postgres/Neon, FastAPI, MCP, and JSON Schema validation.
- Keep command prompts under `.claude/commands/` aligned with actual repo state.
- Keep capture, query, and admin surfaces aligned across CLI, HTTP, and MCP adapters.
- Keep optional extension surfaces aligned with their config gates: ingestion, background summaries, dashboard, and production backend settings.
- Run the repo validator when changes touch docs, metadata, or governance files so schema and secret checks stay green.

## Current Validation Entry Point

```bash
pytest
```

```bash
python -m neurocore.governance.validation
```
