"""MCP server adapter for NeuroCore tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from neurocore.core.config import NeuroCoreConfig, load_config
from neurocore.interfaces.admin import (
    audit_memory,
    delete_memory,
    reindex_memory,
    update_memory,
)
from neurocore.interfaces.briefing import generate_briefing
from neurocore.interfaces.capture import capture_memory
from neurocore.interfaces.dashboard import build_dashboard_data
from neurocore.interfaces.ingest import ingest_discord_event, ingest_slack_event
from neurocore.interfaces.query import query_memory
from neurocore.interfaces.reporting import generate_consensus_report
from neurocore.interfaces.summaries import run_background_summaries
from neurocore.runtime import build_semantic_ranker, build_store
from neurocore.storage.base import BaseStore


def create_mcp_server(
    *,
    store: BaseStore | None = None,
    config: NeuroCoreConfig | None = None,
) -> FastMCP:
    """Create the MCP server and register enabled NeuroCore tools."""
    config = config or load_config()
    store = store or build_store(config)
    semantic_ranker = build_semantic_ranker(config)
    server = FastMCP("NeuroCore")

    server.add_tool(
        lambda request: capture_memory(request, store=store, config=config),
        name="capture_memory",
        description="Capture a record or document into NeuroCore.",
    )
    server.add_tool(
        lambda request: query_memory(
            request,
            store=store,
            config=config,
            semantic_ranker=semantic_ranker,
        ),
        name="query_memory",
        description="Query NeuroCore records or chunks.",
    )
    server.add_tool(
        lambda request: generate_briefing(
            request,
            store=store,
            config=config,
            semantic_ranker=semantic_ranker,
        ),
        name="generate_briefing",
        description="Generate a compact markdown briefing from NeuroCore memory.",
    )
    server.add_tool(
        lambda request: ingest_slack_event(request, store=store, config=config),
        name="ingest_slack_event",
        description="Ingest a Slack event into NeuroCore.",
    )
    server.add_tool(
        lambda request: ingest_discord_event(request, store=store, config=config),
        name="ingest_discord_event",
        description="Ingest a Discord event into NeuroCore.",
    )
    if config.enable_background_summarization:
        server.add_tool(
            lambda request: run_background_summaries(
                request, store=store, config=config
            ),
            name="run_background_summaries",
            description="Run background document summarization.",
        )
    server.add_tool(
        lambda request: generate_consensus_report(
            request,
            store=store,
            config=config,
            semantic_ranker=semantic_ranker,
        ),
        name="generate_consensus_report",
        description="Generate a report from NeuroCore context, falling back to a synthesized briefing when needed.",
    )
    if config.enable_dashboard:
        server.add_tool(
            lambda request: build_dashboard_data(store=store, config=config),
            name="dashboard_data",
            description="Return dashboard data for NeuroCore.",
        )
    if config.enable_admin_surface:
        server.add_tool(
            lambda request: update_memory(request, store=store, config=config),
            name="update_memory",
            description="Update a NeuroCore record or document.",
        )
        server.add_tool(
            lambda request: delete_memory(request, store=store, config=config),
            name="delete_memory",
            description="Delete a NeuroCore record or document.",
        )
        server.add_tool(
            lambda request: reindex_memory(request, store=store, config=config),
            name="reindex_memory",
            description="Reindex NeuroCore retrieval artifacts.",
        )
        server.add_tool(
            lambda request: audit_memory(request, store=store, config=config),
            name="audit_memory",
            description="Audit NeuroCore memory for secret-like values.",
        )

    return server
