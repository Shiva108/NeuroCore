from fastapi.testclient import TestClient

from neurocore.adapters.http_api import create_app
from neurocore.core.config import NeuroCoreConfig
from neurocore.storage.in_memory import InMemoryStore


def build_config(
    enable_admin_surface: bool = False,
    *,
    enable_dashboard: bool = True,
    enable_background_summarization: bool = True,
) -> NeuroCoreConfig:
    return NeuroCoreConfig(
        default_namespace="project-alpha",
        allowed_buckets=("research",),
        default_sensitivity="standard",
        enable_admin_surface=enable_admin_surface,
        max_atomic_tokens=6,
        enable_dashboard=enable_dashboard,
        enable_background_summarization=enable_background_summarization,
        production_backend_provider="neon",
        production_database_url="postgresql://primary",
        production_sealed_database_url="postgresql://sealed",
    )


def test_http_api_capture_and_query_delegate_to_core_interfaces():
    store = InMemoryStore()
    app = create_app(store=store, config=build_config())
    client = TestClient(app)

    capture_response = client.post(
        "/capture",
        json={
            "namespace": "project-alpha",
            "bucket": "research",
            "sensitivity": "standard",
            "content": "http note",
            "content_format": "markdown",
            "source_type": "note",
        },
    )
    query_response = client.post(
        "/query",
        json={
            "query_text": "http",
            "namespace": "project-alpha",
            "allowed_buckets": ["research"],
            "sensitivity_ceiling": "standard",
        },
    )

    assert capture_response.status_code == 200
    assert query_response.status_code == 200
    assert query_response.json()["results"][0]["namespace"] == "project-alpha"


def test_http_api_admin_routes_are_gated():
    app = create_app(
        store=InMemoryStore(), config=build_config(enable_admin_surface=False)
    )
    client = TestClient(app)

    response = client.post(
        "/admin/reindex", json={"ids": ["rec-1"], "scope": "records"}
    )

    assert response.status_code == 403


def test_http_api_optional_summary_and_dashboard_routes_are_gated():
    app = create_app(
        store=InMemoryStore(),
        config=build_config(
            enable_admin_surface=True,
            enable_dashboard=False,
            enable_background_summarization=False,
        ),
    )
    client = TestClient(app)

    summary_response = client.post("/summaries/run", json={"limit": 10})
    dashboard_response = client.get("/dashboard")
    dashboard_data_response = client.get("/dashboard/data")

    assert summary_response.status_code == 403
    assert dashboard_response.status_code == 403
    assert dashboard_data_response.status_code == 403


def test_http_api_exposes_ingestion_summary_and_dashboard_surfaces():
    store = InMemoryStore()
    app = create_app(store=store, config=build_config(enable_admin_surface=True))
    client = TestClient(app)

    slack_response = client.post(
        "/ingest/slack",
        json={
            "type": "event_callback",
            "team_id": "T123",
            "event": {
                "type": "message",
                "channel": "C123",
                "user": "U123",
                "text": "slack dashboard note",
                "ts": "1713897900.000100",
            },
            "bucket": "research",
        },
    )
    summary_response = client.post("/summaries/run", json={"limit": 10})
    dashboard_response = client.get("/dashboard")
    dashboard_data_response = client.get("/dashboard/data")

    assert slack_response.status_code == 200
    assert summary_response.status_code == 200
    assert dashboard_response.status_code == 200
    assert "NeuroCore Dashboard" in dashboard_response.text
    assert dashboard_data_response.status_code == 200
    assert dashboard_data_response.json()["production_backend"]["provider"] == "neon"
    assert dashboard_data_response.json()["production_backend"]["primary_url"] is None


def test_http_api_dashboard_excludes_sealed_documents():
    store = InMemoryStore()
    app = create_app(store=store, config=build_config(enable_admin_surface=True))
    client = TestClient(app)

    client.post(
        "/capture",
        json={
            "namespace": "project-alpha",
            "bucket": "research",
            "sensitivity": "sealed",
            "content": (
                "Sentence one explains the system. "
                "Sentence two adds retrieval detail. "
                "Sentence three covers isolation policy."
            ),
            "content_format": "markdown",
            "source_type": "note",
            "force_kind": "document",
            "title": "Sealed Doc",
        },
    )

    response = client.get("/dashboard/data")
    payload = response.json()

    assert response.status_code == 200
    assert payload["stats"]["document_count"] == 0
    assert payload["recent_documents"] == []
