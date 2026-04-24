from datetime import UTC, datetime

from neurocore.core.models import MemoryChunk, MemoryDocument, MemoryRecord
from neurocore.storage.in_memory import InMemoryStore
from neurocore.storage.router import RoutedStore
from neurocore.storage.sqlite_store import SQLiteStore


def test_in_memory_store_can_create_fetch_update_and_tombstone_records():
    store = InMemoryStore()
    record = MemoryRecord(
        id="rec-1",
        namespace="project-alpha",
        bucket="research",
        content="Initial note",
        content_format="markdown",
        source_type="note",
        sensitivity="standard",
        metadata={"author": "user"},
        content_fingerprint="fingerprint-1",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    store.save_record(record, signature="record:note:markdown")
    fetched = store.get_record("rec-1")
    artifact = store.get_artifact("rec-1")
    assert fetched is not None
    assert fetched.content == "Initial note"
    assert artifact is not None
    assert artifact.item_kind == "record"
    assert artifact.text_hash

    updated = store.update_record(
        "rec-1",
        patch={"title": "Updated title", "metadata": {"author": "reviewer"}},
        mode="in_place",
    )
    assert updated.title == "Updated title"
    assert updated.metadata["author"] == "reviewer"

    store.soft_delete("rec-1", reason="cleanup")
    assert store.get_record("rec-1", include_archived=True).archived_at is not None
    assert store.get_artifact("rec-1").archived_at is not None


def test_in_memory_store_tracks_audit_events():
    store = InMemoryStore()

    store.record_audit(
        actor="tester",
        operation="reindex",
        target_ids=["rec-1"],
        outcome="success",
    )

    assert len(store.audit_events) == 1
    event = store.audit_events[0]
    assert event["actor"] == "tester"
    assert event["operation"] == "reindex"


def test_in_memory_store_hides_soft_deleted_documents_by_default():
    store = InMemoryStore()
    document = MemoryDocument(
        id="doc-1",
        namespace="project-alpha",
        bucket="research",
        title="Design note",
        raw_content="Long design note",
        source_locator=None,
        source_type="note",
        sensitivity="standard",
        metadata={},
        content_fingerprint="fingerprint-doc",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    chunk = MemoryChunk(
        id="chunk-1",
        document_id="doc-1",
        namespace="project-alpha",
        bucket="research",
        ordinal=1,
        chunk_text="Long design note",
        token_count=3,
        sensitivity="standard",
        metadata={},
        created_at=datetime.now(UTC),
    )

    store.save_document(document, [chunk], signature="document:note:markdown")
    store.soft_delete("doc-1", reason="cleanup")

    assert store.get_document("doc-1") is None
    assert store.get_document("doc-1", include_archived=True) is not None
    assert store.get_artifact("chunk-1").archived_at is not None


def test_in_memory_store_tracks_document_chunk_artifacts():
    store = InMemoryStore()
    document = MemoryDocument(
        id="doc-artifact-1",
        namespace="project-alpha",
        bucket="research",
        title="Design note",
        raw_content="Long design note",
        source_locator=None,
        source_type="note",
        sensitivity="standard",
        metadata={"topic": "retrieval"},
        content_fingerprint="fingerprint-doc-artifact",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        tags=("alpha",),
    )
    chunk = MemoryChunk(
        id="chunk-artifact-1",
        document_id="doc-artifact-1",
        namespace="project-alpha",
        bucket="research",
        ordinal=1,
        chunk_text="Long design note",
        token_count=3,
        sensitivity="standard",
        metadata={"topic": "retrieval"},
        created_at=datetime.now(UTC),
    )

    store.save_document(document, [chunk], signature="document:note:markdown")

    artifact = store.get_artifact("chunk-artifact-1")

    assert artifact is not None
    assert artifact.item_kind == "chunk"
    assert artifact.document_id == "doc-artifact-1"
    assert artifact.source_type == "note"
    assert artifact.tags == ("alpha",)


def test_in_memory_store_replaces_removed_document_chunks_cleanly():
    store = InMemoryStore()
    original_document = MemoryDocument(
        id="doc-replace-1",
        namespace="project-alpha",
        bucket="research",
        title="Design note",
        raw_content="Long design note",
        source_locator=None,
        source_type="note",
        sensitivity="standard",
        metadata={},
        content_fingerprint="fingerprint-doc-replace",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    first_chunk = MemoryChunk(
        id="chunk-replace-1",
        document_id="doc-replace-1",
        namespace="project-alpha",
        bucket="research",
        ordinal=1,
        chunk_text="first",
        token_count=1,
        sensitivity="standard",
        metadata={},
        created_at=datetime.now(UTC),
    )
    second_chunk = MemoryChunk(
        id="chunk-replace-2",
        document_id="doc-replace-1",
        namespace="project-alpha",
        bucket="research",
        ordinal=2,
        chunk_text="second",
        token_count=1,
        sensitivity="standard",
        metadata={},
        created_at=datetime.now(UTC),
    )
    replacement_document = MemoryDocument(
        id="doc-replace-1",
        namespace="project-alpha",
        bucket="research",
        title="Design note",
        raw_content="Shortened design note",
        source_locator=None,
        source_type="note",
        sensitivity="standard",
        metadata={},
        content_fingerprint="fingerprint-doc-replace",
        created_at=original_document.created_at,
        updated_at=datetime.now(UTC),
    )

    store.save_document(
        original_document,
        [first_chunk, second_chunk],
        signature="document:note:markdown",
    )
    store.save_document(
        replacement_document,
        [first_chunk],
        signature="document:note:markdown",
    )

    assert store.get_chunk("chunk-replace-2") is None
    assert store.get_artifact("chunk-replace-2") is None


def test_sqlite_store_can_persist_and_reload_records(tmp_path):
    database_path = tmp_path / "neurocore.db"
    store = SQLiteStore(database_path)
    record = MemoryRecord(
        id="rec-sqlite-1",
        namespace="project-alpha",
        bucket="research",
        content="Persisted note",
        content_format="markdown",
        source_type="note",
        sensitivity="standard",
        metadata={"author": "user"},
        content_fingerprint="fp-sqlite-1",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    store.save_record(record, signature="record:note:markdown")
    reloaded = SQLiteStore(database_path)

    fetched = reloaded.get_record("rec-sqlite-1")
    artifact = reloaded.get_artifact("rec-sqlite-1")

    assert fetched is not None
    assert fetched.content == "Persisted note"
    assert artifact is not None
    assert artifact.item_kind == "record"
    assert (
        reloaded.find_duplicate("project-alpha", "fp-sqlite-1", "record:note:markdown")
        == "rec-sqlite-1"
    )


def test_sqlite_store_hard_delete_clears_dedup_index(tmp_path):
    database_path = tmp_path / "neurocore.db"
    store = SQLiteStore(database_path)
    record = MemoryRecord(
        id="rec-sqlite-delete-1",
        namespace="project-alpha",
        bucket="research",
        content="Reusable note",
        content_format="markdown",
        source_type="note",
        sensitivity="standard",
        metadata={},
        content_fingerprint="fp-sqlite-delete-1",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    store.save_record(record, signature="record:note:markdown")
    store.hard_delete(record.id)

    assert (
        store.find_duplicate(
            "project-alpha", "fp-sqlite-delete-1", "record:note:markdown"
        )
        is None
    )


def test_routed_store_sends_sealed_content_to_the_sealed_backend(tmp_path):
    primary = SQLiteStore(tmp_path / "primary.db")
    sealed = SQLiteStore(tmp_path / "sealed.db")
    store = RoutedStore(primary_store=primary, sealed_store=sealed)
    sealed_record = MemoryRecord(
        id="rec-sealed-1",
        namespace="project-alpha",
        bucket="ops",
        content="Sealed note",
        content_format="markdown",
        source_type="note",
        sensitivity="sealed",
        metadata={},
        content_fingerprint="fp-sealed-1",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    store.save_record(sealed_record, signature="record:note:markdown")

    assert primary.get_record("rec-sealed-1") is None
    assert sealed.get_record("rec-sealed-1") is not None
    assert primary.get_artifact("rec-sealed-1") is None
    assert sealed.get_artifact("rec-sealed-1") is not None
