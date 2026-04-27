from neurocore.core.config import NeuroCoreConfig
from neurocore.interfaces.capture import capture_memory
from neurocore.interfaces.reporting import generate_consensus_report
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
    config = NeuroCoreConfig(
        default_namespace="project-alpha",
        allowed_buckets=("research",),
        default_sensitivity="standard",
        enable_multi_model_consensus=False,
    )

    try:
        generate_consensus_report(
            {
                "objective": "Generate a report.",
                "context_markdown": "Context",
            },
            store=InMemoryStore(),
            config=config,
            reporter=FakeReporter(),
        )
    except PermissionError as exc:
        assert "Reporting is disabled" in str(exc)
    else:
        raise AssertionError("Expected reporting to be gated by configuration")
