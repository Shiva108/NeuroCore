"""Base storage contracts for NeuroCore backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from neurocore.core.models import (
    BrainManifest,
    MemoryChunk,
    MemoryDocument,
    MemoryRecord,
    RetrievalArtifact,
)


@dataclass(frozen=True)
class Candidate:
    kind: str
    item: MemoryRecord | MemoryDocument | MemoryChunk
    artifact: RetrievalArtifact
    document: MemoryDocument | None = None


class BaseStore(ABC):
    @abstractmethod
    def find_duplicate(
        self, namespace: str, fingerprint: str, signature: str
    ) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def save_record(self, record: MemoryRecord, signature: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def save_document(
        self, document: MemoryDocument, chunks: list[MemoryChunk], signature: str
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_record(
        self, item_id: str, include_archived: bool = False
    ) -> MemoryRecord | None:
        raise NotImplementedError

    @abstractmethod
    def get_document(
        self, item_id: str, include_archived: bool = False
    ) -> MemoryDocument | None:
        raise NotImplementedError

    @abstractmethod
    def get_chunk(self, item_id: str) -> MemoryChunk | None:
        raise NotImplementedError

    @abstractmethod
    def get_document_chunk_ids(self, document_id: str) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def get_artifact(self, item_id: str) -> RetrievalArtifact | None:
        raise NotImplementedError

    @abstractmethod
    def list_records(self, include_archived: bool = False) -> list[MemoryRecord]:
        raise NotImplementedError

    @abstractmethod
    def list_documents(self, include_archived: bool = False) -> list[MemoryDocument]:
        raise NotImplementedError

    @abstractmethod
    def list_audit_events(self, limit: int = 20) -> list[dict[str, object]]:
        raise NotImplementedError

    @abstractmethod
    def save_brain(self, brain: BrainManifest) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_brain(
        self, brain_id: str, include_archived: bool = False
    ) -> BrainManifest | None:
        raise NotImplementedError

    @abstractmethod
    def list_brains(self, include_archived: bool = False) -> list[BrainManifest]:
        raise NotImplementedError

    @abstractmethod
    def update_brain(self, brain_id: str, patch: dict[str, object]) -> BrainManifest:
        raise NotImplementedError

    @abstractmethod
    def archive_brain(self, brain_id: str, reason: str) -> BrainManifest:
        raise NotImplementedError

    @abstractmethod
    def update_record(
        self, item_id: str, patch: dict[str, object], mode: str
    ) -> MemoryRecord:
        raise NotImplementedError

    @abstractmethod
    def update_document(
        self, item_id: str, patch: dict[str, object], mode: str
    ) -> MemoryDocument:
        raise NotImplementedError

    @abstractmethod
    def soft_delete(self, item_id: str, reason: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def hard_delete(self, item_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def iter_candidates(
        self,
        namespace: str,
        allowed_buckets: tuple[str, ...],
        include_archived: bool = False,
    ) -> list[Candidate]:
        raise NotImplementedError

    @abstractmethod
    def reindex(
        self,
        ids: list[str],
        scope: str,
        semantic_backend: str = "none",
        semantic_model_name: str | None = None,
    ) -> tuple[int, int, list[str]]:
        raise NotImplementedError

    @abstractmethod
    def record_audit(
        self, actor: str, operation: str, target_ids: list[str], outcome: str
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def has_item(self, item_id: str) -> bool:
        raise NotImplementedError
