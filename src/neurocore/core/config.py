"""Runtime configuration loading and validation for NeuroCore."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

BUCKET_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
VALID_SENSITIVITIES = ("standard", "restricted", "sealed")
VALID_STORAGE_BACKENDS = ("in_memory", "sqlite", "postgres")
VALID_SEMANTIC_BACKENDS = ("none", "sentence-transformers")
VALID_PRODUCTION_BACKEND_PROVIDERS = ("none", "neon")
VALID_CONSENSUS_PROVIDERS = ("none", "openai_compatible")


class ConfigError(ValueError):
    """Raised when runtime configuration is invalid."""


@dataclass(frozen=True)
class NeuroCoreConfig:
    """Resolved runtime configuration for a NeuroCore process."""

    default_namespace: str
    allowed_buckets: tuple[str, ...]
    default_sensitivity: str
    storage_backend: str = "in_memory"
    primary_store_path: str = "neurocore.db"
    sealed_store_path: str = "neurocore.sealed.db"
    semantic_backend: str = "none"
    semantic_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    max_atomic_tokens: int = 350
    target_chunk_tokens: int = 600
    max_chunk_tokens: int = 900
    chunk_overlap_tokens: int = 75
    max_content_tokens: int = 50000
    default_top_k: int = 8
    allow_hard_delete: bool = False
    enable_admin_surface: bool = False
    enable_cli_adapter: bool = True
    enable_http_adapter: bool = False
    enable_mcp_adapter: bool = False
    enable_dashboard: bool = False
    enable_background_summarization: bool = False
    enable_multi_model_consensus: bool = False
    consensus_provider: str = "none"
    consensus_model_names: tuple[str, ...] = ()
    consensus_base_url: str | None = None
    consensus_api_key: str | None = None
    production_backend_provider: str = "none"
    production_database_url: str | None = None
    production_sealed_database_url: str | None = None
    dedup_merge_metadata: bool = True


def load_config(env: dict[str, str] | None = None) -> NeuroCoreConfig:
    """Load and validate configuration from environment-style key/value data."""
    values = dict(os.environ if env is None else env)
    default_namespace = _required(values, "NEUROCORE_DEFAULT_NAMESPACE")
    allowed_buckets = _parse_buckets(_required(values, "NEUROCORE_ALLOWED_BUCKETS"))
    default_sensitivity = _parse_sensitivity(
        _required(values, "NEUROCORE_DEFAULT_SENSITIVITY")
    )

    return NeuroCoreConfig(
        default_namespace=default_namespace,
        allowed_buckets=allowed_buckets,
        default_sensitivity=default_sensitivity,
        storage_backend=_parse_enum(
            values, "NEUROCORE_STORAGE_BACKEND", VALID_STORAGE_BACKENDS, "in_memory"
        ),
        primary_store_path=values.get("NEUROCORE_PRIMARY_STORE_PATH", "neurocore.db"),
        sealed_store_path=values.get(
            "NEUROCORE_SEALED_STORE_PATH", "neurocore.sealed.db"
        ),
        semantic_backend=_parse_enum(
            values, "NEUROCORE_SEMANTIC_BACKEND", VALID_SEMANTIC_BACKENDS, "none"
        ),
        semantic_model_name=values.get(
            "NEUROCORE_SEMANTIC_MODEL_NAME",
            "sentence-transformers/all-MiniLM-L6-v2",
        ),
        max_atomic_tokens=_parse_int(values, "NEUROCORE_MAX_ATOMIC_TOKENS", 350, 1),
        target_chunk_tokens=_parse_int(values, "NEUROCORE_TARGET_CHUNK_TOKENS", 600, 1),
        max_chunk_tokens=_parse_int(values, "NEUROCORE_MAX_CHUNK_TOKENS", 900, 1),
        chunk_overlap_tokens=_parse_int(
            values, "NEUROCORE_CHUNK_OVERLAP_TOKENS", 75, 0
        ),
        max_content_tokens=_parse_int(values, "NEUROCORE_MAX_CONTENT_TOKENS", 50000, 1),
        default_top_k=_parse_int(values, "NEUROCORE_DEFAULT_TOP_K", 8, 1),
        allow_hard_delete=_parse_bool(values, "NEUROCORE_ALLOW_HARD_DELETE", False),
        enable_admin_surface=_parse_bool(
            values, "NEUROCORE_ENABLE_ADMIN_SURFACE", False
        ),
        enable_cli_adapter=_parse_bool(values, "NEUROCORE_ENABLE_CLI_ADAPTER", True),
        enable_http_adapter=_parse_bool(values, "NEUROCORE_ENABLE_HTTP_ADAPTER", False),
        enable_mcp_adapter=_parse_bool(values, "NEUROCORE_ENABLE_MCP_ADAPTER", False),
        enable_dashboard=_parse_bool(values, "NEUROCORE_ENABLE_DASHBOARD", False),
        enable_background_summarization=_parse_bool(
            values, "NEUROCORE_ENABLE_BACKGROUND_SUMMARIZATION", False
        ),
        enable_multi_model_consensus=_parse_bool(
            values, "NEUROCORE_ENABLE_MULTI_MODEL_CONSENSUS", False
        ),
        consensus_provider=_parse_enum(
            values,
            "NEUROCORE_CONSENSUS_PROVIDER",
            VALID_CONSENSUS_PROVIDERS,
            "none",
        ),
        consensus_model_names=_parse_csv(values, "NEUROCORE_CONSENSUS_MODEL_NAMES"),
        consensus_base_url=_parse_optional_string(
            values, "NEUROCORE_CONSENSUS_BASE_URL"
        ),
        consensus_api_key=_parse_optional_string(values, "NEUROCORE_CONSENSUS_API_KEY"),
        production_backend_provider=_parse_enum(
            values,
            "NEUROCORE_PRODUCTION_BACKEND_PROVIDER",
            VALID_PRODUCTION_BACKEND_PROVIDERS,
            "none",
        ),
        production_database_url=_parse_optional_string(
            values, "NEUROCORE_PRODUCTION_DATABASE_URL"
        ),
        production_sealed_database_url=_parse_optional_string(
            values, "NEUROCORE_PRODUCTION_SEALED_DATABASE_URL"
        ),
        dedup_merge_metadata=_parse_bool(
            values, "NEUROCORE_DEDUP_MERGE_METADATA", True
        ),
    )


def _required(values: dict[str, str], key: str) -> str:
    """Return a required configuration value or raise a ConfigError."""
    value = values.get(key, "").strip()
    if not value:
        raise ConfigError(f"Missing required configuration: {key}")
    return value


def _parse_buckets(raw: str) -> tuple[str, ...]:
    """Parse and validate the allowed bucket list."""
    buckets = tuple(part.strip() for part in raw.split(",") if part.strip())
    if not buckets:
        raise ConfigError("At least one allowed bucket must be configured")
    invalid = [bucket for bucket in buckets if not BUCKET_PATTERN.match(bucket)]
    if invalid:
        raise ConfigError(f"Invalid bucket values: {', '.join(invalid)}")
    return buckets


def _parse_sensitivity(raw: str) -> str:
    """Parse the default sensitivity value."""
    value = raw.strip().lower()
    if value not in VALID_SENSITIVITIES:
        raise ConfigError(f"Invalid sensitivity value: {raw}")
    return value


def _parse_int(values: dict[str, str], key: str, default: int, minimum: int) -> int:
    """Parse an integer config value with minimum bound enforcement."""
    raw = values.get(key)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"Configuration {key} must be an integer") from exc
    if value < minimum:
        raise ConfigError(f"Configuration {key} must be >= {minimum}")
    return value


def _parse_bool(values: dict[str, str], key: str, default: bool) -> bool:
    """Parse a boolean config value from common truthy and falsy strings."""
    raw = values.get(key)
    if raw is None or not raw.strip():
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"Configuration {key} must be a boolean")


def _parse_enum(
    values: dict[str, str], key: str, valid: tuple[str, ...], default: str
) -> str:
    """Parse a string enum value."""
    raw = values.get(key)
    if raw is None or not raw.strip():
        return default
    value = raw.strip().lower()
    if value not in valid:
        label = key.replace("NEUROCORE_", "").replace("_", " ").lower()
        raise ConfigError(f"Invalid {label}: {raw}")
    return value


def _parse_optional_string(values: dict[str, str], key: str) -> str | None:
    """Return a stripped optional string value when present."""
    raw = values.get(key)
    if raw is None or not raw.strip():
        return None
    return raw.strip()


def _parse_csv(values: dict[str, str], key: str) -> tuple[str, ...]:
    """Parse a comma-separated configuration value."""
    raw = values.get(key)
    if raw is None or not raw.strip():
        return ()
    return tuple(part.strip() for part in raw.split(",") if part.strip())
