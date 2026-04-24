"""Query interface for retrieving NeuroCore records and chunks."""

from __future__ import annotations

from neurocore.core.config import NeuroCoreConfig
from neurocore.retrieval.query import QueryEngine
from neurocore.retrieval.rankers import SemanticRanker
from neurocore.storage.base import BaseStore


def query_memory(
    request: dict[str, object],
    store: BaseStore,
    config: NeuroCoreConfig,
    semantic_ranker: SemanticRanker | None = None,
) -> dict[str, object]:
    engine = QueryEngine(store=store, semantic_ranker=semantic_ranker)
    return engine.execute(request, config)
