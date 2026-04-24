import pytest

from neurocore.core.config import NeuroCoreConfig
from neurocore.interfaces.admin import delete_memory, reindex_memory, update_memory
from neurocore.interfaces.capture import capture_memory
from neurocore.storage.in_memory import InMemoryStore


def disabled_config() -> NeuroCoreConfig:
    return NeuroCoreConfig(
        default_namespace="project-alpha",
        allowed_buckets=("research",),
        default_sensitivity="standard",
        enable_admin_surface=False,
    )


def enabled_config() -> NeuroCoreConfig:
    return NeuroCoreConfig(
        default_namespace="project-alpha",
        allowed_buckets=("research",),
        default_sensitivity="standard",
        max_atomic_tokens=6,
        target_chunk_tokens=6,
        max_chunk_tokens=8,
        chunk_overlap_tokens=2,
        enable_admin_surface=True,
        allow_hard_delete=False,
    )


def test_admin_operations_are_disabled_by_default():
    store = InMemoryStore()
    config = disabled_config()

    with pytest.raises(PermissionError, match="disabled"):
        update_memory({"id": "rec-1", "patch": {}, "mode": "in_place"}, store, config)

    with pytest.raises(PermissionError, match="disabled"):
        delete_memory({"id": "rec-1", "mode": "soft_delete"}, store, config)

    with pytest.raises(PermissionError, match="disabled"):
        reindex_memory({"ids": ["rec-1"], "scope": "records"}, store, config)


def test_admin_update_and_delete_emit_audit_events():
    store = InMemoryStore()
    config = enabled_config()

    capture = capture_memory(
        {
            "namespace": "project-alpha",
            "bucket": "research",
            "sensitivity": "standard",
            "content": "admin managed note",
            "content_format": "markdown",
            "source_type": "note",
        },
        store=store,
        config=config,
    )

    updated = update_memory(
        {
            "id": capture["id"],
            "patch": {"title": "Reviewed"},
            "mode": "in_place",
            "actor": "tester",
        },
        store,
        config,
    )
    deleted = delete_memory(
        {
            "id": capture["id"],
            "mode": "soft_delete",
            "reason": "cleanup",
            "actor": "tester",
        },
        store,
        config,
    )

    assert updated["updated"] is True
    assert deleted["deleted"] is True
    assert len(store.audit_events) >= 2


def test_admin_update_can_replace_content_and_set_supersedes_id():
    store = InMemoryStore()
    config = enabled_config()

    capture = capture_memory(
        {
            "namespace": "project-alpha",
            "bucket": "research",
            "sensitivity": "standard",
            "content": (
                "Sentence one explains the system. "
                "Sentence two adds retrieval detail. "
                "Sentence three covers isolation policy."
            ),
            "content_format": "markdown",
            "source_type": "note",
            "title": "Before",
        },
        store=store,
        config=config,
    )

    replaced = update_memory(
        {
            "id": capture["id"],
            "patch": {
                "content": "Replacement sentence one. Replacement sentence two.",
                "title": "After",
            },
            "mode": "replace_content",
            "actor": "tester",
        },
        store,
        config,
    )

    assert replaced["id"] != capture["id"]
    assert replaced["superseded_id"] == capture["id"]
    replacement_doc = store.get_document(replaced["id"])
    assert replacement_doc is not None
    assert replacement_doc.supersedes_id == capture["id"]
    assert store.get_document(capture["id"], include_archived=True) is not None


def test_admin_delete_hard_delete_requires_explicit_policy():
    store = InMemoryStore()
    config = enabled_config()
    capture = capture_memory(
        {
            "namespace": "project-alpha",
            "bucket": "research",
            "sensitivity": "standard",
            "content": "hard delete note",
            "content_format": "markdown",
            "source_type": "note",
        },
        store=store,
        config=config,
    )

    with pytest.raises(PermissionError, match="Hard delete"):
        delete_memory(
            {
                "id": capture["id"],
                "mode": "hard_delete",
                "reason": "cleanup",
                "actor": "tester",
            },
            store,
            config,
        )

    permissive_config = NeuroCoreConfig(
        default_namespace="project-alpha",
        allowed_buckets=("research",),
        default_sensitivity="standard",
        enable_admin_surface=True,
        allow_hard_delete=True,
    )
    deleted = delete_memory(
        {
            "id": capture["id"],
            "mode": "hard_delete",
            "reason": "cleanup",
            "actor": "tester",
        },
        store,
        permissive_config,
    )

    assert deleted["deleted"] is True
    assert store.get_record(capture["id"], include_archived=True) is None


def test_admin_hard_delete_allows_recapture_of_the_same_content():
    store = InMemoryStore()
    permissive_config = NeuroCoreConfig(
        default_namespace="project-alpha",
        allowed_buckets=("research",),
        default_sensitivity="standard",
        enable_admin_surface=True,
        allow_hard_delete=True,
    )
    first = capture_memory(
        {
            "namespace": "project-alpha",
            "bucket": "research",
            "sensitivity": "standard",
            "content": "reusable note after hard delete",
            "content_format": "markdown",
            "source_type": "note",
        },
        store=store,
        config=permissive_config,
    )

    delete_memory(
        {
            "id": first["id"],
            "mode": "hard_delete",
            "reason": "cleanup",
            "actor": "tester",
        },
        store,
        permissive_config,
    )
    second = capture_memory(
        {
            "namespace": "project-alpha",
            "bucket": "research",
            "sensitivity": "standard",
            "content": "reusable note after hard delete",
            "content_format": "markdown",
            "source_type": "note",
        },
        store=store,
        config=permissive_config,
    )

    assert second["deduplicated"] is False
    assert store.get_record(second["id"], include_archived=True) is not None


def test_admin_reindex_reports_processed_ids_without_changing_identity():
    store = InMemoryStore()
    config = enabled_config()
    capture = capture_memory(
        {
            "namespace": "project-alpha",
            "bucket": "research",
            "sensitivity": "standard",
            "content": "reindex note",
            "content_format": "markdown",
            "source_type": "note",
        },
        store=store,
        config=config,
    )

    response = reindex_memory(
        {"ids": [capture["id"], "missing-id"], "scope": "records", "actor": "tester"},
        store,
        config,
    )

    assert response["processed"] == 1
    assert response["failed"] == 1
    assert response["warnings"] == []
    assert store.get_record(capture["id"]) is not None


def test_admin_reindex_rebuilds_record_artifacts():
    store = InMemoryStore()
    config = enabled_config()
    capture = capture_memory(
        {
            "namespace": "project-alpha",
            "bucket": "research",
            "sensitivity": "standard",
            "content": "artifact rebuild note",
            "content_format": "markdown",
            "source_type": "note",
        },
        store=store,
        config=config,
    )

    before = store.get_artifact(capture["id"])

    response = reindex_memory(
        {"ids": [capture["id"]], "scope": "records", "actor": "tester"},
        store,
        config,
    )

    after = store.get_artifact(capture["id"])

    assert before is not None
    assert after is not None
    assert after.item_id == capture["id"]
    assert after.indexed_at >= before.indexed_at
    assert response["processed"] == 1
    assert response["failed"] == 0


def test_admin_reindex_rebuilds_document_chunk_artifacts_and_reports_missing_semantic_backend():
    store = InMemoryStore()
    config = NeuroCoreConfig(
        default_namespace="project-alpha",
        allowed_buckets=("research",),
        default_sensitivity="standard",
        max_atomic_tokens=6,
        target_chunk_tokens=6,
        max_chunk_tokens=8,
        chunk_overlap_tokens=2,
        enable_admin_surface=True,
        semantic_backend="sentence-transformers",
    )
    capture = capture_memory(
        {
            "namespace": "project-alpha",
            "bucket": "research",
            "sensitivity": "standard",
            "content": (
                "Sentence one explains the system. "
                "Sentence two adds retrieval detail. "
                "Sentence three covers isolation policy."
            ),
            "content_format": "markdown",
            "source_type": "note",
        },
        store=store,
        config=config,
    )

    chunk_id = store.get_document_chunk_ids(capture["id"])[0]
    before = store.get_artifact(chunk_id)

    response = reindex_memory(
        {"ids": [capture["id"]], "scope": "documents", "actor": "tester"},
        store,
        config,
    )

    after = store.get_artifact(chunk_id)

    assert before is not None
    assert after is not None
    assert after.document_id == capture["id"]
    assert after.indexed_at >= before.indexed_at
    assert response["processed"] == 1
    assert response["failed"] == 0
    assert response["warnings"]
