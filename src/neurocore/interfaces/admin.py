"""Administrative interfaces for updating and deleting NeuroCore content."""

from __future__ import annotations

from neurocore.core.config import NeuroCoreConfig
from neurocore.interfaces.capture import capture_memory
from neurocore.storage.base import BaseStore


def update_memory(
    request: dict[str, object], store: BaseStore, config: NeuroCoreConfig
) -> dict[str, object]:
    _ensure_admin_enabled(config)
    item_id = str(request["id"])
    patch = dict(request.get("patch", {}))
    mode = str(request.get("mode", "in_place"))
    actor = str(request.get("actor", "system"))

    if mode == "replace_content":
        replacement = _replace_content(item_id, patch, store, config)
        store.record_audit(
            actor=actor,
            operation="update",
            target_ids=[item_id, replacement["id"]],
            outcome="success",
        )
        return {
            "id": replacement["id"],
            "updated": True,
            "mode": mode,
            "superseded_id": item_id,
            "warnings": replacement["warnings"],
        }

    if store.get_record(item_id, include_archived=True) is not None:
        store.update_record(item_id, patch=patch, mode=mode)
    elif store.get_document(item_id, include_archived=True) is not None:
        store.update_document(item_id, patch=patch, mode=mode)
    else:
        raise KeyError(item_id)

    store.record_audit(
        actor=actor, operation="update", target_ids=[item_id], outcome="success"
    )
    return {
        "id": item_id,
        "updated": True,
        "mode": mode,
        "superseded_id": None,
        "warnings": [],
    }


def delete_memory(
    request: dict[str, object], store: BaseStore, config: NeuroCoreConfig
) -> dict[str, object]:
    _ensure_admin_enabled(config)
    item_id = str(request["id"])
    mode = str(request.get("mode", "soft_delete"))
    actor = str(request.get("actor", "system"))
    if mode == "hard_delete" and not config.allow_hard_delete:
        raise PermissionError("Hard delete is disabled")

    if mode == "hard_delete":
        store.hard_delete(item_id)
    else:
        store.soft_delete(item_id, reason=str(request.get("reason", "")))
    store.record_audit(
        actor=actor, operation="delete", target_ids=[item_id], outcome="success"
    )
    return {"id": item_id, "deleted": True, "mode": mode, "warnings": []}


def reindex_memory(
    request: dict[str, object], store: BaseStore, config: NeuroCoreConfig
) -> dict[str, object]:
    _ensure_admin_enabled(config)
    ids = [str(item_id) for item_id in request.get("ids", [])]
    actor = str(request.get("actor", "system"))
    processed, failed, warnings = store.reindex(
        ids,
        scope=str(request.get("scope", "records")),
        semantic_backend=config.semantic_backend,
        semantic_model_name=config.semantic_model_name,
    )
    store.record_audit(
        actor=actor, operation="reindex", target_ids=ids, outcome="success"
    )
    return {"processed": processed, "failed": failed, "warnings": warnings}


def _ensure_admin_enabled(config: NeuroCoreConfig) -> None:
    if not config.enable_admin_surface:
        raise PermissionError("Admin surface is disabled")


def _replace_content(
    item_id: str, patch: dict[str, object], store: BaseStore, config: NeuroCoreConfig
) -> dict[str, object]:
    record = store.get_record(item_id, include_archived=True)
    if record is not None:
        replacement = capture_memory(
            {
                "namespace": record.namespace,
                "bucket": record.bucket,
                "sensitivity": record.sensitivity,
                "content": patch["content"],
                "content_format": record.content_format,
                "source_type": record.source_type,
                "title": patch.get("title", record.title),
                "tags": patch.get("tags", record.tags),
                "metadata": patch.get("metadata", record.metadata),
                "external_id": record.external_id,
                "created_at": record.created_at,
                "supersedes_id": item_id,
            },
            store=store,
            config=config,
        )
        store.soft_delete(item_id, reason="superseded")
        return replacement

    document = store.get_document(item_id, include_archived=True)
    if document is not None:
        replacement = capture_memory(
            {
                "namespace": document.namespace,
                "bucket": document.bucket,
                "sensitivity": document.sensitivity,
                "content": patch["content"],
                "content_format": "markdown",
                "source_type": document.source_type,
                "title": patch.get("title", document.title),
                "tags": patch.get("tags", document.tags),
                "metadata": patch.get("metadata", document.metadata),
                "external_id": document.external_id,
                "created_at": document.created_at,
                "supersedes_id": item_id,
                "force_kind": "document",
            },
            store=store,
            config=config,
        )
        store.soft_delete(item_id, reason="superseded")
        return replacement

    raise KeyError(item_id)
