from neurocore.core.config import NeuroCoreConfig
import pytest

from neurocore.runtime import (
    build_production_backend_choice,
    build_store,
    build_summarizer,
)


def test_build_store_selects_postgres_backends_for_neon_runtime(monkeypatch):
    captured_urls: list[str] = []

    class FakePostgresStore:
        def __init__(self, database_url: str) -> None:
            captured_urls.append(database_url)

    monkeypatch.setattr("neurocore.runtime.PostgresStore", FakePostgresStore)

    config = NeuroCoreConfig(
        default_namespace="project-alpha",
        allowed_buckets=("research",),
        default_sensitivity="standard",
        storage_backend="postgres",
        production_backend_provider="neon",
        production_database_url="postgresql://primary-host/db",
        production_sealed_database_url="postgresql://sealed-host/db",
    )

    store = build_store(config)

    assert captured_urls == [
        "postgresql://primary-host/db",
        "postgresql://sealed-host/db",
    ]
    assert store.primary_store.__class__.__name__ == "FakePostgresStore"
    assert store.sealed_store.__class__.__name__ == "FakePostgresStore"


def test_build_production_backend_choice_redacts_urls():
    config = NeuroCoreConfig(
        default_namespace="project-alpha",
        allowed_buckets=("research",),
        default_sensitivity="standard",
        production_backend_provider="neon",
        production_database_url="postgresql://user:secret@primary-host:5432/db",
        production_sealed_database_url="postgresql://user:secret@sealed-host:5432/db",
    )

    payload = build_production_backend_choice(config).to_dict()

    assert payload["provider"] == "neon"
    assert payload["primary_url"] is None
    assert payload["sealed_url"] is None
    assert payload["primary_target"] == "postgresql://primary-host:5432"
    assert payload["sealed_target"] == "postgresql://sealed-host:5432"


def test_build_store_rejects_postgres_backend_without_production_provider():
    config = NeuroCoreConfig(
        default_namespace="project-alpha",
        allowed_buckets=("research",),
        default_sensitivity="standard",
        storage_backend="postgres",
        production_backend_provider="none",
        production_database_url="postgresql://primary-host/db",
        production_sealed_database_url="postgresql://sealed-host/db",
    )

    with pytest.raises(ValueError, match="production backend provider"):
        build_store(config)


def test_build_summarizer_rejects_duplicate_model_names():
    config = NeuroCoreConfig(
        default_namespace="project-alpha",
        allowed_buckets=("research",),
        default_sensitivity="standard",
        enable_multi_model_consensus=True,
        consensus_provider="openai_compatible",
        consensus_model_names=("model-a", "model-a"),
        consensus_base_url="https://api.example.test/v1",
        consensus_api_key="test-key",
    )

    with pytest.raises(ValueError, match="unique model names"):
        build_summarizer(config)
