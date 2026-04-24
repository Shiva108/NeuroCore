"""Capture interface for storing records and documents in NeuroCore."""

from __future__ import annotations

from datetime import UTC, datetime

from neurocore.core.config import NeuroCoreConfig
from neurocore.core.models import MemoryChunk, MemoryDocument, MemoryRecord
from neurocore.core.policies import (
    validate_bucket,
    validate_namespace,
    validate_sensitivity,
)
from neurocore.ingest.chunking import (
    chunk_text_with_offsets,
    classify_content_kind,
)
from neurocore.ingest.normalize import (
    compute_content_fingerprint,
    count_tokens,
    generate_stable_id,
)
from neurocore.storage.base import BaseStore


def capture_memory(
    request: dict[str, object], store: BaseStore, config: NeuroCoreConfig
) -> dict[str, object]:
    content = str(request.get("content", "")).strip()
    if not content:
        raise ValueError("content is required")
    if count_tokens(content) > config.max_content_tokens:
        raise ValueError("content exceeds the configured maximum content size")

    namespace = validate_namespace(
        str(request.get("namespace") or config.default_namespace)
    )
    bucket = validate_bucket(str(request.get("bucket")), config.allowed_buckets)
    sensitivity = validate_sensitivity(
        str(request.get("sensitivity") or config.default_sensitivity)
    )
    content_format = str(request.get("content_format") or "markdown").strip()
    source_type = str(request.get("source_type") or "note").strip()
    metadata = dict(request.get("metadata", {}))
    fingerprint = compute_content_fingerprint(content)
    kind = str(request.get("force_kind") or classify_content_kind(content, config))
    signature = f"{kind}:{source_type}:{content_format}:{sensitivity}"

    existing_id = store.find_duplicate(namespace, fingerprint, signature)
    if existing_id is not None:
        _merge_duplicate_metadata(
            store=store,
            existing_id=existing_id,
            metadata=metadata,
            tags=tuple(request.get("tags", ())),
            config=config,
        )
        chunk_count = len(store.get_document_chunk_ids(existing_id))
        return {
            "id": existing_id,
            "kind": "document" if chunk_count else "record",
            "namespace": namespace,
            "bucket": bucket,
            "stored": True,
            "deduplicated": True,
            "chunk_count": chunk_count,
            "warnings": [],
        }

    now = _parse_request_created_at(request.get("created_at")) or datetime.now(UTC)

    if kind == "record":
        record = MemoryRecord(
            id=generate_stable_id(
                "rec", namespace, bucket, fingerprint, source_type, sensitivity
            ),
            namespace=namespace,
            bucket=bucket,
            content=content,
            content_format=content_format,
            source_type=source_type,
            sensitivity=sensitivity,
            metadata=metadata,
            content_fingerprint=fingerprint,
            created_at=now,
            updated_at=now,
            title=request.get("title"),
            tags=tuple(request.get("tags", ())),
            external_id=request.get("external_id"),
            idempotency_key=request.get("idempotency_key"),
            supersedes_id=request.get("supersedes_id"),
        )
        store.save_record(record, signature=signature)
        return {
            "id": record.id,
            "kind": "record",
            "namespace": namespace,
            "bucket": bucket,
            "stored": True,
            "deduplicated": False,
            "chunk_count": 0,
            "warnings": [],
        }

    title = str(request.get("title") or _synthetic_title(content))
    document = MemoryDocument(
        id=generate_stable_id(
            "doc", namespace, bucket, fingerprint, source_type, sensitivity
        ),
        namespace=namespace,
        bucket=bucket,
        title=title,
        raw_content=content,
        source_locator=metadata.get("source_url") if metadata else None,
        source_type=source_type,
        sensitivity=sensitivity,
        metadata=metadata,
        content_fingerprint=fingerprint,
        created_at=now,
        updated_at=now,
        external_id=request.get("external_id"),
        tags=tuple(request.get("tags", ())),
        supersedes_id=request.get("supersedes_id"),
    )
    chunk_values = chunk_text_with_offsets(
        content,
        target_tokens=config.target_chunk_tokens,
        max_tokens=config.max_chunk_tokens,
        overlap_tokens=config.chunk_overlap_tokens,
    )
    chunks = [
        MemoryChunk(
            id=generate_stable_id("chunk", document.id, str(ordinal)),
            document_id=document.id,
            namespace=namespace,
            bucket=bucket,
            ordinal=ordinal,
            chunk_text=chunk_value.text,
            token_count=count_tokens(chunk_value.text),
            sensitivity=sensitivity,
            metadata=metadata,
            created_at=now,
            start_offset=chunk_value.start_offset,
            end_offset=chunk_value.end_offset,
        )
        for ordinal, chunk_value in enumerate(chunk_values, start=1)
    ]
    store.save_document(document, chunks, signature=signature)
    return {
        "id": document.id,
        "kind": "document",
        "namespace": namespace,
        "bucket": bucket,
        "stored": True,
        "deduplicated": False,
        "chunk_count": len(chunks),
        "warnings": [],
    }


def _synthetic_title(content: str) -> str:
    return " ".join(content.split()[:8]) or "Untitled document"


def _parse_request_created_at(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise ValueError("created_at must be an ISO timestamp or datetime")


def _merge_duplicate_metadata(
    store: BaseStore,
    existing_id: str,
    metadata: dict[str, object],
    tags: tuple[str, ...],
    config: NeuroCoreConfig,
) -> None:
    if not config.dedup_merge_metadata:
        return
    record = store.get_record(existing_id, include_archived=True)
    if record is not None:
        store.update_record(
            existing_id,
            patch={
                "metadata": {**record.metadata, **metadata},
                "tags": _merge_tags(record.tags, tags),
            },
            mode="in_place",
        )
        return
    document = store.get_document(existing_id, include_archived=True)
    if document is not None:
        store.update_document(
            existing_id,
            patch={
                "metadata": {**document.metadata, **metadata},
                "tags": _merge_tags(document.tags, tags),
            },
            mode="in_place",
        )


def _merge_tags(existing: tuple[str, ...], new: tuple[str, ...]) -> tuple[str, ...]:
    merged = list(existing)
    for tag in new:
        if tag not in merged:
            merged.append(tag)
    return tuple(merged)
