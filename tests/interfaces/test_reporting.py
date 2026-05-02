from neurocore.core.config import NeuroCoreConfig
from neurocore.interfaces.capture import capture_memory
from neurocore.interfaces.reporting import (
    build_reporting_status,
    generate_consensus_report,
)
from neurocore.storage.in_memory import InMemoryStore


class FakeReporter:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate(
        self,
        *,
        objective: str,
        context_markdown: str,
        sections: tuple[str, ...] = ("Overview", "Findings", "Risks", "Actions"),
    ):
        self.calls.append(
            {
                "objective": objective,
                "context_markdown": context_markdown,
                "sections": sections,
            }
        )
        return {
            "report": "## Overview\nReady.",
            "model_outputs": {"model-a": "## Overview\nReady."},
            "agreement_score": 1.0,
            "metadata": {"sections": list(sections)},
        }


def test_generate_consensus_report_uses_query_request_context():
    store = InMemoryStore()
    config = NeuroCoreConfig(
        default_namespace="project-alpha",
        allowed_buckets=("research",),
        default_sensitivity="standard",
        enable_multi_model_consensus=True,
    )
    capture_memory(
        {
            "namespace": "project-alpha",
            "bucket": "research",
            "sensitivity": "standard",
            "content": "Validated SSRF finding with evidence and remediation notes.",
            "content_format": "markdown",
            "source_type": "note",
        },
        store=store,
        config=config,
    )
    reporter = FakeReporter()

    response = generate_consensus_report(
        {
            "objective": "Generate a security review report.",
            "query_request": {
                "query_text": "SSRF finding",
                "namespace": "project-alpha",
                "allowed_buckets": ["research"],
                "sensitivity_ceiling": "standard",
            },
            "sections": ["Overview", "Findings"],
            "max_items": 1,
        },
        store=store,
        config=config,
        reporter=reporter,
    )

    assert response["report"].startswith("## Overview")
    assert response["metadata"]["context_source"] == "query_request"
    assert response["metadata"]["query_id"].startswith("query-")
    assert "Validated SSRF finding" in response["context_markdown"]
    assert reporter.calls[0]["sections"] == ("Overview", "Findings")


def test_generate_consensus_report_uses_explicit_context_when_provided():
    config = NeuroCoreConfig(
        default_namespace="project-alpha",
        allowed_buckets=("research",),
        default_sensitivity="standard",
        enable_multi_model_consensus=True,
    )
    reporter = FakeReporter()

    response = generate_consensus_report(
        {
            "objective": "Generate an operator handoff report.",
            "context_markdown": "Explicit operator context",
        },
        store=InMemoryStore(),
        config=config,
        reporter=reporter,
    )

    assert response["metadata"]["context_source"] == "context_markdown"
    assert response["context_markdown"] == "Explicit operator context"
    assert reporter.calls[0]["context_markdown"] == "Explicit operator context"


def test_generate_consensus_report_requires_enabled_consensus_reporting():
    store = InMemoryStore()
    config = NeuroCoreConfig(
        default_namespace="project-alpha",
        allowed_buckets=("research",),
        default_sensitivity="standard",
        enable_multi_model_consensus=False,
    )
    capture_memory(
        {
            "namespace": "project-alpha",
            "bucket": "research",
            "sensitivity": "standard",
            "content": "Validated SSRF finding with evidence and remediation notes.",
            "content_format": "markdown",
            "source_type": "note",
        },
        store=store,
        config=config,
    )

    response = generate_consensus_report(
        {
            "objective": "Generate a report.",
            "query_request": {
                "query_text": "SSRF finding",
                "namespace": "project-alpha",
                "allowed_buckets": ["research"],
                "sensitivity_ceiling": "standard",
            },
        },
        store=store,
        config=config,
        reporter=FakeReporter(),
    )

    assert response["mode"] == "fallback-briefing"
    assert response["report"].startswith("## Overview")


def test_generate_consensus_report_falls_back_when_reporter_raises():
    store = InMemoryStore()
    config = NeuroCoreConfig(
        default_namespace="project-alpha",
        allowed_buckets=("research",),
        default_sensitivity="standard",
        enable_multi_model_consensus=True,
    )
    capture_memory(
        {
            "namespace": "project-alpha",
            "bucket": "research",
            "sensitivity": "standard",
            "content": "Validated SSRF finding with evidence and remediation notes.",
            "content_format": "markdown",
            "source_type": "note",
        },
        store=store,
        config=config,
    )

    class FailingReporter:
        def generate(self, **_kwargs):
            raise RuntimeError("reporter unavailable")

    response = generate_consensus_report(
        {
            "objective": "Generate a report.",
            "query_request": {
                "query_text": "SSRF finding",
                "namespace": "project-alpha",
                "allowed_buckets": ["research"],
                "sensitivity_ceiling": "standard",
            },
        },
        store=store,
        config=config,
        reporter=FailingReporter(),
    )

    assert response["mode"] == "fallback-briefing"
    assert response["metadata"]["fallback_reason"] == "reporter unavailable"


def test_build_reporting_status_emits_explicit_readiness_fields():
    disabled = NeuroCoreConfig(
        default_namespace="project-alpha",
        allowed_buckets=("research",),
        default_sensitivity="standard",
        enable_multi_model_consensus=False,
    )
    enabled = NeuroCoreConfig(
        default_namespace="project-alpha",
        allowed_buckets=("research",),
        default_sensitivity="standard",
        enable_multi_model_consensus=True,
        consensus_provider="openai_compatible",
        consensus_model_names=("gpt-1", "gpt-2"),
        consensus_base_url="http://reporter.test",
        consensus_api_key="token",
    )
    invalid_provider = NeuroCoreConfig(
        default_namespace="project-alpha",
        allowed_buckets=("research",),
        default_sensitivity="standard",
        enable_multi_model_consensus=True,
        consensus_provider="none",
    )

    disabled_status = build_reporting_status(disabled)
    enabled_status = build_reporting_status(enabled)
    invalid_status = build_reporting_status(invalid_provider)

    assert disabled_status["status"] == "fallback-only"
    assert disabled_status["configured"] is False
    assert disabled_status["bootstrapped"] is False
    assert disabled_status["healthy"] is False
    assert disabled_status["issues"]

    assert enabled_status["status"] == "healthy"
    assert enabled_status["configured"] is True
    assert enabled_status["bootstrapped"] is True
    assert enabled_status["healthy"] is True
    assert enabled_status["issues"] == []

    assert invalid_status["status"] == "degraded"
    assert invalid_status["configured"] is False
    assert invalid_status["bootstrapped"] is False
    assert invalid_status["healthy"] is False
    assert invalid_status["issues"] == ["Consensus reporting requires a supported consensus provider"]
