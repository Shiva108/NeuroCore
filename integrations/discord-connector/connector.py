"""Runnable Discord connector package for NeuroCore."""

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
from neurocore.interfaces.ingest import ingest_discord_event
from neurocore.interfaces.protocols import run_protocol
from neurocore.interfaces.query import query_memory
from neurocore.interfaces.reporting import generate_consensus_report
from neurocore.runtime import build_semantic_ranker, build_store
from neurocore.storage.base import BaseStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python integrations/discord-connector/connector.py")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("ingest", "query", "report", "protocol"):
        child = subparsers.add_parser(name)
        child.add_argument("--request-json", required=True)
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
    request = _parse_request(args.request_json)

    if args.command == "ingest":
        response = ingest_discord_event(request, store=store, config=config)
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
