from fastapi.testclient import TestClient

from neurocore.adapters import http_api as http_api_module
from neurocore.adapters.http_api import create_app
from neurocore.core.config import NeuroCoreConfig
from neurocore.interfaces.capture import capture_memory
from neurocore.storage.in_memory import InMemoryStore


def build_config(
    enable_admin_surface: bool = False,
    *,
    enable_dashboard: bool = True,
    enable_background_summarization: bool = True,
    enable_multi_model_consensus: bool = False,
) -> NeuroCoreConfig:
    return NeuroCoreConfig(
        default_namespace="project-alpha",
        allowed_buckets=("research",),
        default_sensitivity="standard",
        enable_admin_surface=enable_admin_surface,
        max_atomic_tokens=6,
        enable_dashboard=enable_dashboard,
        enable_background_summarization=enable_background_summarization,
        enable_multi_model_consensus=enable_multi_model_consensus,
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
    audit_response = client.post("/admin/audit", json={})

    assert response.status_code == 403
    assert audit_response.status_code == 403


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


def test_http_api_report_route_returns_fallback_when_consensus_disabled():
    app = create_app(
        store=InMemoryStore(),
        config=build_config(enable_multi_model_consensus=False),
    )
    client = TestClient(app)

    response = client.post(
        "/reports/consensus",
        json={
            "objective": "Generate a review report.",
            "context_markdown": "Retrieved context",
        },
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "fallback-briefing"


def test_http_api_report_route_delegates_to_reporting_interface(monkeypatch):
    called: dict[str, object] = {}

    def fake_generate_consensus_report(
        request, *, store, config, semantic_ranker=None, reporter=None
    ):
        called["request"] = request
        return {
            "report": "## Overview\nReady.",
            "agreement_score": 1.0,
            "model_outputs": {"model-a": "## Overview\nReady."},
            "metadata": {"objective": request["objective"]},
        }

    monkeypatch.setattr(
        http_api_module,
        "generate_consensus_report",
        fake_generate_consensus_report,
    )

    app = create_app(
        store=InMemoryStore(),
        config=build_config(enable_multi_model_consensus=True),
    )
    client = TestClient(app)

    response = client.post(
        "/reports/consensus",
        json={
            "objective": "Generate a review report.",
            "context_markdown": "Retrieved context",
        },
    )

    assert response.status_code == 200
    assert response.json()["report"].startswith("## Overview")
    assert called["request"]["objective"] == "Generate a review report."


def test_http_api_protocol_route_returns_protocol_payload():
    store = InMemoryStore()
    config = build_config(enable_multi_model_consensus=False)
    capture_memory(
        {
            "namespace": "project-alpha",
            "bucket": "research",
            "sensitivity": "standard",
            "content": "critical operator concern with ATT&CK T1190",
            "content_format": "markdown",
            "source_type": "note",
            "tags": ["ciso-concern", "severity:critical"],
            "title": "Critical external exposure",
        },
        store=store,
        config=config,
    )
    app = create_app(store=store, config=config)
    client = TestClient(app)

    response = client.post(
        "/protocols/run",
        json={
            "name": "cti-review-v1",
            "namespace": "project-alpha",
            "query_text": "ATT&CK T1190",
            "allowed_buckets": ["research"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["protocol"]["name"] == "cti-review-v1"
    assert "## Actions" in payload["report"]


def test_http_api_protocol_list_route_returns_protocol_manifests():
    app = create_app(store=InMemoryStore(), config=build_config())
    client = TestClient(app)

    response = client.get("/protocols/list")

    assert response.status_code == 200
    payload = response.json()
    names = {entry["name"] for entry in payload["protocols"]}
    assert "cti-review-v1" in names


def test_http_api_briefing_route_delegates_to_briefing_interface(monkeypatch):
    called: dict[str, object] = {}

    def fake_generate_briefing(
        request, *, store, config, semantic_ranker=None, summarizer=None
    ):
        called["request"] = request
        return {
            "briefing": "## Overview\nReady.",
            "metadata": {"brain_id": request["brain_id"]},
        }

    monkeypatch.setattr(http_api_module, "generate_briefing", fake_generate_briefing)

    app = create_app(store=InMemoryStore(), config=build_config())
    client = TestClient(app)

    response = client.post(
        "/briefings/generate",
        json={
            "brain_id": "project-alpha",
            "query_request": {
                "query_text": "briefing",
                "allowed_buckets": ["research"],
                "sensitivity_ceiling": "standard",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["briefing"].startswith("## Overview")
    assert called["request"]["brain_id"] == "project-alpha"


def test_http_api_report_route_falls_back_to_briefing_when_reporting_disabled():
    store = InMemoryStore()
    config = build_config()
    capture_memory(
        {
            "namespace": "project-alpha",
            "bucket": "research",
            "sensitivity": "standard",
            "content": "Validated SSRF finding with evidence and remediation notes.",
            "content_format": "markdown",
            "source_type": "note",
        },
        store=store,
        config=config,
    )
    app = create_app(store=store, config=config)
    client = TestClient(app)

    response = client.post(
        "/reports/consensus",
        json={
            "objective": "Generate a review report.",
            "query_request": {
                "query_text": "SSRF finding",
                "namespace": "project-alpha",
                "allowed_buckets": ["research"],
                "sensitivity_ceiling": "standard",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "fallback-briefing"
    assert payload["report"].startswith("## Overview")


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
    assert "NeuroCore Reference App" in dashboard_response.text
    assert dashboard_data_response.status_code == 200
    assert dashboard_data_response.json()["production_backend"]["provider"] == "neon"
    assert dashboard_data_response.json()["production_backend"]["primary_url"] is None


def test_http_api_admin_audit_route_returns_findings_when_enabled():
    store = InMemoryStore()
    app = create_app(store=store, config=build_config(enable_admin_surface=True))
    client = TestClient(app)

    client.post(
        "/capture",
        json={
            "namespace": "project-alpha",
            "bucket": "research",
            "sensitivity": "standard",
            "content": "API_KEY=super-secret-value",
            "content_format": "markdown",
            "source_type": "note",
        },
    )

    response = client.post(
        "/admin/audit",
        json={"namespace": "project-alpha", "allowed_buckets": ["research"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["findings"]
    assert payload["candidate_actions"]


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


def test_http_api_dashboard_renders_reference_app_sections():
    app = create_app(
        store=InMemoryStore(), config=build_config(enable_admin_surface=False)
    )
    client = TestClient(app)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "NeuroCore Reference App" in response.text
    assert "Brain Selector" in response.text
    assert "Capture Memory" in response.text
    assert "Search Memory" in response.text
    assert "Briefing Pane" in response.text
    assert "Report Pane" in response.text
    assert "Filter Recent Activity" in response.text
    assert "Admin Actions" not in response.text


def test_http_api_dashboard_shows_admin_section_when_enabled():
    app = create_app(
        store=InMemoryStore(), config=build_config(enable_admin_surface=True)
    )
    client = TestClient(app)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Admin Actions" in response.text


def test_http_api_dashboard_capture_form_delegates_to_capture_interface(
    monkeypatch,
):
    called: dict[str, object] = {}

    def fake_capture_memory(request, *, store, config):
        called["request"] = request
        return {"kind": "record", "id": "rec-demo"}

    monkeypatch.setattr(http_api_module, "capture_memory", fake_capture_memory)

    app = create_app(
        store=InMemoryStore(), config=build_config(enable_admin_surface=False)
    )
    client = TestClient(app)

    response = client.post(
        "/dashboard/capture",
        data={
            "bucket": "research",
            "sensitivity": "standard",
            "content": "dashboard note",
            "content_format": "markdown",
            "source_type": "note",
            "title": "Dashboard Note",
        },
    )

    assert response.status_code == 200
    assert called["request"]["content"] == "dashboard note"
    assert "rec-demo" in response.text


def test_http_api_dashboard_query_form_delegates_to_query_interface(monkeypatch):
    called: dict[str, object] = {}

    def fake_query_memory(request, *, store, config, semantic_ranker):
        called["request"] = request
        return {"results": [{"id": "rec-demo", "content": "match"}]}

    monkeypatch.setattr(http_api_module, "query_memory", fake_query_memory)

    app = create_app(
        store=InMemoryStore(), config=build_config(enable_admin_surface=False)
    )
    client = TestClient(app)

    response = client.post(
        "/dashboard/query",
        data={
            "query_text": "dashboard",
            "allowed_buckets": "research",
            "sensitivity_ceiling": "standard",
        },
    )

    assert response.status_code == 200
    assert called["request"]["query_text"] == "dashboard"
    assert "rec-demo" in response.text


def test_http_api_dashboard_brain_switch_updates_active_brain():
    app = create_app(
        store=InMemoryStore(), config=build_config(enable_admin_surface=False)
    )
    client = TestClient(app)

    response = client.get("/dashboard?brain_id=brain-beta")

    assert response.status_code == 200
    assert "Active brain / namespace: <strong>brain-beta</strong>" in response.text
    assert 'name="brain_id" value="brain-beta"' in response.text


def test_http_api_dashboard_report_form_renders_mode_and_report(monkeypatch):
    def fake_generate_consensus_report(
        request, *, store, config, semantic_ranker=None, reporter=None
    ):
        return {
            "mode": "fallback-briefing",
            "report": "## Overview\nRecovered durable memory report.",
            "metadata": {"brain_id": request["brain_id"]},
        }

    monkeypatch.setattr(
        http_api_module,
        "generate_consensus_report",
        fake_generate_consensus_report,
    )

    app = create_app(
        store=InMemoryStore(), config=build_config(enable_admin_surface=False)
    )
    client = TestClient(app)

    response = client.post(
        "/dashboard/report",
        data={
            "brain_id": "brain-beta",
            "namespace": "brain-beta",
            "objective": "Generate a durable memory report.",
            "query_text": "operator hints",
            "allowed_buckets": "research",
            "sensitivity_ceiling": "standard",
        },
    )

    assert response.status_code == 200
    assert "Report Result" in response.text
    assert "Mode:</strong> fallback-briefing" in response.text
    assert "Recovered durable memory report." in response.text


def test_http_api_dashboard_admin_update_renders_result(monkeypatch):
    called: dict[str, object] = {}

    def fake_update_memory(request, *, store, config):
        called["request"] = request
        return {"updated_ids": ["rec-demo"], "mode": request["mode"]}

    monkeypatch.setattr(http_api_module, "update_memory", fake_update_memory)

    app = create_app(
        store=InMemoryStore(), config=build_config(enable_admin_surface=True)
    )
    client = TestClient(app)

    response = client.post(
        "/dashboard/admin/update",
        data={
            "id": "rec-demo",
            "mode": "replace_content",
            "title": "Updated title",
            "content": "Updated content",
            "brain_id": "brain-beta",
        },
    )

    assert response.status_code == 200
    assert called["request"]["id"] == "rec-demo"
    assert "Admin Result" in response.text
    assert "updated_ids" in response.text


def test_http_api_builds_dashboard_report_payload_with_defaults():
    config = build_config(enable_admin_surface=False)

    payload = http_api_module._build_dashboard_payload(
        "/dashboard/report",
        {
            "query_text": ["operator hints"],
            "allowed_buckets": ["research"],
        },
        config,
    )

    assert payload["brain_id"] == "project-alpha"
    assert payload["objective"] == "Generate a durable memory report."
    assert payload["query_request"]["namespace"] == "project-alpha"
    assert payload["query_request"]["allowed_buckets"] == ["research"]


def test_http_api_builds_dashboard_delete_payload_from_ids():
    config = build_config(enable_admin_surface=True)

    payload = http_api_module._build_dashboard_payload(
        "/dashboard/admin/delete",
        {
            "ids": ["rec-1, rec-2"],
            "mode": ["hard"],
            "reason": ["cleanup"],
        },
        config,
    )

    assert payload["ids"] == ["rec-1", "rec-2"]
    assert payload["mode"] == "hard"
    assert payload["reason"] == "cleanup"
