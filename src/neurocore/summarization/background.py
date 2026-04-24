"""Background summarization runner primitives for NeuroCore."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from neurocore.core.config import NeuroCoreConfig
from neurocore.storage.base import BaseStore
from neurocore.summarization.consensus import ConsensusSummary


class Summarizer(Protocol):
    """Protocol for summary engines used by the background runner."""

    def summarize(self, text: str, max_sentences: int = 2) -> ConsensusSummary:
        """Summarize text into a consensus summary."""


@dataclass
class BackgroundSummarizationRunner:
    """Iterate over eligible documents and write back summaries."""

    store: BaseStore
    config: NeuroCoreConfig
    summarizer: Summarizer

    def run(self, limit: int = 10) -> dict[str, object]:
        """Summarize up to ``limit`` unsummarized documents."""
        if not self.config.enable_background_summarization:
            raise PermissionError("Background summarization is disabled")

        processed = 0
        failed = 0
        warnings: list[str] = []
        for document in self.store.list_documents(include_archived=False):
            if processed >= limit:
                break
            if document.sensitivity == "sealed":
                continue
            if document.summary or not document.raw_content:
                continue
            try:
                consensus = self.summarizer.summarize(document.raw_content)
                self.store.update_document(
                    document.id,
                    patch={"summary": consensus.summary},
                    mode="in_place",
                )
                processed += 1
            except Exception as exc:
                failed += 1
                warnings.append(f"{document.id}: {exc}")

        return {"processed": processed, "failed": failed, "warnings": warnings}
