import pytest

from neurocore.adapters.mcp_server import create_mcp_server
from neurocore.core.config import NeuroCoreConfig
from neurocore.storage.in_memory import InMemoryStore


@pytest.mark.asyncio
async def test_mcp_server_exposes_capture_and_query_tools_only_when_admin_disabled():
    server = create_mcp_server(
        store=InMemoryStore(),
        config=NeuroCoreConfig(
            default_namespace="project-alpha",
            allowed_buckets=("research",),
            default_sensitivity="standard",
            enable_admin_surface=False,
        ),
    )

    tool_names = {tool.name for tool in await server.list_tools()}

    assert tool_names == {
        "capture_memory",
        "generate_briefing",
        "generate_consensus_report",
        "list_protocols",
        "query_memory",
        "run_protocol",
        "ingest_slack_event",
        "ingest_discord_event",
    }


@pytest.mark.asyncio
async def test_mcp_server_registers_admin_tools_when_enabled():
    server = create_mcp_server(
        store=InMemoryStore(),
        config=NeuroCoreConfig(
            default_namespace="project-alpha",
            allowed_buckets=("research",),
            default_sensitivity="standard",
            enable_admin_surface=True,
            enable_dashboard=True,
            enable_background_summarization=True,
            enable_multi_model_consensus=True,
        ),
    )

    tool_names = {tool.name for tool in await server.list_tools()}

    assert {
        "capture_memory",
        "generate_briefing",
        "query_memory",
        "list_protocols",
        "run_protocol",
        "ingest_slack_event",
        "ingest_discord_event",
        "run_background_summaries",
        "generate_consensus_report",
        "dashboard_data",
        "update_memory",
        "delete_memory",
        "reindex_memory",
        "audit_memory",
    }.issubset(tool_names)


@pytest.mark.asyncio
async def test_mcp_server_keeps_optional_summary_and_dashboard_tools_gated():
    server = create_mcp_server(
        store=InMemoryStore(),
        config=NeuroCoreConfig(
            default_namespace="project-alpha",
            allowed_buckets=("research",),
            default_sensitivity="standard",
            enable_admin_surface=True,
            enable_dashboard=False,
            enable_background_summarization=False,
        ),
    )

    tool_names = {tool.name for tool in await server.list_tools()}

    assert "capture_memory" in tool_names
    assert "generate_briefing" in tool_names
    assert "generate_consensus_report" in tool_names
    assert "query_memory" in tool_names
    assert "run_protocol" in tool_names
    assert "update_memory" in tool_names
    assert "run_background_summaries" not in tool_names
    assert "dashboard_data" not in tool_names
