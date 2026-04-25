# Setup Guide

This guide keeps the root [README](../README.md) focused while covering the
full local bootstrap flow for contributors, evaluators, and GitHub visitors.

## Prerequisites

- Python 3.11 or newer
- `pip` or another PEP 517-compatible installer
- Optional: a virtual environment tool such as `venv` or `uv`

## Recommended Bootstrap Path

Use the bootstrap script when you want the fastest working local setup:

```bash
python scripts/bootstrap.py
```

By default this path:

- creates or reuses `.venv`
- installs `.[dev,semantic]`
- writes `.env` from the security-operator profile
- copies `secrets.json` and `preferences.json` from their example files
- creates `data/`
- runs `pytest` and `python -m neurocore.governance.validation`

If you want a small interactive flow for namespace, `.env` overwrite, and
verification choices:

```bash
python scripts/bootstrap.py --wizard
```

The bootstrap script preserves an existing `.env` unless you pass
`--force-env`.

## Manual Setup

Use the manual path when you want full control over each setup step or want a
different local profile than the bootstrap defaults.

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install the project with development dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

3. Create local configuration files:

```bash
cp .env.example .env
cp secrets.json.example secrets.json
cp preferences.json.example preferences.json
```

4. Edit the copied files with values appropriate for your environment.

For the security-oriented default values used by the bootstrap flow, see
[.env.security-operator.example](../.env.security-operator.example).

## What Each Config File Is For

- `.env`: runtime configuration consumed by `neurocore.core.config`
- `secrets.json`: local-only secret material for tooling or operator workflows
- `preferences.json`: local-only convenience defaults that should stay untracked

## Validation

Run the full publication baseline before opening a pull request:

```bash
black --check src tests
flake8 src tests
pytest
python -m neurocore.governance.validation
```

## Running NeuroCore

Use the installed console entry point:

```bash
neurocore --help
```

Or invoke the adapter module directly:

```bash
python -m neurocore.adapters.cli capture --request-json '{"bucket":"recon","content":"hello"}'
```

## Optional Runtime Paths

- Set `NEUROCORE_STORAGE_BACKEND=sqlite` to persist data locally.
- Set `NEUROCORE_STORAGE_BACKEND=postgres` with production URLs to route primary
  and sealed content to Postgres-backed storage.
- Enable `NEUROCORE_ENABLE_HTTP_ADAPTER=true` or
  `NEUROCORE_ENABLE_MCP_ADAPTER=true` only when those surfaces are required.
- Enable multi-model consensus only after providing a real consensus API key and
  base URL.

## Next Reading

- [Security Guide](./security.md)
- [Troubleshooting](./troubleshooting.md)
- [AI-Assisted Setup](./ai-assisted-setup.md)
- [SSD Architecture](./ssd/architecture.md)
