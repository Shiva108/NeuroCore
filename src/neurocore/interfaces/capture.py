"""Capture interface for storing records and documents in NeuroCore."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import re
from typing import Callable

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
from neurocore.runtime import build_summarizer
from neurocore.storage.base import BaseStore


@dataclass(frozen=True)
class CapturePlan:
    content: str
    namespace: str
    bucket: str
    sensitivity: str
    content_format: str
    source_type: str
    metadata: dict[str, object]
    fingerprint: str
    kind: str
    signature: str
    request_tags: tuple[str, ...]
    now: datetime


def capture_memory(
    request: dict[str, object],
    store: BaseStore,
    config: NeuroCoreConfig,
    action_item_generator: Callable[[str], list[str]] | None = None,
) -> dict[str, object]:
    plan = _build_capture_plan(
        request,
        config=config,
        action_item_generator=action_item_generator,
    )
    existing_id = store.find_duplicate(
        plan.namespace, plan.fingerprint, plan.signature
    )
    if existing_id is not None:
        return _handle_deduplicated_capture(
            store=store,
            config=config,
            existing_id=existing_id,
            plan=plan,
            request_tags=tuple(request.get("tags", ())),
        )
    if plan.kind == "record":
        return _store_record_capture(request, store=store, plan=plan)
    return _store_document_capture(request, store=store, config=config, plan=plan)


def _build_capture_plan(
    request: dict[str, object],
    *,
    config: NeuroCoreConfig,
    action_item_generator: Callable[[str], list[str]] | None = None,
) -> CapturePlan:
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
    enriched_metadata, enriched_tags = _enrich_content(
        content,
        action_item_generator=action_item_generator or _build_action_item_generator(config),
    )
    now = _parse_request_created_at(request.get("created_at")) or datetime.now(UTC)
    metadata = {**enriched_metadata, **metadata}
    fingerprint = compute_content_fingerprint(content)
    kind = str(request.get("force_kind") or classify_content_kind(content, config))
    request_tags = _merge_tags(tuple(request.get("tags", ())), enriched_tags)
    return CapturePlan(
        content=content,
        namespace=namespace,
        bucket=bucket,
        sensitivity=sensitivity,
        content_format=content_format,
        source_type=source_type,
        metadata=metadata,
        fingerprint=fingerprint,
        kind=kind,
        signature=f"{kind}:{source_type}:{content_format}:{sensitivity}",
        request_tags=request_tags,
        now=now,
    )


def _handle_deduplicated_capture(
    *,
    store: BaseStore,
    config: NeuroCoreConfig,
    existing_id: str,
    plan: CapturePlan,
    request_tags: tuple[str, ...],
) -> dict[str, object]:
    _merge_duplicate_metadata(
        store=store,
        existing_id=existing_id,
        metadata=plan.metadata,
        tags=request_tags,
        config=config,
    )
    chunk_count = len(store.get_document_chunk_ids(existing_id))
    return _capture_response(
        item_id=existing_id,
        kind="document" if chunk_count else "record",
        namespace=plan.namespace,
        bucket=plan.bucket,
        deduplicated=True,
        chunk_count=chunk_count,
    )


def _store_record_capture(
    request: dict[str, object],
    *,
    store: BaseStore,
    plan: CapturePlan,
) -> dict[str, object]:
    record = MemoryRecord(
        id=generate_stable_id(
            "rec",
            plan.namespace,
            plan.bucket,
            plan.fingerprint,
            plan.source_type,
            plan.sensitivity,
        ),
        namespace=plan.namespace,
        bucket=plan.bucket,
        content=plan.content,
        content_format=plan.content_format,
        source_type=plan.source_type,
        sensitivity=plan.sensitivity,
        metadata=plan.metadata,
        content_fingerprint=plan.fingerprint,
        created_at=plan.now,
        updated_at=plan.now,
        title=request.get("title"),
        tags=plan.request_tags,
        external_id=request.get("external_id"),
        idempotency_key=request.get("idempotency_key"),
        supersedes_id=request.get("supersedes_id"),
    )
    store.save_record(record, signature=plan.signature)
    return _capture_response(
        item_id=record.id,
        kind="record",
        namespace=plan.namespace,
        bucket=plan.bucket,
        deduplicated=False,
        chunk_count=0,
    )


def _store_document_capture(
    request: dict[str, object],
    *,
    store: BaseStore,
    config: NeuroCoreConfig,
    plan: CapturePlan,
) -> dict[str, object]:
    document = MemoryDocument(
        id=generate_stable_id(
            "doc",
            plan.namespace,
            plan.bucket,
            plan.fingerprint,
            plan.source_type,
            plan.sensitivity,
        ),
        namespace=plan.namespace,
        bucket=plan.bucket,
        title=str(request.get("title") or _synthetic_title(plan.content)),
        raw_content=plan.content,
        source_locator=plan.metadata.get("source_url") if plan.metadata else None,
        source_type=plan.source_type,
        sensitivity=plan.sensitivity,
        metadata=plan.metadata,
        content_fingerprint=plan.fingerprint,
        created_at=plan.now,
        updated_at=plan.now,
        external_id=request.get("external_id"),
        tags=plan.request_tags,
        supersedes_id=request.get("supersedes_id"),
    )
    chunks = _build_document_chunks(document, plan=plan, config=config)
    store.save_document(document, chunks, signature=plan.signature)
    return _capture_response(
        item_id=document.id,
        kind="document",
        namespace=plan.namespace,
        bucket=plan.bucket,
        deduplicated=False,
        chunk_count=len(chunks),
    )


def _build_document_chunks(
    document: MemoryDocument,
    *,
    plan: CapturePlan,
    config: NeuroCoreConfig,
) -> list[MemoryChunk]:
    chunk_values = chunk_text_with_offsets(
        plan.content,
        target_tokens=config.target_chunk_tokens,
        max_tokens=config.max_chunk_tokens,
        overlap_tokens=config.chunk_overlap_tokens,
    )
    return [
        MemoryChunk(
            id=generate_stable_id("chunk", document.id, str(ordinal)),
            document_id=document.id,
            namespace=plan.namespace,
            bucket=plan.bucket,
            ordinal=ordinal,
            chunk_text=chunk_value.text,
            token_count=count_tokens(chunk_value.text),
            sensitivity=plan.sensitivity,
            metadata=plan.metadata,
            created_at=plan.now,
            start_offset=chunk_value.start_offset,
            end_offset=chunk_value.end_offset,
        )
        for ordinal, chunk_value in enumerate(chunk_values, start=1)
    ]


def _capture_response(
    *,
    item_id: str,
    kind: str,
    namespace: str,
    bucket: str,
    deduplicated: bool,
    chunk_count: int,
) -> dict[str, object]:
    return {
        "id": item_id,
        "kind": kind,
        "namespace": namespace,
        "bucket": bucket,
        "stored": True,
        "deduplicated": deduplicated,
        "chunk_count": chunk_count,
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


def _enrich_content(
    content: str,
    *,
    action_item_generator: Callable[[str], list[str]] | None = None,
) -> tuple[dict[str, object], tuple[str, ...]]:
    urls = re.findall(r"https?://\S+", content)
    cves = re.findall(r"\bCVE-\d{4}-\d{4,7}\b", content, flags=re.IGNORECASE)
    cwes = re.findall(r"\bCWE-\d+\b", content, flags=re.IGNORECASE)
    attack_ids = re.findall(r"\bT\d{4}(?:\.\d{3})?\b", content, flags=re.IGNORECASE)
    severity_markers = _ordered_unique(
        match.lower()
        for match in re.findall(
            r"\b(critical|high|medium|low|informational)\b",
            content,
            flags=re.IGNORECASE,
        )
    )
    action_items = _extract_action_items(content)
    if action_item_generator is not None:
        try:
            generated_actions = _ordered_unique(action_item_generator(content))
        except Exception:
            generated_actions = []
        if generated_actions:
            action_items = generated_actions
    metadata: dict[str, object] = {}
    if urls:
        metadata["extracted_urls"] = _ordered_unique(urls)
    if cves:
        metadata["extracted_cves"] = _ordered_unique(value.upper() for value in cves)
    if cwes:
        metadata["extracted_cwes"] = _ordered_unique(value.upper() for value in cwes)
    if attack_ids:
        metadata["extracted_attack_ids"] = _ordered_unique(
            value.upper() for value in attack_ids
        )
    if severity_markers:
        metadata["severity_markers"] = severity_markers
    if action_items:
        metadata["suggested_actions"] = action_items
        metadata["action_items_strategy"] = (
            "model-backed" if action_item_generator is not None else "deterministic"
        )
    tags = tuple(severity_markers)
    return metadata, tags


def _extract_action_items(content: str) -> list[str]:
    actions: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", content):
        stripped = sentence.strip()
        if not stripped:
            continue
        lowered = stripped.lower()
        if lowered.startswith(("next action:", "todo:", "action:")):
            actions.append(stripped.split(":", 1)[1].strip() or stripped)
    return _ordered_unique(actions)


def _ordered_unique(values) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            ordered.append(value)
            seen.add(value)
    return ordered


def _build_action_item_generator(
    config: NeuroCoreConfig,
) -> Callable[[str], list[str]] | None:
    if not config.enable_multi_model_consensus:
        return None
    try:
        summarizer = build_summarizer(config)
    except Exception:
        return None

    def generator(content: str) -> list[str]:
        prompt = (
            "Extract up to three concrete operator action items from the following "
            "security memory. Prefer imperative, review-ready next steps.\n\n"
            f"{content}"
        )
        summary = summarizer.summarize(prompt, max_sentences=3)
        text = str(getattr(summary, "summary", "")).strip()
        if not text:
            return []
        actions = [
            item.strip(" -")
            for item in re.split(r"(?:\n+|(?<=[.!?])\s+)", text)
            if item.strip()
        ]
        return actions[:3]

    return generator
