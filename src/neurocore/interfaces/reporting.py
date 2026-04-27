"""Public reporting interfaces built on top of NeuroCore retrieval."""

from __future__ import annotations

from typing import Any

from neurocore.core.config import NeuroCoreConfig
from neurocore.interfaces.query import query_memory
from neurocore.reporting.consensus import MultiModelConsensusReporter
from neurocore.reporting.workflows import build_report_context_from_query_response
from neurocore.runtime import build_reporter
from neurocore.storage.base import BaseStore


def generate_consensus_report(
    request: dict[str, object],
    *,
    store: BaseStore,
    config: NeuroCoreConfig,
    semantic_ranker: object | None = None,
    reporter: MultiModelConsensusReporter | Any | None = None,
) -> dict[str, object]:
    """Generate a multi-model consensus report from explicit or queried context."""
    if not config.enable_multi_model_consensus:
        raise PermissionError("Reporting is disabled")

    objective = str(request.get("objective", "")).strip()
    if not objective:
        raise ValueError("objective is required")

    max_items = _parse_max_items(request.get("max_items", 5))
    sections = _parse_sections(request.get("sections"))
    context_source, context_markdown, query_id = _resolve_context(
        request,
        store=store,
        config=config,
        semantic_ranker=semantic_ranker,
        max_items=max_items,
    )
    active_reporter = reporter or build_reporter(config)
    result = active_reporter.generate(
        objective=objective,
        context_markdown=context_markdown,
        sections=sections,
    )
    payload = result.to_dict() if hasattr(result, "to_dict") else dict(result)
    metadata = dict(payload.get("metadata", {}))
    metadata["context_source"] = context_source
    if query_id:
        metadata["query_id"] = query_id
    payload["metadata"] = metadata
    payload["context_markdown"] = context_markdown
    return payload


def _resolve_context(
    request: dict[str, object],
    *,
    store: BaseStore,
    config: NeuroCoreConfig,
    semantic_ranker: object | None,
    max_items: int,
) -> tuple[str, str, str | None]:
    raw_context = request.get("context_markdown")
    if isinstance(raw_context, str) and raw_context.strip():
        return "context_markdown", raw_context.strip(), None

    raw_query_response = request.get("query_response")
    if isinstance(raw_query_response, dict):
        return (
            "query_response",
            build_report_context_from_query_response(
                raw_query_response, max_items=max_items
            ),
            _optional_query_id(raw_query_response),
        )

    raw_query_request = request.get("query_request")
    if isinstance(raw_query_request, dict):
        query_response = query_memory(
            raw_query_request,
            store=store,
            config=config,
            semantic_ranker=semantic_ranker,
        )
        return (
            "query_request",
            build_report_context_from_query_response(
                query_response, max_items=max_items
            ),
            _optional_query_id(query_response),
        )

    raise ValueError(
        "request must include context_markdown, query_response, or query_request"
    )


def _parse_max_items(raw: object) -> int:
    if isinstance(raw, bool):
        raise ValueError("max_items must be an integer")
    try:
        max_items = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("max_items must be an integer") from exc
    if max_items < 1:
        raise ValueError("max_items must be >= 1")
    return max_items


def _parse_sections(raw: object) -> tuple[str, ...]:
    if raw is None:
        return ("Overview", "Findings", "Risks", "Actions")
    if not isinstance(raw, (list, tuple)):
        raise ValueError("sections must be a list of strings")
    sections = tuple(str(section).strip() for section in raw if str(section).strip())
    if not sections:
        raise ValueError("sections must include at least one heading")
    return sections


def _optional_query_id(query_response: dict[str, object]) -> str | None:
    query_id = query_response.get("query_id")
    if query_id in (None, ""):
        return None
    return str(query_id)
