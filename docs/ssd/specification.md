# NeuroCore Specification Details

## Scope

This specification defines the stable behavior and contracts for NeuroCore v1.
It remains contract-first, but it now reflects the current repository
implementation instead of an undecided future runtime.

## Current implementation

- Python runtime under `src/neurocore/`
- `pytest` test suite and contract coverage under `tests/`
- in-memory, SQLite, and Postgres storage backends with routed sealed storage
- library, CLI, FastAPI, and MCP adapters
- Slack and Discord ingestion adapters that normalize external events into
  `capture_memory()`
- deterministic summarization, optional multi-model consensus support, and a
  background summarization runner
- config-gated dashboard data and HTML dashboard surfaces
- GitHub repo gate, metadata schema validation, and a source coverage ledger

## Expected behavior

NeuroCore v1 must support the following behaviors:

- capture a new atomic memory record
- capture a long-form document and convert it into retrievable chunks
- persist retrieval artifacts for records and chunks
- deduplicate repeated captures within the same namespace
- retrieve records through hybrid filtering and optional semantic ranking
- enforce namespace, bucket, and sensitivity constraints on every query
- expose logically separate capture, query, and admin interfaces
- rebuild retrieval artifacts through admin reindex operations
- expose optional ingest, summary, dashboard, and production-backend features
  behind explicit config flags
- provide onboarding, governance, and source-traceability documentation that
  matches the implementation

## Functional boundaries

### In scope for v1

- core domain model
- capture and query workflows
- chunking and document linkage
- deduplication
- isolation policy enforcement
- retrieval artifact persistence and rebuilds
- admin hooks for update, delete, and reindex
- library, CLI, HTTP, and MCP adapters
- Slack and Discord event ingestion
- background summarization and optional multi-model consensus summarization
- dashboard/data surfaces
- Postgres/Neon-backed routed storage
- setup and contribution templates
- GitHub repo validation for docs, metadata, and secret hygiene
- source coverage tracking via `docs/ssd/source-matrix.md`

### Out of scope for v1

- CTI-specific workflows
- always-on semantic embedding infrastructure
- hosted vector backend selection beyond the current pluggable interfaces
- verbatim adoption of upstream repository structure or licensed
  implementation details

## Domain entities

### MemoryRecord

Canonical storage unit for atomic content.

Required fields:

- `id`
- `namespace`
- `bucket`
- `content`
- `content_format`
- `source_type`
- `sensitivity`
- `metadata`
- `content_fingerprint`
- `created_at`
- `updated_at`

Optional fields:

- `title`
- `tags`
- `external_id`
- `idempotency_key`
- `supersedes_id`
- `archived_at`

### MemoryDocument

Parent object for long-form content.

Required fields:

- `id`
- `namespace`
- `bucket`
- `title` or synthetic title
- one of `raw_content` or `source_locator`
- `source_type`
- `sensitivity`
- `metadata`
- `content_fingerprint`
- `created_at`
- `updated_at`

Optional fields:

- `external_id`
- `tags`
- `summary`
- `supersedes_id`
- `archived_at`

At least one source-preservation field must be present so NeuroCore can retain
canonical long-form lineage even when retrieval happens at the chunk level.

### MemoryChunk

Retrieval unit derived from a document.

Required fields:

- `id`
- `document_id`
- `namespace`
- `bucket`
- `ordinal`
- `chunk_text`
- `token_count`
- `sensitivity`
- `metadata`
- `created_at`

Optional fields:

- `start_offset`
- `end_offset`
- `summary`

### RetrievalArtifact

Persisted retrieval-facing representation for records and chunks.

Required fields:

- `item_id`
- `item_kind`
- `namespace`
- `bucket`
- `sensitivity`
- `source_type`
- `tags`
- `normalized_text`
- `text_hash`
- `created_at`
- `semantic_backend`
- `semantic_status`
- `indexed_at`

Optional fields:

- `document_id`
- `archived_at`
- `semantic_model_name`

Rules:

- one artifact per `MemoryRecord`
- one artifact per `MemoryChunk`
- document parents do not require their own retrieval artifact in v1
- artifact rebuilds must preserve canonical record and document ids

### QueryContext

Runtime scope envelope for any retrieval operation.

Required fields:

- `namespace`
- `allowed_buckets`
- `sensitivity_ceiling`

Optional fields:

- `tags_any`
- `tags_all`
- `source_types`
- `time_range`
- `include_archived`

## Public interfaces

The transport may vary by adapter, but the functional contracts must remain
stable.

### Capture interface

#### `capture_memory(request)`

Purpose:

- ingest a new record or document into NeuroCore

Input contract:

```json
{
  "namespace": "optional explicit namespace",
  "bucket": "research",
  "sensitivity": "standard",
  "content": "Short note or long-form body",
  "content_format": "markdown",
  "source_type": "note",
  "title": "optional title",
  "tags": ["memory", "architecture"],
  "metadata": {
    "author": "user",
    "source_url": "optional"
  },
  "external_id": "optional external reference",
  "idempotency_key": "optional caller-supplied dedup key",
  "created_at": "optional source timestamp"
}
```

Capture rules:

- `namespace` may be supplied explicitly
- if `namespace` is omitted, NeuroCore defaults it from
  `NEUROCORE_DEFAULT_NAMESPACE`
- `bucket` remains required at request time unless a transport-specific adapter
  supplies one before delegating to `capture_memory()`

Expected output:

```json
{
  "id": "stable-id",
  "kind": "record",
  "namespace": "project-alpha",
  "bucket": "research",
  "stored": true,
  "deduplicated": false,
  "chunk_count": 0,
  "warnings": []
}
```

For document capture:

```json
{
  "id": "stable-document-id",
  "kind": "document",
  "namespace": "project-alpha",
  "bucket": "research",
  "stored": true,
  "deduplicated": false,
  "chunk_count": 6,
  "warnings": []
}
```

### Query interface

#### `query_memory(request)`

Purpose:

- retrieve the most relevant records or chunks within an allowed scope

Input contract:

```json
{
  "query_text": "memory chunking tradeoffs",
  "namespace": "project-alpha",
  "allowed_buckets": ["research", "architecture"],
  "sensitivity_ceiling": "restricted",
  "tags_any": ["memory"],
  "tags_all": ["architecture"],
  "source_types": ["note", "article"],
  "time_range": ["2025-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"],
  "include_archived": false,
  "top_k": 8,
  "return_mode": "hybrid"
}
```

Expected output:

```json
{
  "query_id": "stable-query-id",
  "results": [
    {
      "id": "chunk-or-record-id",
      "kind": "chunk",
      "document_id": "optional-parent-id",
      "namespace": "project-alpha",
      "bucket": "research",
      "score": 0.92,
      "matched_by": "hybrid",
      "explanation": {
        "matched_signals": ["semantic", "metadata"],
        "filters_applied": {
          "namespace": "project-alpha",
          "buckets": ["research", "architecture"],
          "sensitivity_ceiling": "restricted"
        }
      },
      "content_preview": "retrieved text excerpt",
      "metadata": {
        "source_type": "article",
        "tags": ["memory"]
      }
    }
  ],
  "truncated": false,
  "warnings": []
}
```

Return modes:

- `record_only`
- `chunk_only`
- `document_aggregate`
- `hybrid`

### Admin interface

#### `update_memory(request)`

Purpose:

- modify metadata or content for an existing record or document

Input contract:

```json
{
  "id": "stable-id",
  "patch": {
    "title": "updated title",
    "tags": ["updated", "tag"],
    "metadata": {
      "reviewed_by": "user"
    }
  },
  "mode": "in_place"
}
```

Minimum behavior:

- preserve auditability
- update `updated_at`
- mark superseded items when content replacement is chosen instead of in-place
  edit

Expected output:

```json
{
  "id": "stable-id",
  "updated": true,
  "mode": "in_place",
  "superseded_id": null,
  "warnings": []
}
```

#### `delete_memory(request)`

Purpose:

- remove content from normal retrieval

Input contract:

```json
{
  "id": "stable-id",
  "mode": "soft_delete",
  "reason": "user requested removal"
}
```

Minimum behavior:

- prefer tombstone or soft-delete semantics by default
- allow hard delete only behind explicit elevated policy
- archive or remove corresponding retrieval artifacts consistently

Expected output:

```json
{
  "id": "stable-id",
  "deleted": true,
  "mode": "soft_delete",
  "warnings": []
}
```

#### `reindex_memory(request)`

Purpose:

- rebuild retrieval artifacts after content or backend changes

Input contract:

```json
{
  "ids": ["id-1", "id-2"],
  "scope": "documents"
}
```

Expected output:

```json
{
  "processed": 2,
  "failed": 0,
  "warnings": []
}
```

Reindex rules:

- `scope="records"` rebuilds record artifacts only
- `scope="documents"` rebuilds chunk artifacts for the named documents
- `scope="all"` rebuilds both records and document chunks for the requested ids
- canonical ids must remain stable
- missing optional semantic backends must produce warnings instead of hard
  failure

All admin operations must emit an audit event containing:

- actor or calling identity
- operation type
- target ids
- timestamp
- outcome

### Supported transport surfaces

The package currently exposes these contract-aligned entrypoints:

- library interfaces for capture, query, admin, ingest, summaries, and
  dashboard data
- CLI commands for `capture`, `query`, `ingest`, `summaries run`, and
  config-gated `admin`
- HTTP endpoints for `/capture`, `/query`, `/admin/*`, `/ingest/slack`,
  `/ingest/discord`, `/summaries/run`, `/dashboard`, and `/dashboard/data`
- MCP tools for `capture_memory`, `query_memory`, ingestion tools, and
  config-gated summary, dashboard, and admin tools

## Chunking specification

NeuroCore must make chunking deterministic enough for repeatable behavior.

Default rules:

- content under the atomic threshold stays a `MemoryRecord`
- content exceeding the threshold becomes a `MemoryDocument` plus `MemoryChunk`
  children
- chunks should align to sentence or section boundaries where possible
- chunks should preserve stable ordering
- chunks should use small contextual overlap to protect meaning across
  boundaries
- chunks should preserve stable `start_offset` and `end_offset` values

Recommended default settings:

- `max_atomic_tokens = 350`
- `target_chunk_tokens = 600`
- `max_chunk_tokens = 900`
- `chunk_overlap_tokens = 75`

These values are defaults, not hard architectural limits.

## Deduplication rules

NeuroCore must deduplicate within the same namespace using normalized content.

Rules:

- compute `content_fingerprint` from normalized content
- scope deduplication by namespace and sensitivity so identical text may exist
  in different namespaces or sensitivity tiers
- if the fingerprint already exists:
  - return the existing id when content and structural metadata match
  - merge safe metadata fields when configured
  - do not duplicate chunks for the same document body

## Isolation rules

Every record or document must have:

- `namespace`
- `bucket`
- `sensitivity`

Policy rules:

- queries must never cross namespace boundaries unless an explicit future
  cross-namespace policy is introduced
- `bucket` narrows the search area but is not a sufficient security boundary on
  its own
- `tags` improve discoverability but must not be treated as access controls
- `sealed` content must not be returned from the default query path
- sealed content should persist to a separate configured store

Recommended sensitivity enum:

- `standard`
- `restricted`
- `sealed`

Recommended bucket examples:

- `work`
- `research`
- `planning`
- `personal`
- `ops`

Bucket names are implementation-defined, but the system should validate them
against configuration.

## Retrieval behavior

NeuroCore queries must be hybrid by default.

Required sequence:

1. apply namespace constraint
2. apply sensitivity ceiling
3. apply bucket and metadata filters
4. run semantic or ranked recall over the remaining subset
5. optionally aggregate chunk hits to document-level output

Fallback behavior:

- metadata-only retrieval must remain available when no semantic backend is
  configured
- callers must receive a warning when semantic ranking is unavailable

## Configuration needs

NeuroCore v1 defines these configuration areas:

- `NEUROCORE_DEFAULT_NAMESPACE`
- `NEUROCORE_ALLOWED_BUCKETS`
- `NEUROCORE_DEFAULT_SENSITIVITY`
- `NEUROCORE_STORAGE_BACKEND`
- `NEUROCORE_PRIMARY_STORE_PATH`
- `NEUROCORE_SEALED_STORE_PATH`
- `NEUROCORE_SEMANTIC_BACKEND`
- `NEUROCORE_SEMANTIC_MODEL_NAME`
- `NEUROCORE_MAX_ATOMIC_TOKENS`
- `NEUROCORE_TARGET_CHUNK_TOKENS`
- `NEUROCORE_MAX_CHUNK_TOKENS`
- `NEUROCORE_CHUNK_OVERLAP_TOKENS`
- `NEUROCORE_MAX_CONTENT_TOKENS`
- `NEUROCORE_DEFAULT_TOP_K`
- `NEUROCORE_ALLOW_HARD_DELETE`
- `NEUROCORE_ENABLE_ADMIN_SURFACE`
- `NEUROCORE_ENABLE_CLI_ADAPTER`
- `NEUROCORE_ENABLE_HTTP_ADAPTER`
- `NEUROCORE_ENABLE_MCP_ADAPTER`
- `NEUROCORE_ENABLE_DASHBOARD`
- `NEUROCORE_ENABLE_BACKGROUND_SUMMARIZATION`
- `NEUROCORE_ENABLE_MULTI_MODEL_CONSENSUS`
- `NEUROCORE_CONSENSUS_PROVIDER`
- `NEUROCORE_CONSENSUS_MODEL_NAMES`
- `NEUROCORE_CONSENSUS_BASE_URL`
- `NEUROCORE_CONSENSUS_API_KEY`
- `NEUROCORE_PRODUCTION_BACKEND_PROVIDER`
- `NEUROCORE_PRODUCTION_DATABASE_URL`
- `NEUROCORE_PRODUCTION_SEALED_DATABASE_URL`
- `NEUROCORE_DEDUP_MERGE_METADATA`

## Failure modes and edge cases

NeuroCore must define expected handling for these cases:

### Empty or whitespace-only capture

Expected behavior:

- reject with validation error

### Missing namespace or bucket

Expected behavior:

- default `namespace` from `NEUROCORE_DEFAULT_NAMESPACE` when omitted
- reject missing or invalid `bucket`

### Oversized content

Expected behavior:

- route to document chunking if supported
- reject only if the configured maximum absolute size is exceeded

### Duplicate capture

Expected behavior:

- return deterministic dedup result instead of creating a second record

### Query without allowed buckets

Expected behavior:

- either reject or fall back to configured defaults
- behavior must be explicit and tested

### Cross-sensitivity request

Expected behavior:

- never return records above the declared sensitivity ceiling

### Chunking failure

Expected behavior:

- fail the request cleanly
- do not persist a partial document unless the storage layer supports atomic
  multi-write semantics

### Retrieval with no semantic backend available

Expected behavior:

- degrade to metadata-only query if supported
- emit warning so callers know ranking quality changed

## Migration and compatibility concerns

Compatibility goals:

- keep the domain entities transport-neutral
- keep adapter-specific details out of core models
- make storage backends replaceable behind interfaces
- preserve id stability for records and documents across reindexing

If NeuroCore later upgrades isolation or storage behavior further, migration
utilities should support:

- backfilling namespaces
- validating bucket assignments
- moving sealed records into isolated storage

## Onboarding documentation requirements

NeuroCore should keep a reusable setup-doc template under `docs/`.

Required sections for the template:

- purpose
- prerequisites
- required configuration
- step-by-step setup
- verification checkpoints
- troubleshooting
- AI-assisted workflow
- next steps

## Contributor contract requirements

NeuroCore should maintain:

- `CONTRIBUTING.md`
- `.github/pull_request_template.md`
- `.github/workflows/repo-gate.yml`
- `.github/module-metadata.schema.json`
- `docs/ssd/source-matrix.md`

Metadata validation targets:

- repository files named `module-metadata.json`
- JSON fixtures under `tests/fixtures/metadata/`

Minimum metadata fields:

- `name`
- `kind`
- `description`
- `owner`
- `status`
- `interfaces`
- `test_coverage`

## Assumptions

- NeuroCore is implemented incrementally, but the repository already contains a
  working reference implementation.
- Core memory/query/admin contracts are the stable center of the system.
- Ingestion, summarization, dashboard, and production-backend features are
  supported extensions in the same package and remain config-gated.
- A later MCP surface remains important, which is why tool governance and
  transport parity are part of the base spec.
- Upstream projects may inform the design, but NeuroCore adapts ideas instead
  of copying source or docs blindly.
