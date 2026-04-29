"""Repo-local Claude Desktop MCP connector helper for NeuroCore."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from io import StringIO
from pathlib import Path
from typing import TextIO

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from neurocore.adapters.mcp_server import create_mcp_server
from neurocore.core.config import NeuroCoreConfig, load_config
from neurocore.interfaces.brains import list_brains
from neurocore.interfaces.briefing import generate_briefing
from neurocore.interfaces.protocols import list_protocols, run_protocol
from neurocore.interfaces.reporting import generate_consensus_report
from neurocore.interfaces.sessions import resume_session
from neurocore.runtime import build_semantic_ranker, build_store
from neurocore.storage.base import BaseStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python integrations/claude-desktop-mcp/connector.py")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("describe-tools")
    subparsers.add_parser("list-protocols")
    subparsers.add_parser("list-brains")
    config_parser = subparsers.add_parser("claude-config")
    config_parser.add_argument("--command", default="neurocore")
    config_parser.add_argument("--transport", default="stdio")
    for name in ("briefing", "protocol", "report", "session-resume"):
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
    output = stdout or sys.stdout

    if args.command == "describe-tools":
        server = create_mcp_server(store=store, config=config)
        payload = {"tools": asyncio.run(_list_tool_names(server))}
    elif args.command == "list-protocols":
        payload = {"protocols": list_protocols()}
    elif args.command == "list-brains":
        payload = list_brains({"include_archived": True}, store=store)
    elif args.command == "claude-config":
        payload = {
            "mcpServers": {
                "neurocore": {
                    "command": args.command,
                    "args": ["serve", "mcp", "--transport", args.transport],
                }
            }
        }
    else:
        request = _parse_request(args.request_json)
        if args.command == "briefing":
            payload = generate_briefing(
                request,
                store=store,
                config=config,
                semantic_ranker=semantic_ranker,
            )
        elif args.command == "report":
            payload = generate_consensus_report(
                request,
                store=store,
                config=config,
                semantic_ranker=semantic_ranker,
            )
        elif args.command == "session-resume":
            payload = resume_session(request, store=store, config=config)
        else:
            payload = run_protocol(
                request,
                store=store,
                config=config,
                semantic_ranker=semantic_ranker,
            )

    output.write(json.dumps(payload))
    output.write("\n")
    return 0


def run_for_test(argv: list[str], *, store: BaseStore, config: NeuroCoreConfig) -> dict[str, object]:
    buffer = StringIO()
    main(argv, store=store, config=config, stdout=buffer)
    return json.loads(buffer.getvalue())


async def _list_tool_names(server) -> list[str]:
    tools = await server.list_tools()
    return sorted(tool.name for tool in tools)


def _parse_request(raw: str) -> dict[str, object]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("request-json must decode to an object")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
