"""Storage router for separating standard and sealed NeuroCore content."""

from __future__ import annotations

from neurocore.core.models import (
    BrainManifest,
    MemoryChunk,
    MemoryDocument,
    MemoryRecord,
    RetrievalArtifact,
)
from neurocore.storage.base import BaseStore, Candidate


class RoutedStore(BaseStore):
    def __init__(self, primary_store: BaseStore, sealed_store: BaseStore) -> None:
        self.primary_store = primary_store
        self.sealed_store = sealed_store

    def _route_for_sensitivity(self, sensitivity: str) -> BaseStore:
        if sensitivity == "sealed":
            return self.sealed_store
        return self.primary_store

    def _find_store_for_id(self, item_id: str) -> BaseStore:
        if self.primary_store.has_item(item_id):
            return self.primary_store
        if self.sealed_store.has_item(item_id):
            return self.sealed_store
        raise KeyError(item_id)

    def find_duplicate(
        self, namespace: str, fingerprint: str, signature: str
    ) -> str | None:
        return self.primary_store.find_duplicate(
            namespace, fingerprint, signature
        ) or self.sealed_store.find_duplicate(namespace, fingerprint, signature)

    def save_record(self, record: MemoryRecord, signature: str) -> None:
        self._route_for_sensitivity(record.sensitivity).save_record(record, signature)

    def save_document(
        self, document: MemoryDocument, chunks: list[MemoryChunk], signature: str
    ) -> None:
        self._route_for_sensitivity(document.sensitivity).save_document(
            document, chunks, signature
        )

    def get_record(
        self, item_id: str, include_archived: bool = False
    ) -> MemoryRecord | None:
        return self.primary_store.get_record(
            item_id, include_archived=include_archived
        ) or self.sealed_store.get_record(item_id, include_archived=include_archived)

    def get_document(
        self, item_id: str, include_archived: bool = False
    ) -> MemoryDocument | None:
        return self.primary_store.get_document(
            item_id, include_archived=include_archived
        ) or self.sealed_store.get_document(item_id, include_archived=include_archived)

    def get_chunk(self, item_id: str) -> MemoryChunk | None:
        return self.primary_store.get_chunk(item_id) or self.sealed_store.get_chunk(
            item_id
        )

    def get_document_chunk_ids(self, document_id: str) -> list[str]:
        if self.primary_store.has_item(document_id):
            return self.primary_store.get_document_chunk_ids(document_id)
        if self.sealed_store.has_item(document_id):
            return self.sealed_store.get_document_chunk_ids(document_id)
        return []

    def get_artifact(self, item_id: str) -> RetrievalArtifact | None:
        return self.primary_store.get_artifact(
            item_id
        ) or self.sealed_store.get_artifact(item_id)

    def list_records(self, include_archived: bool = False) -> list[MemoryRecord]:
        records = self.primary_store.list_records(include_archived=include_archived)
        records.extend(
            self.sealed_store.list_records(include_archived=include_archived)
        )
        return sorted(records, key=lambda item: item.created_at, reverse=True)

    def list_documents(self, include_archived: bool = False) -> list[MemoryDocument]:
        documents = self.primary_store.list_documents(include_archived=include_archived)
        documents.extend(
            self.sealed_store.list_documents(include_archived=include_archived)
        )
        return sorted(documents, key=lambda item: item.created_at, reverse=True)

    def list_audit_events(self, limit: int = 20) -> list[dict[str, object]]:
        events = self.primary_store.list_audit_events(limit=limit)
        events.extend(self.sealed_store.list_audit_events(limit=limit))
        return sorted(
            events,
            key=lambda item: item.get("timestamp"),
            reverse=True,
        )[:limit]

    def save_brain(self, brain: BrainManifest) -> None:
        self.primary_store.save_brain(brain)

    def get_brain(
        self, brain_id: str, include_archived: bool = False
    ) -> BrainManifest | None:
        return self.primary_store.get_brain(
            brain_id, include_archived=include_archived
        )

    def list_brains(self, include_archived: bool = False) -> list[BrainManifest]:
        return self.primary_store.list_brains(include_archived=include_archived)

    def update_brain(self, brain_id: str, patch: dict[str, object]) -> BrainManifest:
        return self.primary_store.update_brain(brain_id, patch)

    def archive_brain(self, brain_id: str, reason: str) -> BrainManifest:
        return self.primary_store.archive_brain(brain_id, reason)

    def update_record(
        self, item_id: str, patch: dict[str, object], mode: str
    ) -> MemoryRecord:
        return self._find_store_for_id(item_id).update_record(item_id, patch, mode)

    def update_document(
        self, item_id: str, patch: dict[str, object], mode: str
    ) -> MemoryDocument:
        return self._find_store_for_id(item_id).update_document(item_id, patch, mode)

    def soft_delete(self, item_id: str, reason: str) -> None:
        self._find_store_for_id(item_id).soft_delete(item_id, reason)

    def hard_delete(self, item_id: str) -> None:
        self._find_store_for_id(item_id).hard_delete(item_id)

    def iter_candidates(
        self,
        namespace: str,
        allowed_buckets: tuple[str, ...],
        include_archived: bool = False,
    ) -> list[Candidate]:
        return self.primary_store.iter_candidates(
            namespace, allowed_buckets, include_archived=include_archived
        )

    def reindex(
        self,
        ids: list[str],
        scope: str,
        semantic_backend: str = "none",
        semantic_model_name: str | None = None,
    ) -> tuple[int, int, list[str]]:
        processed = 0
        failed = 0
        warnings: list[str] = []
        for item_id in ids:
            if self.primary_store.has_item(item_id):
                local_processed, local_failed, local_warnings = (
                    self.primary_store.reindex(
                        [item_id],
                        scope=scope,
                        semantic_backend=semantic_backend,
                        semantic_model_name=semantic_model_name,
                    )
                )
                processed += local_processed
                failed += local_failed
                warnings.extend(local_warnings)
            elif self.sealed_store.has_item(item_id):
                local_processed, local_failed, local_warnings = (
                    self.sealed_store.reindex(
                        [item_id],
                        scope=scope,
                        semantic_backend=semantic_backend,
                        semantic_model_name=semantic_model_name,
                    )
                )
                processed += local_processed
                failed += local_failed
                warnings.extend(local_warnings)
            else:
                failed += 1
        return processed, failed, list(dict.fromkeys(warnings))

    def record_audit(
        self, actor: str, operation: str, target_ids: list[str], outcome: str
    ) -> None:
        self.primary_store.record_audit(actor, operation, target_ids, outcome)
        self.sealed_store.record_audit(actor, operation, target_ids, outcome)

    def has_item(self, item_id: str) -> bool:
        return self.primary_store.has_item(item_id) or self.sealed_store.has_item(
            item_id
        )
