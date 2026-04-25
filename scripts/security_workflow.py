"""Helper workflow for NeuroCore security operations and research capture."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


SECURITY_BUCKETS = (
    "recon",
    "targets",
    "findings",
    "payloads",
    "reports",
    "agents",
    "ops",
)
PRESETS = {
    "bb": {
        "description": "Bug bounty recon, triage, and payload recall.",
        "capture_bucket": "recon",
        "capture_tags": ["bug-bounty"],
        "query_buckets": ["targets", "recon", "findings", "payloads", "agents"],
    },
    "pentest": {
        "description": "Penetration testing and red-team operator knowledge.",
        "capture_bucket": "ops",
        "capture_tags": ["pentest"],
        "query_buckets": [
            "targets",
            "recon",
            "findings",
            "payloads",
            "reports",
            "agents",
            "ops",
        ],
    },
    "paper": {
        "description": "External research, article digests, and arXiv-style papers.",
        "capture_bucket": "reports",
        "capture_source_type": "paper",
        "capture_tags": ["research", "paper"],
        "query_buckets": ["reports", "agents", "payloads", "ops"],
    },
    "agent": {
        "description": "Hackingagent traces, LLM experiments, and agent artifacts.",
        "capture_bucket": "agents",
        "capture_source_type": "agent_trace",
        "capture_tags": ["hackingagent"],
        "query_buckets": ["agents", "recon", "findings", "payloads", "ops"],
    },
}
PRESET_NAMES = tuple(PRESETS)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Capture and query security research, notes, and agent artifacts "
            "through the local NeuroCore install."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    note_parser = subparsers.add_parser(
        "capture-note", help="Store a short note or observation."
    )
    _add_capture_args(
        note_parser,
        default_bucket="ops",
        default_source_type="note",
    )
    note_parser.add_argument("content", help="Note content to store.")

    file_parser = subparsers.add_parser(
        "capture-file",
        help="Store a local file as a note, article digest, playbook, or report.",
    )
    _add_capture_args(
        file_parser,
        default_bucket="reports",
        default_source_type="article",
    )
    file_parser.add_argument("path", help="Path to the source file to ingest.")
    file_parser.add_argument(
        "--content-format",
        default=None,
        help="Override the auto-detected content format.",
    )

    paper_parser = subparsers.add_parser(
        "capture-paper",
        help="Store a scientific paper summary, notes, or arXiv-style digest.",
    )
    _add_capture_args(
        paper_parser,
        default_bucket="reports",
        default_source_type="paper",
    )
    paper_parser.add_argument("--url", help="Paper URL or arXiv link.")
    paper_parser.add_argument(
        "--authors",
        action="append",
        default=[],
        help="Repeat for multiple authors.",
    )
    paper_parser.add_argument(
        "--topic",
        action="append",
        default=[],
        help="Repeat for topic tags such as llm, red-team, or web-security.",
    )
    paper_parser.add_argument(
        "--published-at",
        help="Publication date in ISO format or freeform text.",
    )
    paper_parser.add_argument(
        "--summary",
        help="Inline paper summary or key findings.",
    )
    paper_parser.add_argument(
        "--summary-file",
        help="Path to a markdown or text file containing the summary.",
    )
    paper_parser.add_argument(
        "--notes",
        help="Inline operator notes about why the paper matters.",
    )
    paper_parser.add_argument(
        "--notes-file",
        help="Path to a markdown or text file containing extra notes.",
    )

    agent_parser = subparsers.add_parser(
        "capture-hackingagent",
        help="Store a local hackingagent artifact, session log, or prompt trace.",
    )
    _add_capture_args(
        agent_parser,
        default_bucket="agents",
        default_source_type="agent_trace",
    )
    agent_parser.add_argument("path", help="Path to the hackingagent artifact.")
    agent_parser.add_argument(
        "--artifact-type",
        default="session-log",
        help="Describe the artifact kind, for example session-log or prompt-trace.",
    )
    agent_parser.add_argument(
        "--target",
        help="Optional target, client, or lab name tied to the artifact.",
    )
    agent_parser.add_argument(
        "--project",
        default="hackingagent",
        help="Source project name. Defaults to hackingagent.",
    )

    query_parser = subparsers.add_parser(
        "query",
        help="Search across captured security knowledge and agent artifacts.",
    )
    query_parser.add_argument("query_text", help="Search text.")
    query_parser.add_argument(
        "--namespace",
        help="Override the default namespace from .env.",
    )
    query_parser.add_argument(
        "--preset",
        choices=PRESET_NAMES,
        help="Apply a saved workflow preset.",
    )
    query_parser.add_argument(
        "--bucket",
        action="append",
        choices=SECURITY_BUCKETS,
        default=[],
        help="Repeat to search one or more buckets. Defaults to all security buckets.",
    )
    query_parser.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Repeat to match any of these tags.",
    )
    query_parser.add_argument(
        "--source-type",
        action="append",
        default=[],
        help="Repeat to filter by source type such as paper or agent_trace.",
    )
    query_parser.add_argument(
        "--top-k",
        type=int,
        default=8,
        help="Maximum number of results to return.",
    )
    query_parser.add_argument(
        "--return-mode",
        choices=("hybrid", "record_only", "chunk_only", "document_aggregate"),
        default="hybrid",
        help="Query response mode.",
    )
    query_parser.add_argument(
        "--sensitivity-ceiling",
        default=None,
        help="Override the retrieval sensitivity ceiling.",
    )

    subparsers.add_parser("presets", help="List the saved workflow presets.")

    return parser


def _add_capture_args(
    parser: argparse.ArgumentParser,
    *,
    default_bucket: str,
    default_source_type: str,
) -> None:
    parser.set_defaults(
        fallback_bucket=default_bucket,
        fallback_source_type=default_source_type,
    )
    parser.add_argument(
        "--preset",
        choices=PRESET_NAMES,
        help="Apply a saved workflow preset.",
    )
    parser.add_argument(
        "--namespace",
        help="Override the default namespace from .env.",
    )
    parser.add_argument(
        "--bucket",
        default=None,
        choices=SECURITY_BUCKETS,
        help="Destination bucket.",
    )
    parser.add_argument(
        "--sensitivity",
        default=None,
        help="Override the default sensitivity from .env.",
    )
    parser.add_argument(
        "--source-type",
        default=None,
        help="Logical source type, for example note, paper, article, or agent_trace.",
    )
    parser.add_argument("--title", help="Optional title for longer captures.")
    parser.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Repeat to attach tags.",
    )
    parser.add_argument(
        "--metadata-json",
        default="{}",
        help="JSON object merged into metadata.",
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]
    env = _runtime_env(repo_root)

    if args.command == "presets":
        print(json.dumps(PRESETS, indent=2, sort_keys=True))
        return 0

    if args.command == "capture-note":
        request = _build_capture_request(
            args,
            content=args.content,
            metadata={},
            content_format="markdown",
        )
        return _run_neurocore(repo_root, env, "capture", request)

    if args.command == "capture-file":
        path = Path(args.path).expanduser().resolve()
        content = _read_text_file(path, description="capture file")
        request = _build_capture_request(
            args,
            content=content,
            metadata={"source_path": str(path)},
            content_format=args.content_format or _detect_content_format(path),
            title=args.title or path.stem.replace("-", " ").replace("_", " "),
        )
        return _run_neurocore(repo_root, env, "capture", request)

    if args.command == "capture-paper":
        if not args.title:
            parser.error("capture-paper requires --title")
        summary_text = _optional_text(args.summary, args.summary_file)
        notes_text = _optional_text(args.notes, args.notes_file)
        request = _build_capture_request(
            args,
            content=_paper_markdown(
                title=args.title,
                url=args.url,
                authors=args.authors,
                published_at=args.published_at,
                summary=summary_text,
                notes=notes_text,
            ),
            metadata={
                "paper_url": args.url,
                "authors": args.authors,
                "published_at": args.published_at,
                "topics": args.topic,
            },
            content_format="markdown",
            title=args.title,
            extra_tags=args.topic,
        )
        return _run_neurocore(repo_root, env, "capture", request)

    if args.command == "capture-hackingagent":
        path = Path(args.path).expanduser().resolve()
        content = _read_text_file(path, description="hackingagent artifact")
        request = _build_capture_request(
            args,
            content=content,
            metadata={
                "source_project": args.project,
                "artifact_type": args.artifact_type,
                "source_path": str(path),
                "target": args.target,
            },
            content_format=_detect_content_format(path),
            title=args.title or path.name,
        )
        return _run_neurocore(repo_root, env, "capture", request)

    preset = PRESETS.get(args.preset or "")
    request = {
        "query_text": args.query_text,
        "allowed_buckets": args.bucket or preset.get("query_buckets", list(SECURITY_BUCKETS)),
        "sensitivity_ceiling": (
            args.sensitivity_ceiling
            or env.get("NEUROCORE_DEFAULT_SENSITIVITY", "restricted")
        ),
        "top_k": args.top_k,
        "return_mode": args.return_mode,
    }
    if args.namespace:
        request["namespace"] = args.namespace
    if args.tag:
        request["tags_any"] = args.tag
    if args.source_type:
        request["source_types"] = args.source_type
    return _run_neurocore(repo_root, env, "query", request)


def _build_capture_request(
    args: argparse.Namespace,
    *,
    content: str,
    metadata: dict[str, object],
    content_format: str,
    title: str | None = None,
    extra_tags: list[str] | None = None,
) -> dict[str, object]:
    preset = PRESETS.get(args.preset or "")
    request: dict[str, object] = {
        "bucket": args.bucket or preset.get("capture_bucket") or args.fallback_bucket,
        "content": content,
        "content_format": content_format,
        "source_type": (
            args.source_type
            or preset.get("capture_source_type")
            or args.fallback_source_type
        ),
        "metadata": _merge_metadata(args.metadata_json, metadata),
    }
    if args.namespace:
        request["namespace"] = args.namespace
    if args.sensitivity:
        request["sensitivity"] = args.sensitivity
    tags = list(preset.get("capture_tags", [])) + list(args.tag)
    if extra_tags:
        tags.extend(extra_tags)
    if tags:
        request["tags"] = _dedupe_strings(tags)
    final_title = title or args.title
    if final_title:
        request["title"] = final_title
    return request


def _merge_metadata(raw_json: str, extra: dict[str, object]) -> dict[str, object]:
    metadata = json.loads(raw_json)
    if not isinstance(metadata, dict):
        raise ValueError("--metadata-json must decode to a JSON object")
    merged = dict(metadata)
    for key, value in extra.items():
        if value not in (None, "", []):
            merged[key] = value
    return merged


def _optional_text(inline: str | None, file_path: str | None) -> str | None:
    parts: list[str] = []
    if inline:
        parts.append(inline.strip())
    if file_path:
        parts.append(
            _read_text_file(
                Path(file_path).expanduser().resolve(),
                description="summary or notes file",
            ).strip()
        )
    joined = "\n\n".join(part for part in parts if part)
    return joined or None


def _read_text_file(path: Path, *, description: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise SystemExit(f"{description.capitalize()} not found: {path}") from exc
    except UnicodeDecodeError as exc:
        raise SystemExit(
            f"{description.capitalize()} must be UTF-8 text: {path}"
        ) from exc
    except OSError as exc:
        raise SystemExit(f"Could not read {description}: {path} ({exc})") from exc


def _paper_markdown(
    *,
    title: str,
    url: str | None,
    authors: list[str],
    published_at: str | None,
    summary: str | None,
    notes: str | None,
) -> str:
    sections = [f"# {title}"]
    if url:
        sections.append(f"Source: {url}")
    if authors:
        sections.append(f"Authors: {', '.join(authors)}")
    if published_at:
        sections.append(f"Published: {published_at}")
    if summary:
        sections.append(f"## Summary\n\n{summary}")
    if notes:
        sections.append(f"## Operator Notes\n\n{notes}")
    return "\n\n".join(sections)


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            ordered.append(value)
            seen.add(value)
    return ordered


def _detect_content_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown"}:
        return "markdown"
    if suffix == ".json":
        return "json"
    if suffix in {".html", ".htm"}:
        return "html"
    return "text"


def _runtime_env(repo_root: Path) -> dict[str, str]:
    env = dict(os.environ)
    env.update(_load_env_file(repo_root / ".env"))
    env.setdefault("NEUROCORE_ALLOWED_BUCKETS", ",".join(SECURITY_BUCKETS))
    env.setdefault("NEUROCORE_DEFAULT_SENSITIVITY", "restricted")
    return env


def _load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _run_neurocore(
    repo_root: Path,
    env: dict[str, str],
    command: str,
    request: dict[str, object],
) -> int:
    python_path = repo_root / ".venv" / "bin" / "python"
    if not python_path.exists():
        raise SystemExit(
            "NeuroCore virtual environment is missing. Run `python scripts/bootstrap.py` first."
        )

    completed = subprocess.run(
        [
            str(python_path),
            "-m",
            "neurocore.adapters.cli",
            command,
            "--request-json",
            json.dumps(request),
        ],
        cwd=repo_root,
        env=env,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        if completed.stderr:
            sys.stderr.write(completed.stderr)
        elif completed.stdout:
            sys.stderr.write(completed.stdout)
        return completed.returncode

    output = completed.stdout.strip()
    if not output:
        return 0
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        print(output)
        return 0
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
