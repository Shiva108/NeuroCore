"""Dashboard data interface for NeuroCore."""

from __future__ import annotations

from neurocore.core.config import NeuroCoreConfig
from neurocore.runtime import build_production_backend_choice
from neurocore.storage.base import BaseStore


def build_dashboard_data(
    store: BaseStore, config: NeuroCoreConfig, *, bucket_filter: str | None = None
) -> dict[str, object]:
    """Build a dashboard-safe snapshot of non-sealed repository activity."""
    records = [
        record
        for record in store.list_records(include_archived=True)
        if record.sensitivity != "sealed"
        and (bucket_filter is None or record.bucket == bucket_filter)
    ]
    documents = [
        document
        for document in store.list_documents(include_archived=True)
        if document.sensitivity != "sealed"
        and (bucket_filter is None or document.bucket == bucket_filter)
    ]
    recent_records = []
    for record in records[:10]:
        recent_records.append(
            {
                "id": record.id,
                "title": record.title,
                "content": record.content,
                "namespace": record.namespace,
                "bucket": record.bucket,
                "archived": record.archived_at is not None,
            }
        )
    recent_documents = []
    for document in documents[:10]:
        recent_documents.append(
            {
                "id": document.id,
                "title": document.title,
                "namespace": document.namespace,
                "bucket": document.bucket,
                "summary": document.summary,
                "archived": document.archived_at is not None,
            }
        )

    return {
        "stats": {
            "record_count": len(records),
            "document_count": len(documents),
            "archived_document_count": sum(
                1 for document in documents if document.archived_at is not None
            ),
            "summarized_document_count": sum(
                1 for document in documents if document.summary
            ),
        },
        "recent_documents": recent_documents,
        "recent_records": recent_records,
        "recent_audit_events": store.list_audit_events(limit=10),
        "production_backend": build_production_backend_choice(config).to_dict(),
        "available_buckets": list(config.allowed_buckets),
        "active_bucket_filter": bucket_filter,
    }
