import pytest

from neurocore.reporting.consensus import MultiModelConsensusReporter


class FakeExternalReportClient:
    def __init__(self, outputs: dict[str, str]) -> None:
        self.outputs = outputs
        self.calls: list[str] = []

    def generate_report(self, *, model_name: str, prompt: str) -> str:
        self.calls.append(model_name)
        return self.outputs[model_name]


def test_multi_model_consensus_reporter_uses_all_models_and_returns_consensus():
    client = FakeExternalReportClient(
        {
            "model-a": (
                "## Overview\nA.\n## Findings\nB.\n## Risks\nC.\n## Actions\nD."
            ),
            "model-b": (
                "## Overview\nA.\n## Findings\nB.\n## Risks\nC.\n## Actions\nD."
            ),
            "model-c": (
                "## Overview\nX.\n## Findings\nY.\n## Risks\nZ.\n## Actions\nW."
            ),
        }
    )
    reporter = MultiModelConsensusReporter(
        model_client=client,
        model_names=("model-a", "model-b", "model-c"),
    )

    result = reporter.generate(
        objective="Generate a security review report.",
        context_markdown="Incident and query context",
    )

    assert client.calls == ["model-a", "model-b", "model-c"]
    assert result.report.startswith("## Overview")
    assert result.report == (
        "## Overview\nA.\n## Findings\nB.\n## Risks\nC.\n## Actions\nD."
    )
    assert set(result.model_outputs) == {"model-a", "model-b", "model-c"}
    assert result.agreement_score >= 0.66
    assert result.metadata["model_count"] == 3


def test_multi_model_consensus_reporter_rejects_duplicate_models():
    reporter = MultiModelConsensusReporter(
        model_client=FakeExternalReportClient({"model-a": "same"}),
        model_names=("model-a", "model-a"),
    )

    with pytest.raises(ValueError, match="unique model names"):
        reporter.generate(
            objective="Generate a review report.",
            context_markdown="Context",
        )


def test_multi_model_consensus_reporter_requires_two_models():
    reporter = MultiModelConsensusReporter(
        model_client=FakeExternalReportClient({"model-a": "only"}),
        model_names=("model-a",),
    )

    with pytest.raises(ValueError, match="at least two"):
        reporter.generate(
            objective="Generate a review report.",
            context_markdown="Context",
        )
