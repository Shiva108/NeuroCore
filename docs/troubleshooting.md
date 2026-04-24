# Troubleshooting

## `ModuleNotFoundError: No module named neurocore`

Install the package in editable mode:

```bash
python -m pip install -e ".[dev]"
```

## `ConfigError: Missing required configuration`

Copy `.env.example` to `.env` and provide at least:

- `NEUROCORE_DEFAULT_NAMESPACE`
- `NEUROCORE_ALLOWED_BUCKETS`
- `NEUROCORE_DEFAULT_SENSITIVITY`

## `PermissionError` For Admin, Dashboard, Or Summaries

Those surfaces are intentionally gated. Enable the relevant flags in `.env`:

- `NEUROCORE_ENABLE_ADMIN_SURFACE=true`
- `NEUROCORE_ENABLE_DASHBOARD=true`
- `NEUROCORE_ENABLE_BACKGROUND_SUMMARIZATION=true`

## `flake8` Or `black` Command Not Found

Reinstall development dependencies:

```bash
python -m pip install -e ".[dev]"
```

## Postgres Backend Fails At Startup

If `NEUROCORE_STORAGE_BACKEND=postgres`, both of these must be configured:

- `NEUROCORE_PRODUCTION_DATABASE_URL`
- `NEUROCORE_PRODUCTION_SEALED_DATABASE_URL`

Also set `NEUROCORE_PRODUCTION_BACKEND_PROVIDER=neon` or another supported
provider when the runtime adds more options.

## Governance Validation Reports Secret-Like Values

Inspect the reported file carefully. The validator is intentionally conservative.
Replace real credentials with placeholders, move local values into ignored files,
and rerun:

```bash
python -m neurocore.governance.validation
```
