"""Runnable Slack connector package for NeuroCore."""

from __future__ import annotations

import argparse
import json
import sys
from io import StringIO
from pathlib import Path
from typing import TextIO

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from neurocore.core.config import NeuroCoreConfig, load_config
from neurocore.interfaces.brains import create_brain, list_brains
from neurocore.interfaces.connectors import OPENBRAIN_CONNECTOR_VERBS
from neurocore.interfaces.ingest import ingest_slack_event
from neurocore.interfaces.protocols import run_protocol
from neurocore.interfaces.query import query_memory
from neurocore.interfaces.reporting import build_reporting_status, generate_consensus_report
from neurocore.interfaces.sessions import capture_session_event, resume_session
from neurocore.runtime import build_semantic_ranker, build_store
from neurocore.storage.base import BaseStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python integrations/slack-connector/connector.py")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("health")
    subparsers.add_parser("describe-capabilities")
    subparsers.add_parser("setup-instructions")
    for name in (
        "ingest",
        "query",
        "report",
        "protocol",
        "select-brain",
        "create-brain",
        "list-brains",
        "session-capture",
        "session-resume",
    ):
        child = subparsers.add_parser(name)
        child.add_argument("--request-json", required=name != "list-brains")
    return parser


def main(
    argv: list[str] | None = None,
    *,
    store: BaseStore | None = None,
    config: NeuroCoreConfig | None = None,
    stdout: TextIO | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    config = config or load_config()
    store = store or build_store(config)
    semantic_ranker = build_semantic_ranker(config)
    if args.command in {"health", "describe-capabilities", "setup-instructions"}:
        response = {
            "connector": "slack",
            "runnable": True,
            "configured": True,
            "healthy": True,
            "supported_verbs": list((*OPENBRAIN_CONNECTOR_VERBS, "ingest_event")),
            "capabilities": [
                "ingest",
                "query",
                "report",
                "protocol",
                "brain-management",
                "session-memory",
            ],
            "reporting_status": build_reporting_status(config),
            "setup_instructions": (
                "Run health, create or select a brain, ingest a Slack event payload, "
                "then query, report, or run a protocol."
            ),
        }
    else:
        request = _parse_request(args.request_json or "{}")
        if args.command == "ingest":
            response = ingest_slack_event(request, store=store, config=config)
        elif args.command == "query":
            response = query_memory(
                request,
                store=store,
                config=config,
                semantic_ranker=semantic_ranker,
            )
        elif args.command == "report":
            response = generate_consensus_report(
                request,
                store=store,
                config=config,
                semantic_ranker=semantic_ranker,
            )
        elif args.command == "create-brain":
            response = create_brain(
                request,
                store=store,
                default_allowed_buckets=config.allowed_buckets,
            )
        elif args.command == "select-brain":
            response = create_brain(
                request,
                store=store,
                default_allowed_buckets=config.allowed_buckets,
            )
        elif args.command == "list-brains":
            response = list_brains(request, store=store)
        elif args.command == "session-capture":
            response = capture_session_event(request, store=store, config=config)
        elif args.command == "session-resume":
            response = resume_session(request, store=store, config=config)
        else:
            response = run_protocol(
                request,
                store=store,
                config=config,
                semantic_ranker=semantic_ranker,
            )

    output = stdout or sys.stdout
    output.write(json.dumps(response))
    output.write("\n")
    return 0


def run_for_test(argv: list[str], *, store: BaseStore, config: NeuroCoreConfig) -> dict[str, object]:
    buffer = StringIO()
    main(argv, store=store, config=config, stdout=buffer)
    return json.loads(buffer.getvalue())


def _parse_request(raw: str) -> dict[str, object]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("request-json must decode to an object")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
