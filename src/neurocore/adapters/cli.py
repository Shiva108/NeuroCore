"""Command-line interface adapter for NeuroCore."""

from __future__ import annotations

import argparse
import json
import sys
from typing import TextIO

from neurocore.core.config import NeuroCoreConfig, load_config
from neurocore.interfaces.admin import delete_memory, reindex_memory, update_memory
from neurocore.interfaces.capture import capture_memory
from neurocore.interfaces.ingest import ingest_discord_event, ingest_slack_event
from neurocore.interfaces.query import query_memory
from neurocore.interfaces.summaries import run_background_summaries
from neurocore.runtime import build_semantic_ranker, build_store
from neurocore.storage.base import BaseStore


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser."""
    parser = argparse.ArgumentParser(prog="neurocore")
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture_parser = subparsers.add_parser("capture")
    capture_parser.add_argument("--request-json", required=True)

    query_parser = subparsers.add_parser("query")
    query_parser.add_argument("--request-json", required=True)

    ingest_parser = subparsers.add_parser("ingest")
    ingest_subparsers = ingest_parser.add_subparsers(
        dest="ingest_command", required=True
    )
    for name in ("slack", "discord"):
        command_parser = ingest_subparsers.add_parser(name)
        command_parser.add_argument("--request-json", required=True)

    summaries_parser = subparsers.add_parser("summaries")
    summaries_subparsers = summaries_parser.add_subparsers(
        dest="summaries_command", required=True
    )
    run_parser = summaries_subparsers.add_parser("run")
    run_parser.add_argument("--request-json", required=True)

    admin_parser = subparsers.add_parser("admin")
    admin_subparsers = admin_parser.add_subparsers(dest="admin_command", required=True)
    for name in ("update", "delete", "reindex"):
        command_parser = admin_subparsers.add_parser(name)
        command_parser.add_argument("--request-json", required=True)

    return parser


def main(
    argv: list[str] | None = None,
    *,
    store: BaseStore | None = None,
    config: NeuroCoreConfig | None = None,
    stdout: TextIO | None = None,
) -> int:
    """Run the NeuroCore CLI and write a JSON response to stdout."""
    parser = build_parser()
    args = parser.parse_args(argv)
    config = config or load_config()
    store = store or build_store(config)
    stdout = stdout or sys.stdout

    if args.command == "capture":
        response = capture_memory(
            _parse_request(args.request_json), store=store, config=config
        )
    elif args.command == "query":
        response = query_memory(
            _parse_request(args.request_json),
            store=store,
            config=config,
            semantic_ranker=build_semantic_ranker(config),
        )
    elif args.command == "ingest":
        request = _parse_request(args.request_json)
        if args.ingest_command == "slack":
            response = ingest_slack_event(request, store=store, config=config)
        else:
            response = ingest_discord_event(request, store=store, config=config)
    elif args.command == "summaries":
        response = run_background_summaries(
            _parse_request(args.request_json),
            store=store,
            config=config,
        )
    else:
        if not config.enable_admin_surface:
            raise PermissionError("Admin surface is disabled")
        request = _parse_request(args.request_json)
        if args.admin_command == "update":
            response = update_memory(request, store=store, config=config)
        elif args.admin_command == "delete":
            response = delete_memory(request, store=store, config=config)
        else:
            response = reindex_memory(request, store=store, config=config)

    stdout.write(json.dumps(response))
    stdout.write("\n")
    return 0


def _parse_request(raw: str) -> dict[str, object]:
    """Parse a JSON object supplied to a CLI command."""
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("request-json must decode to an object")
    return value
