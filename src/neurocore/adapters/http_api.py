"""FastAPI adapter for exposing NeuroCore over HTTP."""

from __future__ import annotations

from collections.abc import Callable
from html import escape
from typing import TypeVar
from urllib.parse import parse_qs

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from neurocore.core.config import NeuroCoreConfig, load_config
from neurocore.interfaces.admin import (
    audit_memory,
    delete_memory,
    reindex_memory,
    update_memory,
)
from neurocore.interfaces.brains import (
    archive_brain,
    create_brain,
    get_brain,
    list_brains,
    update_brain,
)
from neurocore.interfaces.briefing import generate_briefing
from neurocore.interfaces.capture import capture_memory
from neurocore.interfaces.dashboard import build_dashboard_data
from neurocore.interfaces.ingest import ingest_discord_event, ingest_slack_event
from neurocore.interfaces.protocols import list_protocols, run_protocol
from neurocore.interfaces.query import query_memory
from neurocore.interfaces.reporting import generate_consensus_report
from neurocore.interfaces.sessions import (
    capture_session_event,
    checkpoint_session,
    resume_session,
)
from neurocore.interfaces.summaries import run_background_summaries
from neurocore.runtime import build_semantic_ranker, build_store
from neurocore.storage.base import BaseStore

ResponseT = TypeVar("ResponseT")
FormValues = dict[str, list[str]]


def create_app(
    *,
    store: BaseStore | None = None,
    config: NeuroCoreConfig | None = None,
) -> FastAPI:
    """Create the FastAPI application for the configured NeuroCore runtime."""
    config = config or load_config()
    store = store or build_store(config)
    semantic_ranker = build_semantic_ranker(config)

    app = FastAPI(title="NeuroCore")
    app.state.config = config
    _register_core_routes(
        app,
        store=store,
        config=config,
        semantic_ranker=semantic_ranker,
    )
    _register_dashboard_routes(
        app,
        store=store,
        config=config,
        semantic_ranker=semantic_ranker,
    )
    return app


def _register_core_routes(
    app: FastAPI,
    *,
    store: BaseStore,
    config: NeuroCoreConfig,
    semantic_ranker: object | None,
) -> None:
    @app.post("/capture")
    def capture_endpoint(request: dict[str, object]) -> dict[str, object]:
        return capture_memory(request, store=store, config=config)

    @app.post("/brains/create")
    def brain_create_endpoint(request: dict[str, object]) -> dict[str, object]:
        return create_brain(
            request, store=store, default_allowed_buckets=config.allowed_buckets
        )

    @app.post("/brains/get")
    def brain_get_endpoint(request: dict[str, object]) -> dict[str, object]:
        return get_brain(request, store=store)

    @app.post("/brains/list")
    def brain_list_endpoint(request: dict[str, object]) -> dict[str, object]:
        return list_brains(request, store=store)

    @app.post("/brains/update")
    def brain_update_endpoint(request: dict[str, object]) -> dict[str, object]:
        return update_brain(request, store=store)

    @app.post("/brains/archive")
    def brain_archive_endpoint(request: dict[str, object]) -> dict[str, object]:
        return archive_brain(request, store=store)

    @app.post("/query")
    def query_endpoint(request: dict[str, object]) -> dict[str, object]:
        return query_memory(
            request,
            store=store,
            config=config,
            semantic_ranker=semantic_ranker,
        )

    @app.post("/briefings/generate")
    def briefing_endpoint(request: dict[str, object]) -> dict[str, object]:
        return generate_briefing(
            request,
            store=store,
            config=config,
            semantic_ranker=semantic_ranker,
        )

    @app.post("/reports/consensus")
    def report_endpoint(request: dict[str, object]) -> dict[str, object]:
        return _guard_reporting(
            lambda: generate_consensus_report(
                request,
                store=store,
                config=config,
                semantic_ranker=semantic_ranker,
            )
        )

    @app.get("/protocols/list")
    def protocol_list_endpoint() -> dict[str, object]:
        return {"protocols": list_protocols()}

    @app.post("/protocols/run")
    def protocol_endpoint(request: dict[str, object]) -> dict[str, object]:
        return run_protocol(
            request,
            store=store,
            config=config,
            semantic_ranker=semantic_ranker,
        )

    @app.post("/sessions/capture")
    def session_capture_endpoint(request: dict[str, object]) -> dict[str, object]:
        return capture_session_event(request, store=store, config=config)

    @app.post("/sessions/checkpoint")
    def session_checkpoint_endpoint(request: dict[str, object]) -> dict[str, object]:
        return checkpoint_session(request, store=store, config=config)

    @app.post("/sessions/resume")
    def session_resume_endpoint(request: dict[str, object]) -> dict[str, object]:
        return resume_session(request, store=store, config=config)

    @app.post("/admin/update")
    def update_endpoint(request: dict[str, object]) -> dict[str, object]:
        return _guard_admin(lambda: update_memory(request, store=store, config=config))

    @app.post("/admin/delete")
    def delete_endpoint(request: dict[str, object]) -> dict[str, object]:
        return _guard_admin(lambda: delete_memory(request, store=store, config=config))

    @app.post("/admin/reindex")
    def reindex_endpoint(request: dict[str, object]) -> dict[str, object]:
        return _guard_admin(lambda: reindex_memory(request, store=store, config=config))

    @app.post("/admin/audit")
    def audit_endpoint(request: dict[str, object]) -> dict[str, object]:
        return _guard_admin(lambda: audit_memory(request, store=store, config=config))

    @app.post("/ingest/slack")
    def slack_ingest_endpoint(request: dict[str, object]) -> dict[str, object]:
        return ingest_slack_event(request, store=store, config=config)

    @app.post("/ingest/discord")
    def discord_ingest_endpoint(request: dict[str, object]) -> dict[str, object]:
        return ingest_discord_event(request, store=store, config=config)

    @app.post("/summaries/run")
    def run_summaries_endpoint(request: dict[str, object]) -> dict[str, object]:
        return _guard_summaries(
            lambda: run_background_summaries(request, store=store, config=config)
        )


def _register_dashboard_routes(
    app: FastAPI,
    *,
    store: BaseStore,
    config: NeuroCoreConfig,
    semantic_ranker: object | None,
) -> None:
    _register_dashboard_read_routes(
        app,
        store=store,
        config=config,
        semantic_ranker=semantic_ranker,
    )
    _register_dashboard_admin_routes(app, store=store, config=config)


def _register_dashboard_read_routes(
    app: FastAPI,
    *,
    store: BaseStore,
    config: NeuroCoreConfig,
    semantic_ranker: object | None,
) -> None:
    @app.get("/dashboard/data")
    def dashboard_data_endpoint(
        bucket: str | None = None, brain_id: str | None = None
    ) -> dict[str, object]:
        return _guard_dashboard(
            lambda: build_dashboard_data(
                store=store, config=config, bucket_filter=bucket, brain_id=brain_id
            ),
            enabled=config.enable_dashboard,
        )

    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard_endpoint(
        bucket: str | None = None, brain_id: str | None = None
    ) -> str:
        data = _guard_dashboard(
            lambda: build_dashboard_data(
                store=store, config=config, bucket_filter=bucket, brain_id=brain_id
            ),
            enabled=config.enable_dashboard,
        )
        return _render_reference_app(
            data=data,
            config=config,
            capture_result=None,
            query_result=None,
            briefing_result=None,
            report_result=None,
            brain_result=None,
            session_result=None,
            protocol_result=None,
            admin_result=None,
            active_brain_id=brain_id or config.default_namespace,
        )

    @app.post("/dashboard/capture", response_class=HTMLResponse)
    async def dashboard_capture_endpoint(request: Request) -> str:
        payload = await _parse_form_payload(request)
        capture_result = _guard_dashboard(
            lambda: capture_memory(payload, store=store, config=config),
            enabled=config.enable_dashboard,
        )
        return _render_dashboard_response(
            payload,
            store=store,
            config=config,
            capture_result=capture_result,
        )

    @app.post("/dashboard/query", response_class=HTMLResponse)
    async def dashboard_query_endpoint(request: Request) -> str:
        payload = await _parse_form_payload(request)
        query_result = _guard_dashboard(
            lambda: query_memory(
                payload,
                store=store,
                config=config,
                semantic_ranker=semantic_ranker,
            ),
            enabled=config.enable_dashboard,
        )
        return _render_dashboard_response(
            payload,
            store=store,
            config=config,
            query_result=query_result,
        )

    @app.post("/dashboard/briefing", response_class=HTMLResponse)
    async def dashboard_briefing_endpoint(request: Request) -> str:
        payload = await _parse_form_payload(request)
        briefing_result = _guard_dashboard(
            lambda: generate_briefing(
                payload,
                store=store,
                config=config,
                semantic_ranker=semantic_ranker,
            ),
            enabled=config.enable_dashboard,
        )
        return _render_dashboard_response(
            payload,
            store=store,
            config=config,
            briefing_result=briefing_result,
        )

    @app.post("/dashboard/report", response_class=HTMLResponse)
    async def dashboard_report_endpoint(request: Request) -> str:
        payload = await _parse_form_payload(request)
        report_result = _guard_dashboard(
            lambda: _dashboard_report_result(
                payload,
                store=store,
                config=config,
                semantic_ranker=semantic_ranker,
            ),
            enabled=config.enable_dashboard,
        )
        return _render_dashboard_response(
            payload,
            store=store,
            config=config,
            report_result=report_result,
        )

    @app.post("/dashboard/brain/create", response_class=HTMLResponse)
    async def dashboard_brain_create_endpoint(request: Request) -> str:
        payload = await _parse_form_payload(request)
        brain_result = _guard_dashboard(
            lambda: create_brain(
                payload,
                store=store,
                default_allowed_buckets=config.allowed_buckets,
            ),
            enabled=config.enable_dashboard,
        )
        return _render_dashboard_response(
            payload,
            store=store,
            config=config,
            brain_result=brain_result,
        )

    @app.post("/dashboard/brain/archive", response_class=HTMLResponse)
    async def dashboard_brain_archive_endpoint(request: Request) -> str:
        payload = await _parse_form_payload(request)
        brain_result = _guard_dashboard(
            lambda: archive_brain(payload, store=store),
            enabled=config.enable_dashboard,
        )
        return _render_dashboard_response(
            payload,
            store=store,
            config=config,
            brain_result=brain_result,
        )

    @app.post("/dashboard/session/resume", response_class=HTMLResponse)
    async def dashboard_session_resume_endpoint(request: Request) -> str:
        payload = await _parse_form_payload(request)
        session_result = _guard_dashboard(
            lambda: resume_session(payload, store=store, config=config),
            enabled=config.enable_dashboard,
        )
        return _render_dashboard_response(
            payload,
            store=store,
            config=config,
            session_result=session_result,
        )

    @app.post("/dashboard/protocol/run", response_class=HTMLResponse)
    async def dashboard_protocol_endpoint(request: Request) -> str:
        payload = await _parse_form_payload(request)
        protocol_result = _guard_dashboard(
            lambda: run_protocol(
                payload,
                store=store,
                config=config,
                semantic_ranker=semantic_ranker,
            ),
            enabled=config.enable_dashboard,
        )
        return _render_dashboard_response(
            payload,
            store=store,
            config=config,
            protocol_result=protocol_result,
        )


def _register_dashboard_admin_routes(
    app: FastAPI,
    *,
    store: BaseStore,
    config: NeuroCoreConfig,
) -> None:
    @app.post("/dashboard/admin/update", response_class=HTMLResponse)
    async def dashboard_update_endpoint(request: Request) -> str:
        payload = await _parse_form_payload(request)
        admin_result = _guard_dashboard(
            lambda: _guard_admin(lambda: update_memory(payload, store=store, config=config)),
            enabled=config.enable_dashboard,
        )
        return _render_dashboard_response(
            payload,
            store=store,
            config=config,
            admin_result=admin_result,
        )

    @app.post("/dashboard/admin/reindex", response_class=HTMLResponse)
    async def dashboard_reindex_endpoint(request: Request) -> str:
        payload = await _parse_form_payload(request)
        admin_result = _guard_dashboard(
            lambda: _guard_admin(
                lambda: reindex_memory(payload, store=store, config=config)
            ),
            enabled=config.enable_dashboard,
        )
        return _render_dashboard_response(
            payload,
            store=store,
            config=config,
            admin_result=admin_result,
        )

    @app.post("/dashboard/admin/audit", response_class=HTMLResponse)
    async def dashboard_audit_endpoint(request: Request) -> str:
        payload = await _parse_form_payload(request)
        admin_result = _guard_dashboard(
            lambda: _guard_admin(lambda: audit_memory(payload, store=store, config=config)),
            enabled=config.enable_dashboard,
        )
        return _render_dashboard_response(
            payload,
            store=store,
            config=config,
            admin_result=admin_result,
        )

    @app.post("/dashboard/admin/delete", response_class=HTMLResponse)
    async def dashboard_delete_endpoint(request: Request) -> str:
        payload = await _parse_form_payload(request)
        admin_result = _guard_dashboard(
            lambda: _guard_admin(lambda: delete_memory(payload, store=store, config=config)),
            enabled=config.enable_dashboard,
        )
        return _render_dashboard_response(
            payload,
            store=store,
            config=config,
            admin_result=admin_result,
        )


def _guard_admin(fn: Callable[[], ResponseT]) -> ResponseT:
    """Translate admin permission errors into HTTP responses."""
    try:
        return fn()
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _guard_dashboard(fn: Callable[[], ResponseT], *, enabled: bool) -> ResponseT:
    """Guard dashboard-only routes behind the configured feature flag."""
    try:
        return _guard_feature(fn, enabled=enabled, message="Dashboard is disabled")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _guard_summaries(fn: Callable[[], ResponseT]) -> ResponseT:
    """Translate summary permission errors into HTTP responses."""
    try:
        return fn()
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _guard_reporting(fn: Callable[[], ResponseT]) -> ResponseT:
    """Translate reporting permission errors into HTTP responses."""
    try:
        return fn()
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _guard_feature(
    fn: Callable[[], ResponseT], *, enabled: bool, message: str
) -> ResponseT:
    """Run a handler only when the corresponding feature flag is enabled."""
    if not enabled:
        raise PermissionError(message)
    return fn()


def _render_dashboard_response(
    payload: dict[str, object],
    *,
    store: BaseStore,
    config: NeuroCoreConfig,
    capture_result: dict[str, object] | None = None,
    query_result: dict[str, object] | None = None,
    briefing_result: dict[str, object] | None = None,
    report_result: dict[str, object] | None = None,
    brain_result: dict[str, object] | None = None,
    session_result: dict[str, object] | None = None,
    protocol_result: dict[str, object] | None = None,
    admin_result: dict[str, object] | None = None,
) -> str:
    data = _guard_dashboard(
        lambda: build_dashboard_data(
            store=store,
            config=config,
            bucket_filter=_optional_str(payload.get("bucket_filter")),
            brain_id=_optional_str(payload.get("brain_id"))
            or _optional_str(payload.get("namespace")),
        ),
        enabled=config.enable_dashboard,
    )
    return _render_reference_app(
        data=data,
        config=config,
        capture_result=capture_result,
        query_result=query_result,
        briefing_result=briefing_result,
        report_result=report_result,
        brain_result=brain_result,
        session_result=session_result,
        protocol_result=protocol_result,
        admin_result=admin_result,
        active_brain_id=_resolve_dashboard_brain_id(payload, config),
    )


async def _parse_form_payload(request: Request) -> dict[str, object]:
    raw = (await request.body()).decode("utf-8")
    form_values = parse_qs(raw, keep_blank_values=False)
    payload = _build_dashboard_payload(
        request.url.path, form_values, request.app.state.config
    )
    bucket_filter = _first_value(form_values, "bucket_filter")
    if bucket_filter:
        payload["bucket_filter"] = bucket_filter
    return {key: value for key, value in payload.items() if value is not None}


def _build_dashboard_payload(
    path: str,
    form_values: FormValues,
    config: NeuroCoreConfig,
) -> dict[str, object]:
    for suffix, builder in (
        ("/brain/create", _build_brain_create_form_payload),
        ("/brain/archive", _build_brain_archive_form_payload),
        ("/capture", _build_capture_form_payload),
        ("/query", _build_query_form_payload),
        ("/briefing", _build_briefing_form_payload),
        ("/report", _build_report_form_payload),
        ("/protocol/run", _build_protocol_form_payload),
        ("/session/resume", _build_session_resume_form_payload),
        ("/update", _build_update_form_payload),
        ("/reindex", _build_reindex_form_payload),
        ("/audit", _build_audit_form_payload),
        ("/delete", _build_delete_form_payload),
    ):
        if path.endswith(suffix):
            return builder(form_values, config)
    return _build_query_form_payload(form_values, config)


def _build_brain_create_form_payload(
    form_values: FormValues, config: NeuroCoreConfig
) -> dict[str, object]:
    brain_id = _first_value(form_values, "brain_id") or _form_namespace(
        form_values, config
    )
    namespace = _first_value(form_values, "namespace") or brain_id
    owner = _first_value(form_values, "owner")
    tags = _split_csv_values(_first_value(form_values, "tags"))
    return {
        "brain_id": brain_id,
        "namespace": namespace,
        "display_name": _first_value(form_values, "display_name") or brain_id,
        "description": _first_value(form_values, "description") or "",
        "owner": owner,
        "tags": tags,
        "default_allowed_buckets": _split_csv_values(
            _first_value(form_values, "default_allowed_buckets")
        )
        or list(config.allowed_buckets),
    }


def _build_brain_archive_form_payload(
    form_values: FormValues, config: NeuroCoreConfig
) -> dict[str, object]:
    del config
    return {
        "brain_id": _first_value(form_values, "brain_id"),
        "reason": _first_value(form_values, "reason") or "dashboard archive",
    }


def _build_capture_form_payload(
    form_values: FormValues, config: NeuroCoreConfig
) -> dict[str, object]:
    brain_id = _first_value(form_values, "brain_id") or _form_namespace(
        form_values, config
    )
    return {
        "brain_id": brain_id,
        "namespace": _first_value(form_values, "namespace") or None,
        "bucket": _first_value(form_values, "bucket"),
        "sensitivity": _first_value(form_values, "sensitivity"),
        "content": _first_value(form_values, "content"),
        "content_format": _first_value(form_values, "content_format") or "markdown",
        "source_type": _first_value(form_values, "source_type") or "note",
        "title": _first_value(form_values, "title") or None,
    }


def _build_query_form_payload(
    form_values: FormValues, config: NeuroCoreConfig
) -> dict[str, object]:
    return _build_query_request_from_form(form_values, config)


def _build_briefing_form_payload(
    form_values: FormValues, config: NeuroCoreConfig
) -> dict[str, object]:
    namespace = _form_namespace(form_values, config)
    return {
        "brain_id": _first_value(form_values, "brain_id") or namespace,
        "query_request": _build_query_request_from_form(form_values, config),
        "include_operator_hints": True,
    }


def _build_report_form_payload(
    form_values: FormValues, config: NeuroCoreConfig
) -> dict[str, object]:
    namespace = _form_namespace(form_values, config)
    return {
        "brain_id": _first_value(form_values, "brain_id") or namespace,
        "objective": _first_value(form_values, "objective")
        or "Generate a durable memory report.",
        "query_request": _build_query_request_from_form(form_values, config),
        "max_items": 5,
    }


def _build_update_form_payload(
    form_values: FormValues, config: NeuroCoreConfig
) -> dict[str, object]:
    return {
        "id": _first_value(form_values, "id"),
        "mode": _first_value(form_values, "mode") or "replace_content",
        "patch": {
            "content": _first_value(form_values, "content"),
            "title": _first_value(form_values, "title"),
        },
        "actor": _first_value(form_values, "actor") or "dashboard",
    }


def _build_delete_form_payload(
    form_values: FormValues, config: NeuroCoreConfig
) -> dict[str, object]:
    ids = _first_value(form_values, "ids") or ""
    return {
        "ids": [value.strip() for value in ids.split(",") if value.strip()],
        "scope": _first_value(form_values, "scope") or "records",
        "mode": _first_value(form_values, "mode") or "soft",
        "reason": _first_value(form_values, "reason") or "dashboard request",
    }


def _build_query_request_from_form(
    form_values: FormValues, config: NeuroCoreConfig
) -> dict[str, object]:
    allowed_buckets = _form_allowed_buckets(form_values, config)
    return {
        "brain_id": _first_value(form_values, "brain_id")
        or _form_namespace(form_values, config),
        "query_text": _first_value(form_values, "query_text"),
        "namespace": _form_namespace(form_values, config),
        "allowed_buckets": allowed_buckets,
        "sensitivity_ceiling": _first_value(form_values, "sensitivity_ceiling")
        or config.default_sensitivity,
    }


def _form_allowed_buckets(
    form_values: FormValues, config: NeuroCoreConfig
) -> list[str]:
    raw = _first_value(form_values, "allowed_buckets") or ",".join(
        config.allowed_buckets
    )
    return [value.strip() for value in raw.split(",") if value.strip()]


def _form_namespace(form_values: FormValues, config: NeuroCoreConfig) -> str:
    return (
        _first_value(form_values, "namespace")
        or _first_value(form_values, "brain_id")
        or config.default_namespace
    )


def _split_csv_values(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [value.strip() for value in raw.split(",") if value.strip()]


def _build_protocol_form_payload(
    form_values: FormValues, config: NeuroCoreConfig
) -> dict[str, object]:
    payload = _build_query_request_from_form(form_values, config)
    payload["name"] = _first_value(form_values, "name") or "resume-brain-v1"
    payload["objective"] = _first_value(form_values, "objective") or None
    payload["max_items"] = int(_first_value(form_values, "max_items") or 8)
    payload["session_id"] = _first_value(form_values, "session_id")
    return {key: value for key, value in payload.items() if value is not None}


def _build_session_resume_form_payload(
    form_values: FormValues, config: NeuroCoreConfig
) -> dict[str, object]:
    payload = _build_query_request_from_form(form_values, config)
    payload["session_id"] = _first_value(form_values, "session_id")
    payload["source_client"] = _first_value(form_values, "source_client")
    payload["max_items"] = int(_first_value(form_values, "max_items") or 6)
    return {key: value for key, value in payload.items() if value is not None}


def _build_reindex_form_payload(
    form_values: FormValues, config: NeuroCoreConfig
) -> dict[str, object]:
    del config
    ids = _first_value(form_values, "ids") or ""
    return {
        "ids": [value.strip() for value in ids.split(",") if value.strip()],
        "scope": _first_value(form_values, "scope") or "records",
    }


def _build_audit_form_payload(
    form_values: FormValues, config: NeuroCoreConfig
) -> dict[str, object]:
    return {
        "brain_id": _first_value(form_values, "brain_id")
        or _form_namespace(form_values, config),
        "namespace": _form_namespace(form_values, config),
        "allowed_buckets": _form_allowed_buckets(form_values, config),
    }


def _render_reference_app(
    *,
    data: dict[str, object],
    config: NeuroCoreConfig,
    capture_result: dict[str, object] | None,
    query_result: dict[str, object] | None,
    briefing_result: dict[str, object] | None,
    report_result: dict[str, object] | None,
    brain_result: dict[str, object] | None,
    session_result: dict[str, object] | None,
    protocol_result: dict[str, object] | None,
    admin_result: dict[str, object] | None,
    active_brain_id: str,
) -> str:
    stats = data["stats"]
    production = data["production_backend"]
    available_buckets = data.get("available_buckets", [])
    active_bucket = data.get("active_bucket_filter") or ""
    capture_feedback = _render_result_block("Capture Result", capture_result)
    query_feedback = _render_result_block("Search Result", query_result)
    briefing_feedback = _render_result_block("Briefing Result", briefing_result)
    report_feedback = _render_result_block("Report Result", report_result)
    brain_feedback = _render_result_block("Brain Result", brain_result)
    session_feedback = _render_result_block("Session Result", session_result)
    protocol_feedback = _render_result_block("Protocol Result", protocol_result)
    admin_feedback = _render_result_block("Admin Result", admin_result)
    recent_documents = _render_document_list(data["recent_documents"])
    recent_records = _render_record_list(data.get("recent_records", []))
    brains = _render_brain_list(data.get("brains", []), active_brain_id)
    connectors = _render_connector_list(data.get("connectors", []))
    stats_line = (
        f"Records: {stats['record_count']} | Documents: {stats['document_count']} | "
        f"Summarized: {stats['summarized_document_count']}"
    )
    production_line = (
        f"Production backend: {production['provider']} ({production['status']})"
    )
    capture_bucket = escape(str(active_bucket or "research"))
    brain_id = escape(active_brain_id or config.default_namespace)
    default_sensitivity = escape(config.default_sensitivity)
    allowed_bucket_values = escape(",".join(available_buckets) or str(active_bucket))
    bucket_options = "".join(
        _render_bucket_option(bucket, active_bucket) for bucket in available_buckets
    )
    protocol_options = "".join(_render_protocol_option(protocol) for protocol in list_protocols())
    sensitivity_filter_input = _render_sensitivity_filter_input(default_sensitivity)
    admin_section = (
        _render_admin_section(brain_id, active_bucket) if config.enable_admin_surface else ""
    )
    return f"""
    <html>
      <head><title>NeuroCore Reference App</title></head>
      <body>
        <h1>NeuroCore Reference App</h1>
        <p>{stats_line}</p>
        <p>{production_line}</p>
        {_render_brain_selector_section(brain_id, active_bucket)}
        {_render_brain_management_section(brain_id, allowed_bucket_values, brain_feedback)}
        {_render_capture_section(
            brain_id,
            capture_bucket,
            default_sensitivity,
            active_bucket,
            capture_feedback,
        )}
        {_render_search_section(
            brain_id,
            allowed_bucket_values,
            sensitivity_filter_input,
            active_bucket,
            query_feedback,
        )}
        {_render_briefing_section(
            brain_id,
            allowed_bucket_values,
            sensitivity_filter_input,
            active_bucket,
            briefing_feedback,
        )}
        {_render_report_section(
            brain_id,
            allowed_bucket_values,
            sensitivity_filter_input,
            active_bucket,
            report_feedback,
        )}
        {_render_protocol_section(
            brain_id,
            allowed_bucket_values,
            sensitivity_filter_input,
            active_bucket,
            protocol_options,
            protocol_feedback,
        )}
        {_render_session_resume_section(
            brain_id,
            allowed_bucket_values,
            sensitivity_filter_input,
            active_bucket,
            session_feedback,
        )}
        {_render_filter_section(bucket_options)}
        <section>
          <h2>Brains</h2>
          <ul>{brains}</ul>
        </section>
        <section>
          <h2>Recent Memory</h2>
          <ul>{recent_records}</ul>
        </section>
        <section>
          <h2>Recent Documents</h2>
          <ul>{recent_documents}</ul>
        </section>
        <section>
          <h2>Recent Memory / Audit</h2>
          <ul>{_render_audit_list(data.get("recent_audit_events", []))}</ul>
        </section>
        <section>
          <h2>Connector Status</h2>
          <ul>{connectors}</ul>
        </section>
        {admin_section}
        {admin_feedback}
      </body>
    </html>
    """


def _render_sensitivity_filter_input(default_sensitivity: str) -> str:
    return (
        '<label>Sensitivity ceiling <input type="text" '
        f'name="sensitivity_ceiling" value="{default_sensitivity}" /></label>'
    )


def _render_brain_selector_section(brain_id: str, active_bucket: object) -> str:
    return f"""
        <section>
          <h2>Brain Selector</h2>
          <p>Active brain / namespace: <strong>{brain_id}</strong></p>
          <p><small>`brain_id` is the UX alias; core storage still enforces the underlying namespace.</small></p>
          <form method="get" action="/dashboard">
            <label>Brain ID <input type="text" name="brain_id" value="{brain_id}" /></label>
            <input type="hidden" name="bucket" value="{escape(str(active_bucket))}" />
            <button type="submit">Switch Brain</button>
          </form>
        </section>
    """


def _render_brain_management_section(
    brain_id: str, allowed_bucket_values: str, brain_feedback: str
) -> str:
    return f"""
        <section>
          <h2>Brain Management</h2>
          <form method="post" action="/dashboard/brain/create">
            <label>Brain ID <input type="text" name="brain_id" value="{brain_id}" /></label>
            <label>Namespace <input type="text" name="namespace" value="{brain_id}" /></label>
            <label>Display name <input type="text" name="display_name" value="{brain_id}" /></label>
            <label>Description <input type="text" name="description" value="OpenBrain workspace" /></label>
            <label>Owner <input type="text" name="owner" value="dashboard" /></label>
            <label>Tags <input type="text" name="tags" value="openbrain,reference-app" /></label>
            <label>Default buckets <input type="text" name="default_allowed_buckets" value="{allowed_bucket_values}" /></label>
            <button type="submit">Create / Refresh Brain</button>
          </form>
          <form method="post" action="/dashboard/brain/archive">
            <label>Brain ID <input type="text" name="brain_id" value="{brain_id}" /></label>
            <label>Reason <input type="text" name="reason" value="dashboard archive" /></label>
            <button type="submit">Archive Brain</button>
          </form>
          {brain_feedback}
        </section>
    """


def _render_capture_section(
    brain_id: str,
    capture_bucket: str,
    default_sensitivity: str,
    active_bucket: object,
    capture_feedback: str,
) -> str:
    return f"""
        <section>
          <h2>Capture Memory</h2>
          <form method="post" action="/dashboard/capture">
            <label>Brain ID <input type="text" name="brain_id" value="{brain_id}" /></label>
            <label>Namespace <input type="text" name="namespace" value="{brain_id}" /></label>
            <label>Bucket <input type="text" name="bucket" value="{capture_bucket}" /></label>
            <label>Sensitivity <input type="text" name="sensitivity" value="{default_sensitivity}" /></label>
            <label>Title <input type="text" name="title" /></label>
            <label>Content format <input type="text" name="content_format" value="markdown" /></label>
            <label>Source type <input type="text" name="source_type" value="note" /></label>
            <label>Content <textarea name="content"></textarea></label>
            <input type="hidden" name="bucket_filter" value="{escape(str(active_bucket))}" />
            <button type="submit">Capture</button>
          </form>
          {capture_feedback}
        </section>
    """


def _render_search_section(
    brain_id: str,
    allowed_bucket_values: str,
    sensitivity_filter_input: str,
    active_bucket: object,
    query_feedback: str,
) -> str:
    return f"""
        <section>
          <h2>Search Memory</h2>
          <form method="post" action="/dashboard/query">
            <label>Brain ID <input type="text" name="brain_id" value="{brain_id}" /></label>
            <label>Namespace <input type="text" name="namespace" value="{brain_id}" /></label>
            <label>Query text <input type="text" name="query_text" /></label>
            <label>Allowed buckets <input type="text" name="allowed_buckets" value="{allowed_bucket_values}" /></label>
            {sensitivity_filter_input}
            <input type="hidden" name="bucket_filter" value="{escape(str(active_bucket))}" />
            <button type="submit">Search</button>
          </form>
          {query_feedback}
        </section>
    """


def _render_briefing_section(
    brain_id: str,
    allowed_bucket_values: str,
    sensitivity_filter_input: str,
    active_bucket: object,
    briefing_feedback: str,
) -> str:
    return f"""
        <section>
          <h2>Briefing Pane</h2>
          <form method="post" action="/dashboard/briefing">
            <label>Brain ID <input type="text" name="brain_id" value="{brain_id}" /></label>
            <label>Namespace <input type="text" name="namespace" value="{brain_id}" /></label>
            <label>Query text <input type="text" name="query_text" /></label>
            <label>Allowed buckets <input type="text" name="allowed_buckets" value="{allowed_bucket_values}" /></label>
            {sensitivity_filter_input}
            <input type="hidden" name="bucket_filter" value="{escape(str(active_bucket))}" />
            <button type="submit">Generate Briefing</button>
          </form>
          {briefing_feedback}
        </section>
    """


def _render_report_section(
    brain_id: str,
    allowed_bucket_values: str,
    sensitivity_filter_input: str,
    active_bucket: object,
    report_feedback: str,
) -> str:
    return f"""
        <section>
          <h2>Report Pane</h2>
          <p><small>When consensus reporting is unavailable, this pane degrades to a synthesized briefing instead of returning a hard failure.</small></p>
          <form method="post" action="/dashboard/report">
            <label>Brain ID <input type="text" name="brain_id" value="{brain_id}" /></label>
            <label>Namespace <input type="text" name="namespace" value="{brain_id}" /></label>
            <label>Objective <input type="text" name="objective" value="Generate a durable memory report." /></label>
            <label>Query text <input type="text" name="query_text" /></label>
            <label>Allowed buckets <input type="text" name="allowed_buckets" value="{allowed_bucket_values}" /></label>
            {sensitivity_filter_input}
            <input type="hidden" name="bucket_filter" value="{escape(str(active_bucket))}" />
            <button type="submit">Generate Report</button>
          </form>
          {report_feedback}
        </section>
    """


def _render_protocol_section(
    brain_id: str,
    allowed_bucket_values: str,
    sensitivity_filter_input: str,
    active_bucket: object,
    protocol_options: str,
    protocol_feedback: str,
) -> str:
    return f"""
        <section>
          <h2>Protocol Launcher</h2>
          <form method="post" action="/dashboard/protocol/run">
            <label>Brain ID <input type="text" name="brain_id" value="{brain_id}" /></label>
            <label>Protocol
              <select name="name">
                {protocol_options}
              </select>
            </label>
            <label>Query text <input type="text" name="query_text" value="critical memory and next actions" /></label>
            <label>Objective <input type="text" name="objective" value="Summarize the most relevant memory and next actions." /></label>
            <label>Session ID <input type="text" name="session_id" value="default-session" /></label>
            <label>Allowed buckets <input type="text" name="allowed_buckets" value="{allowed_bucket_values}" /></label>
            {sensitivity_filter_input}
            <input type="hidden" name="bucket_filter" value="{escape(str(active_bucket))}" />
            <button type="submit">Run Protocol</button>
          </form>
          {protocol_feedback}
        </section>
    """


def _render_session_resume_section(
    brain_id: str,
    allowed_bucket_values: str,
    sensitivity_filter_input: str,
    active_bucket: object,
    session_feedback: str,
) -> str:
    return f"""
        <section>
          <h2>Session Resume</h2>
          <form method="post" action="/dashboard/session/resume">
            <label>Brain ID <input type="text" name="brain_id" value="{brain_id}" /></label>
            <label>Namespace <input type="text" name="namespace" value="{brain_id}" /></label>
            <label>Session ID <input type="text" name="session_id" value="default-session" /></label>
            <label>Source client <input type="text" name="source_client" value="dashboard" /></label>
            <label>Query text <input type="text" name="query_text" value="session checkpoint summary" /></label>
            <label>Allowed buckets <input type="text" name="allowed_buckets" value="{allowed_bucket_values}" /></label>
            {sensitivity_filter_input}
            <input type="hidden" name="bucket_filter" value="{escape(str(active_bucket))}" />
            <button type="submit">Resume Session</button>
          </form>
          {session_feedback}
        </section>
    """


def _render_filter_section(bucket_options: str) -> str:
    return f"""
        <section>
          <h2>Filter Recent Activity</h2>
          <form method="get" action="/dashboard">
            <label>Bucket
              <select name="bucket">
                <option value="">all</option>
                {bucket_options}
              </select>
            </label>
            <button type="submit">Apply Filter</button>
          </form>
        </section>
    """


def _render_admin_section(brain_id: str, active_bucket: object) -> str:
    return f"""
        <section>
          <h2>Admin Actions</h2>
          <form method="post" action="/dashboard/admin/update">
            <label>ID <input type="text" name="id" /></label>
            <label>Mode
              <select name="mode">
                <option value="replace_content">supersede content</option>
                <option value="in_place">in place</option>
              </select>
            </label>
            <label>Title <input type="text" name="title" /></label>
            <label>Content <textarea name="content"></textarea></label>
            <input type="hidden" name="brain_id" value="{brain_id}" />
            <input type="hidden" name="bucket_filter" value="{escape(str(active_bucket))}" />
            <button type="submit">Supersede / Update</button>
          </form>
          <form method="post" action="/dashboard/admin/reindex">
            <label>IDs <input type="text" name="ids" /></label>
            <label>Scope
              <select name="scope">
                <option value="records">records</option>
                <option value="documents">documents</option>
              </select>
            </label>
            <input type="hidden" name="bucket_filter" value="{escape(str(active_bucket))}" />
            <button type="submit">Reindex</button>
          </form>
          <form method="post" action="/dashboard/admin/audit">
            <input type="hidden" name="bucket_filter" value="{escape(str(active_bucket))}" />
            <button type="submit">Audit Memory</button>
          </form>
          <form method="post" action="/dashboard/admin/delete">
            <label>IDs <input type="text" name="ids" /></label>
            <label>Reason <input type="text" name="reason" value="dashboard cleanup" /></label>
            <label>Mode
              <select name="mode">
                <option value="soft">soft</option>
                <option value="hard">hard</option>
              </select>
            </label>
            <input type="hidden" name="bucket_filter" value="{escape(str(active_bucket))}" />
            <button type="submit">Delete</button>
          </form>
        </section>
    """


def _render_result_block(title: str, payload: dict[str, object] | None) -> str:
    if payload is None:
        return ""
    if title == "Briefing Result" and "briefing" in payload:
        return f"<div><h3>{title}</h3><pre>{escape(str(payload['briefing']))}</pre></div>"
    if title == "Report Result" and "report" in payload:
        mode = escape(str(payload.get("mode", "report")))
        return (
            f"<div><h3>{title}</h3><p><strong>Mode:</strong> {mode}</p>"
            f"<pre>{escape(str(payload['report']))}</pre></div>"
        )
    if title == "Search Result":
        results = payload.get("results", [])
        if results:
            items = "".join(
                (
                    f"<li>{escape(str(result.get('id', 'unknown')))}: "
                    f"{escape(str(result.get('content', result.get('title', ''))))}</li>"
                )
                for result in results
            )
            return f"<div><h3>{title}</h3><ul>{items}</ul></div>"
    items = "".join(
        f"<li>{escape(str(key))}: {escape(str(value))}</li>"
        for key, value in payload.items()
    )
    return f"<div><h3>{title}</h3><ul>{items}</ul></div>"


def _render_document_list(documents: list[dict[str, object]]) -> str:
    if not documents:
        return "<li>No documents yet.</li>"
    return "".join(
        (
            f"<li><strong>{escape(str(item.get('title') or 'Untitled document'))}</strong> "
            f"({escape(str(item['namespace']))}/{escape(str(item['bucket']))})</li>"
        )
        for item in documents
    )


def _render_record_list(records: list[dict[str, object]]) -> str:
    if not records:
        return "<li>No records yet.</li>"
    return "".join(
        (
            f"<li><strong>{escape(str(item.get('title') or item['id']))}</strong> "
            f"({escape(str(item['namespace']))}/{escape(str(item['bucket']))}) - "
            f"{escape(str(item.get('content', ''))[:80])}</li>"
        )
        for item in records
    )


def _render_brain_list(brains: list[dict[str, object]], active_brain_id: str) -> str:
    if not brains:
        return "<li>No brains yet.</li>"
    return "".join(
        (
            f"<li><strong>{escape(str(item.get('brain_id', 'unknown')))}</strong> "
            f"({escape(str(item.get('status', 'active')))}) -> "
            f"{escape(str(item.get('namespace', 'unknown')))}"
            f"{' [active]' if str(item.get('brain_id')) == active_brain_id else ''}</li>"
        )
        for item in brains
    )


def _render_connector_list(connectors: list[dict[str, object]]) -> str:
    if not connectors:
        return "<li>No connector metadata found.</li>"
    return "".join(
        (
            f"<li><strong>{escape(str(item.get('name', item.get('slug', 'unknown'))))}</strong> "
            f"{'runnable' if item.get('runnable') else 'metadata-only'}"
            f" - {escape(str(item.get('description') or ''))}"
            f" - capabilities: {escape(', '.join(str(cap) for cap in item.get('capabilities', [])))}</li>"
        )
        for item in connectors
    )


def _render_protocol_option(protocol: dict[str, object]) -> str:
    name = escape(str(protocol.get("name") or "unknown"))
    purpose = escape(str(protocol.get("purpose") or ""))
    return f'<option value="{name}">{name} - {purpose}</option>'


def _render_bucket_option(bucket: object, active_bucket: object) -> str:
    selected = " selected" if str(bucket) == str(active_bucket) else ""
    escaped_bucket = escape(str(bucket))
    return f'<option value="{escaped_bucket}"{selected}>{escaped_bucket}</option>'


def _render_audit_list(events: list[dict[str, object]]) -> str:
    if not events:
        return "<li>No audit activity yet.</li>"
    return "".join(
        (
            f"<li>{escape(str(event.get('operation', 'unknown')))} · "
            f"{escape(str(event.get('outcome', 'unknown')))} · "
            f"{escape(str(event.get('actor', 'system')))}</li>"
        )
        for event in events
    )


def _first_value(values: dict[str, list[str]], key: str) -> str | None:
    matches = values.get(key)
    if not matches:
        return None
    value = matches[0].strip()
    return value or None


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _resolve_dashboard_brain_id(
    payload: dict[str, object], config: NeuroCoreConfig
) -> str:
    return str(
        payload.get("brain_id")
        or payload.get("namespace")
        or config.default_namespace
    )


def _dashboard_report_result(
    payload: dict[str, object],
    *,
    store: BaseStore,
    config: NeuroCoreConfig,
    semantic_ranker: object | None,
) -> dict[str, object]:
    try:
        return generate_consensus_report(
            payload,
            store=store,
            config=config,
            semantic_ranker=semantic_ranker,
        )
    except PermissionError:
        briefing = generate_briefing(
            {
                "brain_id": payload.get("brain_id"),
                "query_request": payload.get("query_request"),
                "include_operator_hints": True,
                "max_items": payload.get("max_items", 5),
            },
            store=store,
            config=config,
            semantic_ranker=semantic_ranker,
        )
        return {
            "mode": "fallback-briefing",
            "report": briefing["briefing"],
            "metadata": briefing.get("metadata", {}),
        }
