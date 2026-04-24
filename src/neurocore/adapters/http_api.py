"""FastAPI adapter for exposing NeuroCore over HTTP."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from neurocore.core.config import NeuroCoreConfig, load_config
from neurocore.interfaces.admin import delete_memory, reindex_memory, update_memory
from neurocore.interfaces.capture import capture_memory
from neurocore.interfaces.dashboard import build_dashboard_data
from neurocore.interfaces.ingest import ingest_discord_event, ingest_slack_event
from neurocore.interfaces.query import query_memory
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

    @app.post("/admin/update")
    def update_endpoint(request: dict[str, object]) -> dict[str, object]:
        return _guard_admin(lambda: update_memory(request, store=store, config=config))

    @app.post("/admin/delete")
    def delete_endpoint(request: dict[str, object]) -> dict[str, object]:
        return _guard_admin(lambda: delete_memory(request, store=store, config=config))

    @app.post("/admin/reindex")
    def reindex_endpoint(request: dict[str, object]) -> dict[str, object]:
        return _guard_admin(lambda: reindex_memory(request, store=store, config=config))

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
    def dashboard_data_endpoint() -> dict[str, object]:
        return _guard_dashboard(
            lambda: build_dashboard_data(store=store, config=config),
            enabled=config.enable_dashboard,
        )

    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard_endpoint() -> str:
        data = _guard_dashboard(
            lambda: build_dashboard_data(store=store, config=config),
            enabled=config.enable_dashboard,
        )
        recent = (
            "".join(
                f"<li><strong>{item['title']}</strong> ({item['namespace']}/{item['bucket']})</li>"
                for item in data["recent_documents"]
            )
            or "<li>No documents yet.</li>"
        )
        stats = data["stats"]
        production = data["production_backend"]
        summary_line = (
            f"Records: {stats['record_count']} | Documents: {stats['document_count']} | "
            f"Summarized: {stats['summarized_document_count']}"
        )
        return f"""
        <html>
          <head><title>NeuroCore Dashboard</title></head>
          <body>
            <h1>NeuroCore Dashboard</h1>
            <p>{summary_line}</p>
            <p>Production backend: {production['provider']} ({production['status']})</p>
            <h2>Recent Documents</h2>
            <ul>{recent}</ul>
          </body>
        </html>
        """

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


def _guard_feature(
    fn: Callable[[], ResponseT], *, enabled: bool, message: str
) -> ResponseT:
    """Run a handler only when the corresponding feature flag is enabled."""
    if not enabled:
        raise PermissionError(message)
    return fn()
