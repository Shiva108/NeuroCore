import pytest

from neurocore.core.config import ConfigError, NeuroCoreConfig, load_config


def test_load_config_requires_mandatory_environment_variables(monkeypatch):
    required_keys = [
        "NEUROCORE_DEFAULT_NAMESPACE",
        "NEUROCORE_ALLOWED_BUCKETS",
        "NEUROCORE_DEFAULT_SENSITIVITY",
    ]

    for key in required_keys:
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(ConfigError, match="NEUROCORE_DEFAULT_NAMESPACE"):
        load_config()


def test_load_config_rejects_invalid_bucket_entries(monkeypatch):
    monkeypatch.setenv("NEUROCORE_DEFAULT_NAMESPACE", "project-alpha")
    monkeypatch.setenv("NEUROCORE_ALLOWED_BUCKETS", "research,invalid bucket")
    monkeypatch.setenv("NEUROCORE_DEFAULT_SENSITIVITY", "standard")

    with pytest.raises(ConfigError, match="bucket"):
        load_config()


def test_load_config_rejects_invalid_sensitivity(monkeypatch):
    monkeypatch.setenv("NEUROCORE_DEFAULT_NAMESPACE", "project-alpha")
    monkeypatch.setenv("NEUROCORE_ALLOWED_BUCKETS", "research,planning")
    monkeypatch.setenv("NEUROCORE_DEFAULT_SENSITIVITY", "top-secret")

    with pytest.raises(ConfigError, match="sensitivity"):
        load_config()


def test_load_config_applies_documented_defaults(monkeypatch):
    monkeypatch.setenv("NEUROCORE_DEFAULT_NAMESPACE", "project-alpha")
    monkeypatch.setenv("NEUROCORE_ALLOWED_BUCKETS", "research,planning")
    monkeypatch.setenv("NEUROCORE_DEFAULT_SENSITIVITY", "restricted")

    config = load_config()

    assert isinstance(config, NeuroCoreConfig)
    assert config.default_namespace == "project-alpha"
    assert config.allowed_buckets == ("research", "planning")
    assert config.default_sensitivity == "restricted"
    assert config.max_atomic_tokens == 350
    assert config.target_chunk_tokens == 600
    assert config.max_chunk_tokens == 900
    assert config.chunk_overlap_tokens == 75
    assert config.default_top_k == 8
    assert config.allow_hard_delete is False
    assert config.enable_admin_surface is False
    assert config.storage_backend == "in_memory"
    assert config.primary_store_path == "neurocore.db"
    assert config.sealed_store_path == "neurocore.sealed.db"
    assert config.semantic_backend == "none"
    assert config.semantic_model_name == "sentence-transformers/all-MiniLM-L6-v2"
    assert config.max_content_tokens == 50000
    assert config.enable_cli_adapter is True
    assert config.enable_http_adapter is False
    assert config.enable_mcp_adapter is False
    assert config.enable_dashboard is False
    assert config.enable_background_summarization is False
    assert config.enable_multi_model_consensus is False
    assert config.consensus_provider == "none"
    assert config.consensus_model_names == ()
    assert config.dedup_merge_metadata is True


def test_load_config_accepts_extended_backend_and_adapter_settings(monkeypatch):
    monkeypatch.setenv("NEUROCORE_DEFAULT_NAMESPACE", "project-alpha")
    monkeypatch.setenv("NEUROCORE_ALLOWED_BUCKETS", "research,planning")
    monkeypatch.setenv("NEUROCORE_DEFAULT_SENSITIVITY", "restricted")
    monkeypatch.setenv("NEUROCORE_STORAGE_BACKEND", "postgres")
    monkeypatch.setenv("NEUROCORE_PRIMARY_STORE_PATH", "/tmp/neurocore.db")
    monkeypatch.setenv("NEUROCORE_SEALED_STORE_PATH", "/tmp/neurocore.sealed.db")
    monkeypatch.setenv("NEUROCORE_SEMANTIC_BACKEND", "sentence-transformers")
    monkeypatch.setenv("NEUROCORE_SEMANTIC_MODEL_NAME", "test-model")
    monkeypatch.setenv("NEUROCORE_MAX_CONTENT_TOKENS", "1024")
    monkeypatch.setenv("NEUROCORE_ENABLE_HTTP_ADAPTER", "true")
    monkeypatch.setenv("NEUROCORE_ENABLE_MCP_ADAPTER", "true")
    monkeypatch.setenv("NEUROCORE_ENABLE_DASHBOARD", "true")
    monkeypatch.setenv("NEUROCORE_ENABLE_BACKGROUND_SUMMARIZATION", "true")
    monkeypatch.setenv("NEUROCORE_PRODUCTION_BACKEND_PROVIDER", "neon")
    monkeypatch.setenv("NEUROCORE_PRODUCTION_DATABASE_URL", "postgresql://primary")
    monkeypatch.setenv(
        "NEUROCORE_PRODUCTION_SEALED_DATABASE_URL", "postgresql://sealed"
    )
    monkeypatch.setenv("NEUROCORE_ENABLE_MULTI_MODEL_CONSENSUS", "true")
    monkeypatch.setenv("NEUROCORE_CONSENSUS_PROVIDER", "openai_compatible")
    monkeypatch.setenv(
        "NEUROCORE_CONSENSUS_MODEL_NAMES", "gpt-4.1-mini,claude-3.5-sonnet"
    )
    monkeypatch.setenv("NEUROCORE_CONSENSUS_BASE_URL", "https://api.example.test/v1")
    monkeypatch.setenv("NEUROCORE_CONSENSUS_API_KEY", "test-key")

    config = load_config()

    assert config.storage_backend == "postgres"
    assert config.primary_store_path == "/tmp/neurocore.db"
    assert config.sealed_store_path == "/tmp/neurocore.sealed.db"
    assert config.semantic_backend == "sentence-transformers"
    assert config.semantic_model_name == "test-model"
    assert config.max_content_tokens == 1024
    assert config.enable_http_adapter is True
    assert config.enable_mcp_adapter is True
    assert config.enable_dashboard is True
    assert config.enable_background_summarization is True
    assert config.enable_multi_model_consensus is True
    assert config.consensus_provider == "openai_compatible"
    assert config.consensus_model_names == ("gpt-4.1-mini", "claude-3.5-sonnet")
    assert config.consensus_base_url == "https://api.example.test/v1"
    assert config.consensus_api_key == "test-key"
    assert config.production_backend_provider == "neon"
    assert config.production_database_url == "postgresql://primary"
    assert config.production_sealed_database_url == "postgresql://sealed"


def test_load_config_rejects_invalid_storage_backend(monkeypatch):
    monkeypatch.setenv("NEUROCORE_DEFAULT_NAMESPACE", "project-alpha")
    monkeypatch.setenv("NEUROCORE_ALLOWED_BUCKETS", "research,planning")
    monkeypatch.setenv("NEUROCORE_DEFAULT_SENSITIVITY", "restricted")
    monkeypatch.setenv("NEUROCORE_STORAGE_BACKEND", "oracle")

    with pytest.raises(ConfigError, match="storage backend"):
        load_config()


def test_load_config_rejects_invalid_production_backend_provider(monkeypatch):
    monkeypatch.setenv("NEUROCORE_DEFAULT_NAMESPACE", "project-alpha")
    monkeypatch.setenv("NEUROCORE_ALLOWED_BUCKETS", "research,planning")
    monkeypatch.setenv("NEUROCORE_DEFAULT_SENSITIVITY", "restricted")
    monkeypatch.setenv("NEUROCORE_PRODUCTION_BACKEND_PROVIDER", "mystery-cloud")

    with pytest.raises(ConfigError, match="production backend provider"):
        load_config()


def test_load_config_rejects_invalid_consensus_provider(monkeypatch):
    monkeypatch.setenv("NEUROCORE_DEFAULT_NAMESPACE", "project-alpha")
    monkeypatch.setenv("NEUROCORE_ALLOWED_BUCKETS", "research,planning")
    monkeypatch.setenv("NEUROCORE_DEFAULT_SENSITIVITY", "restricted")
    monkeypatch.setenv("NEUROCORE_CONSENSUS_PROVIDER", "mystery")

    with pytest.raises(ConfigError, match="consensus provider"):
        load_config()
