"""Multi-model consensus reporting helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Protocol
from urllib import error, request as urllib_request

from neurocore.reporting.workflows import build_sectioned_report_prompt


@dataclass(frozen=True)
class ConsensusReport:
    """Structured consensus report output."""

    report: str
    model_outputs: dict[str, str]
    agreement_score: float
    metadata: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "report": self.report,
            "model_outputs": self.model_outputs,
            "agreement_score": self.agreement_score,
            "metadata": self.metadata,
        }


class ExternalReportModelClient(Protocol):
    """Protocol for report-generation model backends."""

    def generate_report(self, *, model_name: str, prompt: str) -> str:
        """Generate a markdown report from a model-specific prompt."""


@dataclass(frozen=True)
class OpenAICompatibleReportClient:
    """Minimal client for OpenAI-compatible chat completion APIs."""

    base_url: str
    api_key: str | None = None
    timeout_seconds: float = 30.0

    def generate_report(self, *, model_name: str, prompt: str) -> str:
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib_request.Request(
            url=f"{self.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib_request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except error.URLError as exc:  # pragma: no cover - network path
            raise RuntimeError(
                f"Failed to call external report model {model_name}"
            ) from exc

        try:
            return str(body["choices"][0]["message"]["content"]).strip()
        except (
            KeyError,
            IndexError,
            TypeError,
        ) as exc:  # pragma: no cover - malformed remote response
            raise RuntimeError(
                f"Invalid response from external report model {model_name}"
            ) from exc


@dataclass(frozen=True)
class MultiModelConsensusReporter:
    """Consensus reporter that aggregates outputs from multiple models."""

    model_client: ExternalReportModelClient
    model_names: tuple[str, ...]

    def generate(
        self,
        *,
        objective: str,
        context_markdown: str,
        sections: tuple[str, ...] = ("Overview", "Findings", "Risks", "Actions"),
    ) -> ConsensusReport:
        if len(self.model_names) < 2:
            raise ValueError("Multi-model consensus requires at least two model names")
        if len(set(self.model_names)) != len(self.model_names):
            raise ValueError("Multi-model consensus requires unique model names")

        prompt = build_sectioned_report_prompt(
            objective=objective,
            context_markdown=context_markdown,
            sections=sections,
        )
        outputs = {
            model_name: self.model_client.generate_report(
                model_name=model_name, prompt=prompt
            )
            for model_name in self.model_names
        }
        selected = max(
            outputs.values(),
            key=lambda item: (_agreement(item, outputs), len(item)),
        )
        return ConsensusReport(
            report=selected,
            model_outputs=outputs,
            agreement_score=_agreement(selected, outputs),
            metadata={
                "objective": objective,
                "sections": list(sections),
                "model_count": len(self.model_names),
            },
        )


def _agreement(candidate: str, outputs: dict[str, str]) -> float:
    """Measure lexical agreement for one candidate against all outputs."""
    candidate_terms = set(candidate.lower().split())
    if not candidate_terms:
        return 1.0
    overlaps = []
    for output in outputs.values():
        output_terms = set(output.lower().split())
        overlaps.append(
            len(candidate_terms & output_terms) / max(len(candidate_terms), 1)
        )
    return round(sum(overlaps) / len(overlaps), 2)
