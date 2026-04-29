# NeuroCore

[![License: MIT](https://img.shields.io/github/license/Shiva108/NeuroCore?color=15803D)](https://github.com/Shiva108/NeuroCore/blob/main/LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-1D4ED8.svg)](https://www.python.org/downloads/)
[![CI](https://img.shields.io/github/actions/workflow/status/Shiva108/NeuroCore/repo-gate.yml?branch=main&label=ci)](https://github.com/Shiva108/NeuroCore/actions/workflows/repo-gate.yml)

NeuroCore is a Python package for capturing, storing, querying, and governing
policy-aware memory artifacts. The current repository includes a working core
library, a CLI entrypoint, FastAPI and MCP adapter factories, multiple storage
backends, ingestion helpers for Slack and Discord payloads, and automated tests
covering the main subsystem contracts.

**Version:** `0.1.0`  
Declared in [pyproject.toml](pyproject.toml).

## Overview

Main capabilities currently present in the repository:

- Capture notes and longer documents into record or document storage paths.
- Query stored content with metadata filters and optional semantic ranking.
- Route storage to in-memory, SQLite, or Postgres-backed primary and sealed
  stores.
- Expose the same core behavior through library, CLI, HTTP, and MCP surfaces.
- Run a FastAPI-first reference app and MCP server through official CLI serve
  commands.
- Gate higher-risk or optional surfaces such as admin operations, dashboard
  views, background summarization, and multi-model consensus via configuration.
- Provide reporting helpers for building review and report workflows on top of
  query results.
- Validate repository metadata and scan for obvious secret-like values with a
  built-in governance checker.
- Provide ecosystem contribution surfaces for recipes, skills, integrations,
  dashboards, schemas, primitives, and curated extensions.

## Repository Structure

```text
.
├── src/neurocore/
│   ├── adapters/          # CLI, FastAPI, and MCP adapter implementations
│   ├── core/              # Config, shared content primitives, models, and policy validation
│   ├── governance/        # Repository contract and secret-scan validator
│   ├── ingest/            # Chunking plus ingest-specific compatibility helpers
│   ├── interfaces/        # Public capture, query, ingest, admin, dashboard APIs
│   ├── reporting/         # Report context builders and consensus reporting helpers
│   ├── retrieval/         # Query engine and rankers
│   ├── storage/           # In-memory, SQLite, Postgres, and routed stores
│   ├── summarization/     # Background and consensus summarization logic
│   └── runtime.py         # Runtime factories for stores, rankers, summarizers
├── tests/                 # Pytest suite grouped by subsystem
├── scripts/               # Local bootstrap and repo helper scripts
├── assets/screenshots/    # README visuals
├── .github/               # CI workflow, PR template, metadata schema
├── .claude/commands/      # AI-assisted slash-command prompts used in this repo
├── pyproject.toml         # Packaging metadata, dependencies, tool config
├── Makefile               # Convenience targets for setup and validation
├── .env.example           # Example environment variables
├── .env.security-operator.example # Security-oriented local profile
├── secrets.json.example   # Local-only secret template
├── preferences.json.example # Local-only preference template
└── CHANGELOG.md           # Project change log
```

## Installation Instructions

### Prerequisites

- Python `3.11` or newer
- `pip`
- Optional: `venv` or another virtual environment tool

### Quick Start

The fastest local onboarding path is the bootstrap script:

```bash
python scripts/bootstrap.py
```

This creates or reuses `.venv`, installs `.[dev,semantic]`, writes a
security-oriented `.env`, copies the local-only config templates, creates
`data/`, runs `pytest` plus the repo validator, and prints a readiness summary
for semantic, query, and report support.

If you want a small guided flow for namespace and verification choices:

```bash
python scripts/bootstrap.py --wizard
```

### Setup

1. Clone the repository and change into it.
2. Run the bootstrap script:

```bash
python scripts/bootstrap.py
```

3. Activate the virtual environment and load the generated environment:

```bash
source .venv/bin/activate
set -a
source .env
set +a
```

4. Optional: use the detailed manual path in [docs/setup.md](docs/setup.md) if
   you want to control each step yourself.

### Manual Setup

If you prefer a fully manual setup, the project still supports the documented
step-by-step flow in [docs/setup.md](docs/setup.md).

### Optional Extras

The bootstrap already installs the semantic extra by default for local security
workflows. If you are following the manual path and want the
`sentence-transformers` ranker:

```bash
python -m pip install -e ".[dev,semantic]"
```

## Usage Guide

The checked-in runnable entrypoint is the `neurocore` CLI defined in
`pyproject.toml`. HTTP and MCP support are available as Python adapter
factories and through dedicated serve commands.

For repo checkouts, prefer the checkout-safe wrappers:

```bash
python scripts/neurocore_checkout.py --help
python scripts/validate_checkout.py
```

For security-focused local work, there is also a helper wrapper that reuses the
repo virtual environment, loads `.env`, and exposes shortcuts for notes, files,
papers, and `hackingagent` artifacts:

```bash
./.venv/bin/python scripts/security_workflow.py --help
```

Use `./.venv/bin/python scripts/security_workflow.py presets` to list the built-in bug
bounty, pentest, paper-tracking, and agent-memory workflows.

Two local readiness tiers matter:

- query-ready: capture and retrieval work with your configured storage and semantic backend
- briefing-ready: synthesized briefings work from durable memory even when reporting is unavailable
- full report-ready: consensus reporting also works because the configured provider is live for the current invocation

Check the current state at any time:

```bash
./.venv/bin/python scripts/security_workflow.py capabilities
```

### Inspect the CLI

```bash
neurocore --help
```

### Run structural quality checks

```bash
make sentrux
```

This runs the repo's checked-in Sentrux rules plus the saved structural
baseline from `.sentrux/`.

### Capture a note

This example relies on the default namespace and sensitivity from your exported
environment variables.

```bash
neurocore capture --request-json '{"bucket":"recon","content":"Initial recon note","content_format":"markdown","source_type":"note"}'
```

### Query stored content

```bash
neurocore query --request-json '{"query_text":"recon","allowed_buckets":["recon","findings"],"sensitivity_ceiling":"restricted"}'
```

### Generate a consensus report

Consensus reporting must be enabled first with
`NEUROCORE_ENABLE_MULTI_MODEL_CONSENSUS=true` plus the configured provider,
model names, base URL, and API key. For local development, you can start the
bundled mock provider with `./.venv/bin/python scripts/mock_openai_compatible.py`.

If you want a real external provider instead of the local mock, start from
[.env.reporting-provider.example](./.env.reporting-provider.example).

```bash
neurocore report consensus --request-json '{"objective":"Generate a pentest review report.","query_request":{"query_text":"ssrf findings","allowed_buckets":["findings","reports"],"sensitivity_ceiling":"restricted"}}'
```

If consensus reporting is disabled or the provider is unavailable, the same
report path now returns a synthesized markdown briefing payload with
`"mode":"fallback-briefing"` instead of hard failing.

### Ingest an external event payload

```bash
neurocore ingest slack --request-json '{"type":"event_callback","team_id":"T123","event":{"type":"message","channel":"C123","user":"U123","text":"incident note","ts":"1713897900.000100"},"bucket":"ops"}'
```

The CLI also supports `ingest discord`.

Optional ingest profile defaults can be loaded from a JSON file by setting
`NEUROCORE_INGEST_PROFILE_PATH=/path/to/ingest-profiles.json`.

### Run background summaries

Background summarization must be enabled in the environment first with
`NEUROCORE_ENABLE_BACKGROUND_SUMMARIZATION=true`.

```bash
neurocore summaries run --request-json '{"limit":10}'
```

### Use admin commands

Admin operations are gated behind `NEUROCORE_ENABLE_ADMIN_SURFACE=true`.

```bash
neurocore admin reindex --request-json '{"ids":["rec-1"],"scope":"records"}'
```

Audit stored memory for secret-like values and review non-mutating remediation
candidates:

```bash
neurocore admin audit --request-json '{"namespace":"project-alpha","allowed_buckets":["research"]}'
```

### Use the adapter factories from Python

FastAPI app factory:

```python
from neurocore.adapters.http_api import create_app

app = create_app()
```

MCP server factory:

```python
from neurocore.adapters.mcp_server import create_mcp_server

server = create_mcp_server()
```

### Run the reference app

Enable the HTTP adapter in your environment and run:

```bash
python scripts/neurocore_checkout.py serve http --host 127.0.0.1 --port 8000
```

### Run the MCP server

Enable the MCP adapter in your environment and run:

```bash
python scripts/neurocore_checkout.py serve mcp --transport stdio
```

## Configuration

Required configuration values:

- `NEUROCORE_DEFAULT_NAMESPACE`
- `NEUROCORE_ALLOWED_BUCKETS`
- `NEUROCORE_DEFAULT_SENSITIVITY`

Common optional settings:

- `NEUROCORE_STORAGE_BACKEND=in_memory|sqlite|postgres`
- `NEUROCORE_SEMANTIC_BACKEND=none|sentence-transformers`
- `NEUROCORE_ENABLE_ADMIN_SURFACE=true|false`
- `NEUROCORE_ENABLE_DASHBOARD=true|false`
- `NEUROCORE_ENABLE_BACKGROUND_SUMMARIZATION=true|false`
- `NEUROCORE_ENABLE_MULTI_MODEL_CONSENSUS=true|false`
- `NEUROCORE_PRODUCTION_BACKEND_PROVIDER=none|neon`

For the full generic environment template, see [.env.example](.env.example). For
the security-oriented bootstrap profile, see
[.env.security-operator.example](.env.security-operator.example). For setup,
security, and troubleshooting details, see the docs linked below.

## Setup And Validation

Bootstrap commands:

```bash
python scripts/bootstrap.py
make setup
```

Validation commands:

```bash
black --check src tests
flake8 src tests
pytest
python scripts/validate_checkout.py
```

The GitHub Actions workflow in `.github/workflows/repo-gate.yml` runs those same
checks across Python 3.11, 3.12, and 3.13.

## Documentation

- [Setup Guide](docs/setup.md)
- [Reference Stack](docs/reference-stack.md)
- [Hosted Stack](docs/hosted-stack.md)
- [Security Guide](docs/security.md)
- [Troubleshooting](docs/troubleshooting.md)
- [AI-Assisted Setup](docs/ai-assisted-setup.md)
- [OB1 Gap Report](docs/ob1-gap-report.md)
- [Contributing Guide](CONTRIBUTING.md)

## Ecosystem Surfaces

- [Extensions](extensions/README.md)
- [Primitives](primitives/README.md)
- [Recipes](recipes/README.md)
- [Skills](skills/README.md)
- [Dashboards](dashboards/README.md)
- [Integrations](integrations/README.md)
- [Schemas](schemas/README.md)

Recommended runnable examples:

- [Local Quickstart Recipe](recipes/quickstart-memory-capture/README.md)
- [Hosted Stack Quickstart Recipe](recipes/hosted-stack-quickstart/README.md)

## Demo Screenshots

Publication preview:

![NeuroCore overview](assets/screenshots/overview.svg)

Dashboard mock:

![NeuroCore dashboard mock](assets/screenshots/dashboard.svg)

## Security

- Do not commit `.env`, `secrets.json`, `preferences.json`, `token.json`, or
  real database URLs.
- Treat `secrets.json.example` and `preferences.json.example` as local-only
  templates.
- Run `python scripts/validate_checkout.py` before publishing changes.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for workflow expectations. In short:
review the SDD docs first, keep implementation and contracts aligned, and run
the validation commands before opening a PR.

## License

This project is licensed under the [MIT License](LICENSE).
