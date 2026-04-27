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
from neurocore.interfaces.capture import capture_memory
from neurocore.interfaces.dashboard import build_dashboard_data
from neurocore.interfaces.ingest import ingest_discord_event, ingest_slack_event
from neurocore.interfaces.query import query_memory
from neurocore.interfaces.reporting import generate_consensus_report
from neurocore.interfaces.summaries import run_background_summaries
from neurocore.runtime import build_semantic_ranker, build_store
from neurocore.storage.base import BaseStore

ResponseT = TypeVar("ResponseT")


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

    @app.post("/capture")
    def capture_endpoint(request: dict[str, object]) -> dict[str, object]:
        return capture_memory(request, store=store, config=config)

    @app.post("/query")
    def query_endpoint(request: dict[str, object]) -> dict[str, object]:
        return query_memory(
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

    @app.get("/dashboard/data")
    def dashboard_data_endpoint(bucket: str | None = None) -> dict[str, object]:
        return _guard_dashboard(
            lambda: build_dashboard_data(
                store=store, config=config, bucket_filter=bucket
            ),
            enabled=config.enable_dashboard,
        )

    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard_endpoint(bucket: str | None = None) -> str:
        data = _guard_dashboard(
            lambda: build_dashboard_data(
                store=store, config=config, bucket_filter=bucket
            ),
            enabled=config.enable_dashboard,
        )
        return _render_reference_app(
            data=data,
            config=config,
            capture_result=None,
            query_result=None,
            admin_result=None,
        )

    @app.post("/dashboard/capture", response_class=HTMLResponse)
    async def dashboard_capture_endpoint(request: Request) -> str:
        payload = await _parse_form_payload(request)
        capture_result = _guard_dashboard(
            lambda: capture_memory(payload, store=store, config=config),
            enabled=config.enable_dashboard,
        )
        data = _guard_dashboard(
            lambda: build_dashboard_data(
                store=store,
                config=config,
                bucket_filter=_optional_str(payload.get("bucket_filter")),
            ),
            enabled=config.enable_dashboard,
        )
        return _render_reference_app(
            data=data,
            config=config,
            capture_result=capture_result,
            query_result=None,
            admin_result=None,
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
        data = _guard_dashboard(
            lambda: build_dashboard_data(
                store=store,
                config=config,
                bucket_filter=_optional_str(payload.get("bucket_filter")),
            ),
            enabled=config.enable_dashboard,
        )
        return _render_reference_app(
            data=data,
            config=config,
            capture_result=None,
            query_result=query_result,
            admin_result=None,
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
        data = _guard_dashboard(
            lambda: build_dashboard_data(
                store=store,
                config=config,
                bucket_filter=_optional_str(payload.get("bucket_filter")),
            ),
            enabled=config.enable_dashboard,
        )
        return _render_reference_app(
            data=data,
            config=config,
            capture_result=None,
            query_result=None,
            admin_result=admin_result,
        )

    return app


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


async def _parse_form_payload(request: Request) -> dict[str, object]:
    raw = (await request.body()).decode("utf-8")
    form_values = parse_qs(raw, keep_blank_values=False)
    bucket_filter = _first_value(form_values, "bucket_filter")
    payload: dict[str, object] = {}

    if request.url.path.endswith("/capture"):
        payload = {
            "namespace": _first_value(form_values, "namespace") or None,
            "bucket": _first_value(form_values, "bucket"),
            "sensitivity": _first_value(form_values, "sensitivity"),
            "content": _first_value(form_values, "content"),
            "content_format": _first_value(form_values, "content_format") or "markdown",
            "source_type": _first_value(form_values, "source_type") or "note",
            "title": _first_value(form_values, "title") or None,
        }
    elif request.url.path.endswith("/query"):
        allowed_buckets = _first_value(form_values, "allowed_buckets") or ",".join(
            request.app.state.config.allowed_buckets
        )
        payload = {
            "query_text": _first_value(form_values, "query_text"),
            "namespace": _first_value(form_values, "namespace")
            or request.app.state.config.default_namespace,
            "allowed_buckets": [
                value.strip() for value in allowed_buckets.split(",") if value.strip()
            ],
            "sensitivity_ceiling": _first_value(form_values, "sensitivity_ceiling")
            or request.app.state.config.default_sensitivity,
        }
    else:
        ids = _first_value(form_values, "ids") or ""
        payload = {
            "ids": [value.strip() for value in ids.split(",") if value.strip()],
            "scope": _first_value(form_values, "scope") or "records",
        }

    if bucket_filter:
        payload["bucket_filter"] = bucket_filter
    return {key: value for key, value in payload.items() if value is not None}


def _render_reference_app(
    *,
    data: dict[str, object],
    config: NeuroCoreConfig,
    capture_result: dict[str, object] | None,
    query_result: dict[str, object] | None,
    admin_result: dict[str, object] | None,
) -> str:
    stats = data["stats"]
    production = data["production_backend"]
    available_buckets = data.get("available_buckets", [])
    active_bucket = data.get("active_bucket_filter") or ""
    capture_feedback = _render_result_block("Capture Result", capture_result)
    query_feedback = _render_result_block("Query Result", query_result)
    admin_feedback = _render_result_block("Admin Result", admin_result)
    recent_documents = _render_document_list(data["recent_documents"])
    recent_records = _render_record_list(data.get("recent_records", []))
    stats_line = (
        f"Records: {stats['record_count']} | Documents: {stats['document_count']} | "
        f"Summarized: {stats['summarized_document_count']}"
    )
    production_line = (
        f"Production backend: {production['provider']} ({production['status']})"
    )
    capture_bucket = escape(str(active_bucket or "research"))
    default_sensitivity = escape(config.default_sensitivity)
    allowed_bucket_values = escape(",".join(available_buckets) or str(active_bucket))
    sensitivity_filter_input = (
        '<label>Sensitivity ceiling <input type="text" '
        f'name="sensitivity_ceiling" value="{default_sensitivity}" /></label>'
    )
    bucket_options = "".join(
        _render_bucket_option(bucket, active_bucket) for bucket in available_buckets
    )
    admin_section = ""
    if config.enable_admin_surface:
        admin_section = f"""
        <section>
          <h2>Admin Actions</h2>
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
        </section>
        """

    return f"""
    <html>
      <head><title>NeuroCore Reference App</title></head>
      <body>
        <h1>NeuroCore Reference App</h1>
        <p>{stats_line}</p>
        <p>{production_line}</p>
        <section>
          <h2>Capture Memory</h2>
          <form method="post" action="/dashboard/capture">
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
        <section>
          <h2>Query Memory</h2>
          <form method="post" action="/dashboard/query">
            <label>Query text <input type="text" name="query_text" /></label>
            <label>Allowed buckets <input type="text" name="allowed_buckets" value="{allowed_bucket_values}" /></label>
            {sensitivity_filter_input}
            <input type="hidden" name="bucket_filter" value="{escape(str(active_bucket))}" />
            <button type="submit">Search</button>
          </form>
          {query_feedback}
        </section>
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
        <section>
          <h2>Recent Records</h2>
          <ul>{recent_records}</ul>
        </section>
        <section>
          <h2>Recent Documents</h2>
          <ul>{recent_documents}</ul>
        </section>
        {admin_section}
        {admin_feedback}
      </body>
    </html>
    """


def _render_result_block(title: str, payload: dict[str, object] | None) -> str:
    if payload is None:
        return ""
    if title == "Query Result":
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


def _render_bucket_option(bucket: object, active_bucket: object) -> str:
    selected = " selected" if str(bucket) == str(active_bucket) else ""
    escaped_bucket = escape(str(bucket))
    return f'<option value="{escaped_bucket}"{selected}>{escaped_bucket}</option>'


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
