"""Runtime factories for NeuroCore storage, ranking, and summarization."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from urllib.parse import urlparse

from neurocore.core.config import NeuroCoreConfig
from neurocore.retrieval.rankers import SemanticRanker, SentenceTransformersRanker
from neurocore.storage.base import BaseStore
from neurocore.storage.in_memory import InMemoryStore
from neurocore.storage.postgres_store import PostgresStore
from neurocore.storage.router import RoutedStore
from neurocore.storage.sqlite_store import SQLiteStore
from neurocore.summarization.background import Summarizer
from neurocore.summarization.consensus import (
    ConsensusSummarizer,
    MultiModelConsensusSummarizer,
    OpenAICompatibleSummaryClient,
)


def build_store(config: NeuroCoreConfig) -> BaseStore:
    """Build the configured routed storage backend."""
    if config.storage_backend == "sqlite":
        return RoutedStore(
            primary_store=SQLiteStore(config.primary_store_path),
            sealed_store=SQLiteStore(config.sealed_store_path),
        )
    if config.storage_backend == "postgres":
        if config.production_backend_provider == "none":
            raise ValueError(
                "Postgres storage backend requires a configured production backend provider"
            )
        if (
            not config.production_database_url
            or not config.production_sealed_database_url
        ):
            raise ValueError(
                "Postgres storage backend requires primary and sealed production database URLs"
            )
        return RoutedStore(
            primary_store=PostgresStore(config.production_database_url),
            sealed_store=PostgresStore(config.production_sealed_database_url),
        )
    return RoutedStore(primary_store=InMemoryStore(), sealed_store=InMemoryStore())


def build_semantic_ranker(config: NeuroCoreConfig) -> SemanticRanker | None:
    """Build the configured semantic ranker when one is enabled."""
    if config.semantic_backend == "sentence-transformers":
        return SentenceTransformersRanker(config.semantic_model_name)
    return None


def build_summarizer(config: NeuroCoreConfig) -> Summarizer:
    """Build the summary engine for the current runtime configuration."""
    if config.enable_multi_model_consensus:
        if config.consensus_provider != "openai_compatible":
            raise ValueError(
                "Multi-model consensus requires a supported consensus provider"
            )
        if len(config.consensus_model_names) < 2:
            raise ValueError(
                "Multi-model consensus requires at least two configured model names"
            )
        if len(set(config.consensus_model_names)) != len(config.consensus_model_names):
            raise ValueError("Multi-model consensus requires unique model names")
        if not config.consensus_base_url:
            raise ValueError("Multi-model consensus requires a consensus base URL")
        return MultiModelConsensusSummarizer(
            model_client=OpenAICompatibleSummaryClient(
                base_url=config.consensus_base_url,
                api_key=config.consensus_api_key,
            ),
            model_names=config.consensus_model_names,
        )
    return ConsensusSummarizer()


@dataclass(frozen=True)
class ProductionBackendChoice:
    """Sanitized view of the production backend configuration."""

    provider: str
    primary_configured: bool
    sealed_configured: bool
    status: str
    primary_url: str | None = None
    sealed_url: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a redacted dashboard-safe representation."""
        payload = asdict(self)
        payload["primary_url"] = None
        payload["sealed_url"] = None
        payload["primary_target"] = _redact_target(self.primary_url)
        payload["sealed_target"] = _redact_target(self.sealed_url)
        return payload


def build_production_backend_choice(config: NeuroCoreConfig) -> ProductionBackendChoice:
    """Summarize production backend readiness without exposing secrets."""
    if config.production_backend_provider == "none":
        return ProductionBackendChoice(
            provider="none",
            primary_configured=False,
            sealed_configured=False,
            status="disabled",
        )

    primary_configured = bool(config.production_database_url)
    sealed_configured = bool(config.production_sealed_database_url)
    status = "configured" if primary_configured and sealed_configured else "partial"
    return ProductionBackendChoice(
        provider=config.production_backend_provider,
        primary_configured=primary_configured,
        sealed_configured=sealed_configured,
        status=status,
        primary_url=config.production_database_url,
        sealed_url=config.production_sealed_database_url,
    )


def _redact_target(value: str | None) -> str | None:
    """Strip sensitive path and credential details from connection targets."""
    if value is None:
        return None
    parsed = urlparse(value)
    if parsed.scheme and parsed.hostname:
        if parsed.port is not None:
            return f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
        return f"{parsed.scheme}://{parsed.hostname}"
    return "configured"
