# Contributing to NeuroCore

## Workflow

NeuroCore is being built contract-first. Before changing behavior, review:

- `docs/ssd/architecture.md`
- `docs/ssd/specification.md`
- `docs/ssd/implementation-plan.md`
- `docs/ssd/source-matrix.md`

Prefer small, focused changes that keep the SSD package and implementation in
sync.

## Local Development

1. Bootstrap the local workspace:

```bash
python scripts/bootstrap.py
```

2. Or use the convenience target:

```bash
make setup
```

3. If you need full manual control, create a virtual environment and install
   editable dependencies:

```bash
python3 -m pip install -e ".[dev]"
```

4. Run formatting, linting, and tests:

```bash
black --check src tests
flake8 src tests
pytest
```

5. Run the repo contract check before opening a PR:

```bash
python -m neurocore.governance.validation
```

## Implementation Rules

- Write tests before changing behavior.
- Keep public contracts aligned with the SSD docs.
- Keep `docs/ssd/source-matrix.md` updated when repo guidance or named sources change implementation expectations.
- Preserve the logical separation between capture, query, and admin surfaces.
- Keep storage and ranking integrations behind replaceable abstractions.
- Preserve retrieval artifact behavior when changing storage, query, or reindex code.
- Preserve parity across library, CLI, HTTP, and MCP request/response contracts.
- Preserve config gating for optional extension surfaces such as dashboard, background summaries, and production backend support.

## Security and Configuration

- Never commit secrets or local-only environment files.
- Use `.env.example`, `secrets.json.example`, and `preferences.json.example` as
  checked-in references for local configuration.
- Treat `namespace`, `bucket`, and `sensitivity` as mandatory policy inputs.
- Keep metadata examples aligned with `.github/module-metadata.schema.json`.
- Use `module-metadata.json` for repository metadata files and rely on `python -m neurocore.governance.validation` for schema enforcement.
