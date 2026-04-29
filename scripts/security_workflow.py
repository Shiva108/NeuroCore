"""Helper workflow for NeuroCore security operations and research capture."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import TextIO
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from neurocore.core.config import ConfigError, load_config
from neurocore.core.semantic import sentence_transformers_status
from neurocore.runtime import build_reporter

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
LOCAL_CONSENSUS_BASE_URL = "http://127.0.0.1:8787/v1"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Capture and query security research, notes, and agent artifacts "
            "through the local NeuroCore install."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_capture_note_parser(subparsers)
    _add_capture_file_parser(subparsers)
    _add_capture_paper_parser(subparsers)
    _add_capture_hackingagent_parser(subparsers)
    _add_query_parser(subparsers)
    _add_briefing_parser(subparsers)
    _add_report_parser(subparsers)
    _add_utility_parsers(subparsers)
    return parser


def _add_capture_note_parser(subparsers) -> None:
    note_parser = subparsers.add_parser(
        "capture-note", help="Store a short note or observation."
    )
    _add_capture_args(
        note_parser,
        default_bucket="ops",
        default_source_type="note",
    )
    note_parser.add_argument("content", help="Note content to store.")


def _add_capture_file_parser(subparsers) -> None:
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


def _add_capture_paper_parser(subparsers) -> None:
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


def _add_capture_hackingagent_parser(subparsers) -> None:
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


def _add_query_parser(subparsers) -> None:
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


def _add_briefing_parser(subparsers) -> None:
    briefing_parser = subparsers.add_parser(
        "briefing",
        help="Generate a compact markdown briefing from NeuroCore query context.",
    )
    briefing_parser.add_argument("query_text", help="Search text.")
    briefing_parser.add_argument(
        "--namespace",
        help="Override the default namespace from .env.",
    )
    briefing_parser.add_argument(
        "--brain-id",
        help="Alias for namespace used by integrations and the reference app.",
    )
    briefing_parser.add_argument(
        "--preset",
        choices=PRESET_NAMES,
        help="Apply a saved workflow preset.",
    )
    briefing_parser.add_argument(
        "--bucket",
        action="append",
        choices=SECURITY_BUCKETS,
        default=[],
        help="Repeat to search one or more buckets. Defaults to preset query buckets.",
    )
    briefing_parser.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Repeat to match any of these tags.",
    )
    briefing_parser.add_argument(
        "--source-type",
        action="append",
        default=[],
        help="Repeat to filter by source type such as paper or agent_trace.",
    )
    briefing_parser.add_argument(
        "--top-k",
        type=int,
        default=8,
        help="Maximum number of query results to retrieve.",
    )
    briefing_parser.add_argument(
        "--max-items",
        type=int,
        default=5,
        help="Maximum number of retrieved items to include in briefing context.",
    )
    briefing_parser.add_argument(
        "--return-mode",
        choices=("hybrid", "record_only", "chunk_only", "document_aggregate"),
        default="hybrid",
        help="Query response mode.",
    )
    briefing_parser.add_argument(
        "--sensitivity-ceiling",
        default=None,
        help="Override the retrieval sensitivity ceiling.",
    )
    briefing_parser.add_argument(
        "--include-operator-hints",
        action="store_true",
        help="Include operator retrospective memory when available.",
    )


def _add_report_parser(subparsers) -> None:
    report_parser = subparsers.add_parser(
        "report",
        help="Generate a consensus report from NeuroCore query context.",
    )
    report_parser.add_argument("query_text", help="Search text.")
    report_parser.add_argument(
        "--objective",
        required=True,
        help="Report objective sent to the consensus reporter.",
    )
    report_parser.add_argument(
        "--namespace",
        help="Override the default namespace from .env.",
    )
    report_parser.add_argument(
        "--preset",
        choices=PRESET_NAMES,
        help="Apply a saved workflow preset.",
    )
    report_parser.add_argument(
        "--bucket",
        action="append",
        choices=SECURITY_BUCKETS,
        default=[],
        help="Repeat to search one or more buckets. Defaults to preset query buckets.",
    )
    report_parser.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Repeat to match any of these tags.",
    )
    report_parser.add_argument(
        "--source-type",
        action="append",
        default=[],
        help="Repeat to filter by source type such as paper or agent_trace.",
    )
    report_parser.add_argument(
        "--section",
        action="append",
        default=[],
        help="Repeat to choose report sections.",
    )
    report_parser.add_argument(
        "--top-k",
        type=int,
        default=8,
        help="Maximum number of query results to retrieve before reporting.",
    )
    report_parser.add_argument(
        "--max-items",
        type=int,
        default=5,
        help="Maximum number of retrieved items to include in report context.",
    )
    report_parser.add_argument(
        "--return-mode",
        choices=("hybrid", "record_only", "chunk_only", "document_aggregate"),
        default="hybrid",
        help="Query response mode.",
    )
    report_parser.add_argument(
        "--sensitivity-ceiling",
        default=None,
        help="Override the retrieval sensitivity ceiling.",
    )
    report_parser.add_argument(
        "--target",
        default=None,
        help="Optional target or engagement label carried with the request.",
    )


def _add_utility_parsers(subparsers) -> None:
    subparsers.add_parser(
        "capabilities",
        help="Report helper readiness for sibling bridge integrations.",
    )
    subparsers.add_parser("presets", help="List the saved workflow presets.")


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
    repo_root = Path(__file__).resolve().parents[1]
    _maybe_reexec_into_repo_runtime(argv or sys.argv[1:], repo_root)
    parser = build_parser()
    args = parser.parse_args(argv)
    env = _runtime_env(repo_root)

    if args.command == "presets":
        print(json.dumps(PRESETS, indent=2, sort_keys=True))
        return 0

    if args.command == "capabilities":
        print(json.dumps(_capabilities_payload(repo_root, env), indent=2, sort_keys=True))
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
        artifact_tags = []
        if args.artifact_type:
            artifact_tags.extend(
                [args.artifact_type, f"artifact:{args.artifact_type}"]
            )
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
            extra_tags=artifact_tags,
        )
        return _run_neurocore(repo_root, env, "capture", request)

    if args.command == "report":
        query_request = _build_query_request(args, env)
        report_request: dict[str, object] = {
            "objective": args.objective,
            "query_request": query_request,
            "max_items": args.max_items,
        }
        if args.section:
            report_request["sections"] = args.section
        if args.target:
            report_request["target"] = args.target
        return _run_neurocore(repo_root, env, ["report", "consensus"], report_request)

    if args.command == "briefing":
        briefing_request: dict[str, object] = {
            "query_request": _build_query_request(args, env),
            "max_items": args.max_items,
            "include_operator_hints": args.include_operator_hints,
        }
        if args.brain_id:
            briefing_request["brain_id"] = args.brain_id
        return _run_neurocore(repo_root, env, "briefing", briefing_request)

    return _run_neurocore(repo_root, env, "query", _build_query_request(args, env))


def _build_capture_request(
    args: argparse.Namespace,
    *,
    content: str,
    metadata: dict[str, object],
    content_format: str,
    title: str | None = None,
    extra_tags: list[str] | None = None,
) -> dict[str, object]:
    preset = PRESETS.get(args.preset or "", {})
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


def _build_query_request(
    args: argparse.Namespace, env: dict[str, str]
) -> dict[str, object]:
    preset = PRESETS.get(args.preset or "", {})
    request = {
        "query_text": args.query_text,
        "allowed_buckets": args.bucket
        or preset.get("query_buckets", list(SECURITY_BUCKETS)),
        "sensitivity_ceiling": (
            args.sensitivity_ceiling
            or env.get("NEUROCORE_DEFAULT_SENSITIVITY", "restricted")
        ),
        "top_k": args.top_k,
        "return_mode": args.return_mode,
    }
    namespace = getattr(args, "namespace", None)
    brain_id = getattr(args, "brain_id", None)
    if namespace:
        request["namespace"] = args.namespace
    elif brain_id:
        request["namespace"] = brain_id
    if args.tag:
        request["tags_any"] = args.tag
    if args.source_type:
        request["source_types"] = args.source_type
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
    env.setdefault("NEUROCORE_DEFAULT_NAMESPACE", "security-lab")
    src_path = str(repo_root / "src")
    existing_pythonpath = env.get("PYTHONPATH", "").strip()
    if existing_pythonpath:
        parts = existing_pythonpath.split(os.pathsep)
        if src_path not in parts:
            env["PYTHONPATH"] = os.pathsep.join([src_path, *parts])
    else:
        env["PYTHONPATH"] = src_path
    return env


def _capabilities_payload(repo_root: Path, env: dict[str, str]) -> dict[str, object]:
    issues: list[str] = []
    issues_by_surface: dict[str, list[str]] = {
        "runtime": [],
        "default_namespace": [],
        "query": [],
        "semantic": [],
        "report": [],
    }
    default_namespace_ready = bool(env.get("NEUROCORE_DEFAULT_NAMESPACE", "").strip())
    if not default_namespace_ready:
        issues_by_surface["default_namespace"].append(
            "Missing required configuration: NEUROCORE_DEFAULT_NAMESPACE"
        )
    if not (repo_root / ".env").exists():
        issues_by_surface["runtime"].append(
            f"Missing NeuroCore .env file: {repo_root / '.env'}"
        )

    resolved_python = _resolve_repo_python(repo_root, env)
    if resolved_python is None:
        issues_by_surface["runtime"].append(
            "NeuroCore Python executable is missing. "
            "Set NEUROCORE_PYTHON_EXECUTABLE or run `python scripts/bootstrap.py` first."
        )

    query_ready = False
    semantic_ready = False
    report_ready = False
    briefing_ready = False
    report_provider_mode = "disabled"
    config = None
    try:
        config = load_config(env)
        query_ready = True
        briefing_ready = True
    except ConfigError as exc:
        issues_by_surface["query"].append(str(exc))

    if config is not None:
        report_provider_mode = _report_provider_mode(config)
        if config.semantic_backend == "none":
            semantic_ready = True
        elif config.semantic_backend == "sentence-transformers":
            semantic_status, semantic_issue = sentence_transformers_status()
            semantic_ready = semantic_status == "ready"
            if not semantic_ready:
                query_ready = False
                briefing_ready = False
                if semantic_issue:
                    issues_by_surface["semantic"].append(semantic_issue)
        else:
            issues_by_surface["semantic"].append(
                f"Semantic backend {config.semantic_backend} is not recognized."
            )
            query_ready = False
            briefing_ready = False
        try:
            build_reporter(config)
            report_ready, report_issue = _check_reporter_health(config)
            if report_issue:
                issues_by_surface["report"].append(report_issue)
        except PermissionError:
            issues_by_surface["report"].append("Consensus reporting disabled")
        except ValueError as exc:
            issues_by_surface["report"].append(str(exc))

    for surface_issues in issues_by_surface.values():
        issues.extend(surface_issues)

    return {
        "config_ready": query_ready,
        "default_namespace_ready": default_namespace_ready,
        "consensus_report_ready": report_ready,
        "briefing_ready": briefing_ready,
        "semantic_ready": semantic_ready,
        "query_ready": query_ready,
        "report_ready": report_ready,
        "report_provider_mode": report_provider_mode,
        "resolved_python": str(resolved_python) if resolved_python else None,
        "issues_by_surface": {
            key: value for key, value in issues_by_surface.items() if value
        },
        "issues": _dedupe_strings(issues),
    }


def _report_provider_mode(config) -> str:
    if not config.enable_multi_model_consensus:
        return "disabled"
    if _is_local_mock_base_url(config.consensus_base_url):
        return "mock_local"
    return "external_openai_compatible"


def _is_local_mock_base_url(base_url: str | None) -> bool:
    if not base_url:
        return False
    parsed = urlparse(base_url)
    host = (parsed.hostname or "").lower()
    path = parsed.path.rstrip("/") or "/"
    return host in {"127.0.0.1", "localhost"} and path == "/v1"


def _check_reporter_health(config) -> tuple[bool, str | None]:
    base_url = (config.consensus_base_url or "").rstrip("/")
    if not base_url:
        return False, "Consensus reporting requires a consensus base URL"
    headers = {}
    if config.consensus_api_key:
        headers["Authorization"] = f"Bearer {config.consensus_api_key}"
    if _is_local_mock_base_url(base_url):
        parsed = urlparse(base_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        health_urls = [f"{origin}/health"]
    else:
        health_urls = [f"{base_url}/models", f"{base_url}/health"]
    last_error = "Consensus reporter health check failed"
    for url in health_urls:
        req = urllib_request.Request(url=url, headers=headers, method="GET")
        try:
            with urllib_request.urlopen(req, timeout=2.0) as response:
                if 200 <= int(response.status) < 300:
                    return True, None
                last_error = (
                    "Consensus reporter health check returned "
                    f"HTTP {response.status}"
                )
        except urllib_error.URLError as exc:
            last_error = f"Consensus reporter health check failed: {exc.reason}"
    return False, last_error


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
    command: str | list[str],
    request: dict[str, object],
) -> int:
    python_path = _resolve_repo_python(repo_root, env)
    if python_path is None:
        raise SystemExit(
            "NeuroCore Python executable is missing. "
            "Set NEUROCORE_PYTHON_EXECUTABLE or run `python scripts/bootstrap.py` first."
        )

    command_parts = [command] if isinstance(command, str) else list(command)
    completed = subprocess.run(
        [
            str(python_path),
            "-m",
            "neurocore.adapters.cli",
            *command_parts,
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


def _resolve_repo_python(repo_root: Path, env: dict[str, str]) -> Path | None:
    override = env.get("NEUROCORE_PYTHON_EXECUTABLE", "").strip()
    candidates: list[Path] = []
    if override:
        candidates.append(Path(override).expanduser())
    candidates.extend(
        [
            repo_root / ".venv" / "bin" / "python",
            repo_root / ".venv" / "Scripts" / "python.exe",
        ]
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate.expanduser().absolute()
    return None


def _maybe_reexec_into_repo_runtime(argv: list[str], repo_root: Path) -> None:
    repo_python = _resolve_repo_python(repo_root, dict(os.environ))
    if repo_python is None:
        return
    venv_dir = repo_root / ".venv"
    if Path(sys.prefix).resolve() == venv_dir.resolve():
        return
    if os.environ.get("NEUROCORE_SKIP_RUNTIME_REEXEC") == "1":
        return
    env = dict(os.environ)
    env["NEUROCORE_SKIP_RUNTIME_REEXEC"] = "1"
    os.execve(str(repo_python), [str(repo_python), str(Path(__file__)), *argv], env)


def print_readiness_summary(
    *,
    repo_root: Path,
    env: dict[str, str],
    stdout: TextIO,
) -> None:
    payload = _capabilities_payload(repo_root, env)
    print("", file=stdout)
    print(
        "Readiness summary:"
        f" semantic={'ready' if payload['semantic_ready'] else 'not ready'};"
        f" query={'ready' if payload['query_ready'] else 'not ready'};"
        f" report={'ready' if payload['report_ready'] else 'not ready'}",
        file=stdout,
    )
    print(
        f"Report provider mode: {payload['report_provider_mode']}",
        file=stdout,
    )
    if payload["report_ready"] and payload["report_provider_mode"] == "mock_local":
        print(
            "Report readiness is currently using the local mock provider for development only.",
            file=stdout,
        )
    report_issues = payload.get("issues_by_surface", {}).get("report", [])
    if report_issues:
        print("Report prerequisites still missing:", file=stdout)
        for issue in report_issues:
            print(f"- {issue}", file=stdout)
        print(
            "Local-only report generation can use the bundled mock provider at "
            f"{LOCAL_CONSENSUS_BASE_URL}.",
            file=stdout,
        )


if __name__ == "__main__":
    raise SystemExit(main())
