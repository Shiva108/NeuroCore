import importlib.util
import json
from pathlib import Path

from neurocore.core.config import NeuroCoreConfig
from neurocore.interfaces.capture import capture_memory
from neurocore.storage.in_memory import InMemoryStore


def _load_connector(relative_path: str):
    module_path = Path(__file__).resolve().parents[2] / relative_path
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _config() -> NeuroCoreConfig:
    return NeuroCoreConfig(
        default_namespace="project-alpha",
        allowed_buckets=("findings", "reports", "ops", "recon", "agents"),
        default_sensitivity="restricted",
        enable_multi_model_consensus=False,
    )


def test_slack_connector_ingests_and_queries_end_to_end():
    connector = _load_connector("integrations/slack-connector/connector.py")
    store = InMemoryStore()
    config = _config()

    ingest_payload = connector.run_for_test(
        [
            "ingest",
            "--request-json",
            json.dumps(
                {
                    "type": "event_callback",
                    "team_id": "T123",
                    "event": {
                        "type": "message",
                        "channel": "C123",
                        "user": "U123",
                        "text": "critical ciso concern with ATT&CK note",
                        "ts": "1713897900.000100",
                    },
                    "bucket": "reports",
                }
            ),
        ],
        store=store,
        config=config,
    )
    query_payload = connector.run_for_test(
        [
            "query",
            "--request-json",
            json.dumps(
                {
                    "namespace": "slack-t123",
                    "query_text": "ATT&CK note",
                    "allowed_buckets": ["reports"],
                    "sensitivity_ceiling": "restricted",
                }
            ),
        ],
        store=store,
        config=config,
    )

    assert ingest_payload["ignored"] is False
    assert query_payload["results"]
    assert query_payload["results"][0]["namespace"] == "slack-t123"


def test_discord_connector_ingests_and_runs_protocol():
    connector = _load_connector("integrations/discord-connector/connector.py")
    store = InMemoryStore()
    config = _config()

    connector.run_for_test(
        [
            "ingest",
            "--request-json",
            json.dumps(
                {
                    "t": "MESSAGE_CREATE",
                    "d": {
                        "id": "msg-1",
                        "guild_id": "G123",
                        "channel_id": "C123",
                        "timestamp": "2026-04-29T10:00:00Z",
                        "content": "critical ciso concern with CVE-2026-0001",
                        "author": {"id": "U1", "username": "analyst"},
                    },
                    "bucket": "findings",
                }
            ),
        ],
        store=store,
        config=config,
    )
    protocol_payload = connector.run_for_test(
        [
            "protocol",
            "--request-json",
            json.dumps(
                {
                    "name": "cti-review-v1",
                    "namespace": "discord-g123",
                    "query_text": "CVE-2026-0001",
                    "allowed_buckets": ["findings"],
                }
            ),
        ],
        store=store,
        config=config,
    )

    assert protocol_payload["protocol"]["name"] == "cti-review-v1"
    assert "## Overview" in protocol_payload["report"]
    assert "## Findings" in protocol_payload["report"]


def test_claude_desktop_connector_lists_tools_and_runs_protocol():
    connector = _load_connector("integrations/claude-desktop-mcp/connector.py")
    store = InMemoryStore()
    config = _config()
    capture_memory(
        {
            "namespace": "project-alpha",
            "bucket": "reports",
            "sensitivity": "restricted",
            "content": "critical operator concern with ATT&CK T1190",
            "content_format": "markdown",
            "source_type": "note",
            "tags": ["ciso-concern", "severity:critical"],
            "title": "Critical external exposure",
        },
        store=store,
        config=config,
    )

    tools_payload = connector.run_for_test(
        ["describe-tools"],
        store=store,
        config=config,
    )
    protocol_payload = connector.run_for_test(
        [
            "protocol",
            "--request-json",
            json.dumps(
                {
                    "name": "cti-review-v1",
                    "namespace": "project-alpha",
                    "query_text": "ATT&CK T1190",
                    "allowed_buckets": ["reports"],
                }
            ),
        ],
        store=store,
        config=config,
    )

    assert "run_protocol" in tools_payload["tools"]
    assert "generate_briefing" in tools_payload["tools"]
    assert protocol_payload["protocol"]["prioritization_strategy"] == "severity+intel-tags+operator-concern"
    assert "## Actions" in protocol_payload["report"]
