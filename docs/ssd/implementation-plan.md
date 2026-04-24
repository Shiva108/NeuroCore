# NeuroCore Implementation Plan

## Objective

Track the implemented NeuroCore v1 rollout against the SSD package, record what
remains intentionally deferred, and keep the repo's source coverage ledger
aligned with the implementation.

## Current repository state

The repository now contains a working Python implementation:

- `src/neurocore/` application package
- `tests/` contract and behavior coverage
- `assets/` static project assets
- `docs/templates/` onboarding template material
- `.github/` repo governance assets
- `docs/ssd/source-matrix.md` for SSD/source traceability

The SSD package remains the contract source of truth, and this plan serves as a
status-aware implementation ledger for the current codebase.

## Completed milestones

### 1. Repository and tooling baseline

Completed:

- Python package layout under `src/neurocore/`
- `pytest`-based test suite
- `.env.example`
- README and contributor documentation

Validation:

- local setup documented
- test entrypoint established
- governance entrypoint established

### 2. Configuration contract

Completed:

- typed runtime configuration in `src/neurocore/core/config.py`
- chunking, retrieval, storage, semantic backend, and adapter flags
- admin, dashboard, background summarization, consensus, and production backend
  flags

Validation:

- required env vars fail loudly
- invalid bucket and sensitivity values are rejected
- documented defaults are tested

### 3. Core domain model

Completed:

- `MemoryRecord`
- `MemoryDocument`
- `MemoryChunk`
- `RetrievalArtifact`
- `QueryContext`

Validation:

- model tests cover required and optional fields
- invalid namespace, bucket, and sensitivity values fail deterministically

### 4. Normalization, deduplication, and chunking

Completed:

- whitespace normalization
- deterministic fingerprints
- namespace-scoped deduplication
- sensitivity-aware dedup signatures
- deterministic chunking with offsets

Validation:

- identical content in the same namespace deduplicates
- identical content in different namespaces or sensitivities remains distinct
- repeated chunking of the same input is deterministic

### 5. Storage and retrieval

Completed:

- storage abstraction in `src/neurocore/storage/base.py`
- in-memory, SQLite, and Postgres backends
- sealed-store routing through `RoutedStore`
- persisted retrieval artifacts for records and chunks
- query engine with metadata-first filtering and optional semantic ranking
- metadata-only fallback with warnings when semantic ranking is unavailable

Validation:

- records and documents can be created, fetched, updated, archived, and deleted
- retrieval artifacts persist and rebuild correctly
- sealed content stays in the isolated backend
- query flow enforces namespace and sensitivity before ranking

### 6. Interface boundaries

Completed:

- capture interface
- query interface
- admin interface
- parity across library, CLI, HTTP, and MCP surfaces

Validation:

- capture surface cannot perform admin operations
- admin surface is disabled by default
- default query path does not return sealed content

### 7. Extension surfaces

Completed:

- Slack and Discord ingestion adapters
- background summarization runner
- multi-model consensus summarization support
- dashboard data and HTML dashboard surfaces
- production backend selection through Postgres/Neon configuration

Validation:

- ingest surfaces normalize external payloads into capture requests
- summary surfaces stay gated by config
- dashboard surfaces stay gated by config and exclude sealed documents
- production backend configuration is validated and redacted in surfaced status

### 8. Admin rebuilds and maintenance

Completed:

- metadata patch and content replacement updates
- soft delete by default and gated hard delete
- audit-event emission
- artifact-backed reindex behavior
- maintenance helpers for namespace backfill, bucket validation, and sealed
  migration

Validation:

- replacement updates preserve supersession chains
- reindex preserves canonical ids and rebuilds artifacts
- missing optional semantic backends emit warnings instead of hard failure

### 9. Governance, onboarding, and source traceability

Completed:

- `docs/templates/setup-guide-template.md`
- `docs/ai-assisted-setup.md`
- `CONTRIBUTING.md`
- `.github/pull_request_template.md`
- `.github/workflows/repo-gate.yml`
- `.github/module-metadata.schema.json`
- repo validator in `src/neurocore/governance/validation.py`
- `docs/ssd/source-matrix.md`

Validation:

- repo validation checks required docs
- metadata files are discovered and validated against JSON Schema
- obvious secret-like values fail the repo gate
- source matrix statuses are explicit and reviewable

## Remaining intentional deferrals

These items remain outside the implemented v1 scope:

- always-on semantic embedding infrastructure
- hosted vector backend selection beyond the current pluggable interfaces
- CTI-specific workflows

## Execution order used

The implemented rollout followed this practical sequence:

1. establish config and domain contracts
2. add capture, dedup, and chunking
3. add storage backends and query behavior
4. add admin behavior and maintenance utilities
5. add CLI, HTTP, and MCP adapters
6. add extension surfaces for ingest, summaries, dashboard, and production
   backend routing
7. add governance automation, repo validation, and source traceability
8. close final alignment gaps around retrieval artifacts, JSON Schema
   validation, and SSD doc refresh

## Validation plan

Primary commands:

```bash
pytest
python -m neurocore.governance.validation
```

Focused validation continues to rely on narrow `pytest` slices during
development, followed by full-suite and repo-gate checks before closeout.
