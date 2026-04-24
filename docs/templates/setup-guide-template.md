# Setup Guide Template

## Purpose

Use this template when documenting a new NeuroCore setup flow.

## Prerequisites

- Required runtime version
- Package manager or virtual environment steps
- Required environment variables
- Required adapter toggles or backend settings

## Installation

1. Clone or open the repository.
2. Install dependencies.
3. Configure environment variables from `.env.example`.
4. Copy any local-only templates such as `secrets.json.example` or `preferences.json.example`.
5. Confirm the selected storage backend and adapter settings.

## Verification

Run the primary validation command and record the expected success signal.

```bash
pytest
```

## Troubleshooting

- Missing dependency
- Invalid environment variable
- Test discovery or import path problems
- Repo contract or secret hygiene validation failures

## AI-Assisted Workflow

- Point coding agents to `docs/ssd/`
- Ask agents to preserve capture, query, and admin boundaries
- Require tests before behavior changes

## Next Steps

- Run adapter-specific validation if CLI, HTTP, or MCP behavior changed
- Run `python -m neurocore.governance.validation` before opening a PR
