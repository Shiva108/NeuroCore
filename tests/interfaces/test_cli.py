import io
import json

import pytest

from neurocore.adapters.cli import main
from neurocore.core.config import NeuroCoreConfig
from neurocore.storage.in_memory import InMemoryStore


def build_config() -> NeuroCoreConfig:
    return NeuroCoreConfig(
        default_namespace="project-alpha",
        allowed_buckets=("research",),
        default_sensitivity="standard",
        max_atomic_tokens=6,
        enable_admin_surface=False,
        enable_background_summarization=True,
    )


def test_cli_capture_and_query_commands_use_library_contracts():
    store = InMemoryStore()
    config = build_config()
    stdout = io.StringIO()

    exit_code = main(
        [
            "capture",
            "--request-json",
            json.dumps(
                {
                    "namespace": "project-alpha",
                    "bucket": "research",
                    "sensitivity": "standard",
                    "content": "cli note",
                    "content_format": "markdown",
                    "source_type": "note",
                }
            ),
        ],
        store=store,
        config=config,
        stdout=stdout,
    )

    assert exit_code == 0
    capture_response = json.loads(stdout.getvalue())
    assert capture_response["kind"] == "record"

    stdout = io.StringIO()
    exit_code = main(
        [
            "query",
            "--request-json",
            json.dumps(
                {
                    "query_text": "cli",
                    "namespace": "project-alpha",
                    "allowed_buckets": ["research"],
                    "sensitivity_ceiling": "standard",
                }
            ),
        ],
        store=store,
        config=config,
        stdout=stdout,
    )

    assert exit_code == 0
    query_response = json.loads(stdout.getvalue())
    assert len(query_response["results"]) == 1


def test_cli_admin_commands_respect_admin_toggle():
    store = InMemoryStore()
    config = build_config()

    with pytest.raises(PermissionError, match="disabled"):
        main(
            [
                "admin",
                "reindex",
                "--request-json",
                json.dumps({"ids": ["rec-1"], "scope": "records"}),
            ],
            store=store,
            config=config,
            stdout=io.StringIO(),
        )


def test_cli_ingest_and_summarize_commands_use_library_contracts():
    store = InMemoryStore()
    config = build_config()
    stdout = io.StringIO()

    exit_code = main(
        [
            "ingest",
            "slack",
            "--request-json",
            json.dumps(
                {
                    "type": "event_callback",
                    "team_id": "T123",
                    "event": {
                        "type": "message",
                        "channel": "C123",
                        "user": "U123",
                        "text": (
                            "Sentence one explains the system. "
                            "Sentence two adds retrieval detail. "
                            "Sentence three covers isolation policy."
                        ),
                        "ts": "1713897900.000100",
                    },
                    "bucket": "research",
                }
            ),
        ],
        store=store,
        config=config,
        stdout=stdout,
    )

    assert exit_code == 0
    ingest_response = json.loads(stdout.getvalue())
    assert ingest_response["source"] == "slack"

    stdout = io.StringIO()
    exit_code = main(
        ["summaries", "run", "--request-json", json.dumps({"limit": 10})],
        store=store,
        config=config,
        stdout=stdout,
    )

    assert exit_code == 0
    summary_response = json.loads(stdout.getvalue())
    assert summary_response["processed"] >= 1
