# Contributing to NeuroCore

## Workflow

NeuroCore is being built contract-first. Before changing behavior, review:

- `docs/ssd/architecture.md`
- `docs/ssd/specification.md`
- `docs/ssd/implementation-plan.md`
- `docs/ssd/source-matrix.md`

Prefer small, focused changes that keep the SSD package and implementation in
sync.

NeuroCore accepts both core-package changes and ecosystem contributions. The
core package lives under `src/neurocore/`; reusable ecosystem work belongs in
the top-level contribution surfaces documented below.

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

## Reference Stack

NeuroCore ships two blessed runtime profiles:

- `local`: SQLite primary and sealed stores, FastAPI reference app, MCP server,
  and optional local semantic ranking
- `hosted`: Neon-backed Postgres URLs for primary and sealed stores, using the
  same package and adapters as the local stack

Use [docs/reference-stack.md](docs/reference-stack.md) for the default local
path and [docs/hosted-stack.md](docs/hosted-stack.md) for the hosted variant.

## Implementation Rules

- Write tests before changing behavior.
- Keep public contracts aligned with the SSD docs.
- Keep `docs/ssd/source-matrix.md` updated when repo guidance or named sources change implementation expectations.
- Preserve the logical separation between capture, query, and admin surfaces.
- Keep storage and ranking integrations behind replaceable abstractions.
- Preserve retrieval artifact behavior when changing storage, query, or reindex code.
- Preserve parity across library, CLI, HTTP, and MCP request/response contracts.
- Preserve config gating for optional extension surfaces such as dashboard, background summaries, and production backend support.

## Ecosystem Categories

| Category | Purpose | Review Mode |
| --- | --- | --- |
| `extensions/` | Higher-level builds that compose multiple NeuroCore capabilities | Curated |
| `primitives/` | Reusable patterns depended on by multiple ecosystem modules | Curated |
| `recipes/` | Standalone workflows or walkthroughs built on current core behavior | Open |
| `skills/` | Reusable prompt and skill packs for AI clients using NeuroCore | Open |
| `dashboards/` | UI shells or frontend add-ons that build on the reference app | Open |
| `integrations/` | External connectors and ingestion or delivery surfaces | Open |
| `schemas/` | Supplemental schema patterns and storage extensions | Open |

Every ecosystem contribution must include:

- `README.md`
- `metadata.json`
- any category-specific artifact required by the template, such as `SKILL.md`

Use each category's `_template/` folder as the starting point. `extensions/`
and `primitives/` must declare `"curation": "curated"` in `metadata.json`.

## Review Expectations

- Core package changes must keep CLI, HTTP, and MCP behavior in parity.
- Ecosystem contributions must validate against
  `.github/contribution-metadata.schema.json`.
- Docs changes that affect onboarding, taxonomy, or the reference stack must
  keep `docs/ssd/source-matrix.md` aligned with the resulting repo state.

## Security and Configuration

- Never commit secrets or local-only environment files.
- Use `.env.example`, `secrets.json.example`, and `preferences.json.example` as
  checked-in references for local configuration.
- Treat `namespace`, `bucket`, and `sensitivity` as mandatory policy inputs.
- Keep core metadata examples aligned with
  `.github/module-metadata.schema.json`.
- Keep ecosystem contribution metadata aligned with
  `.github/contribution-metadata.schema.json`.
- Use `module-metadata.json` for internal repository metadata files and
  `metadata.json` for ecosystem contribution entries.
