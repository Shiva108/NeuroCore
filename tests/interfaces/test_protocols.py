from __future__ import annotations

from neurocore.core.config import NeuroCoreConfig
from neurocore.interfaces.capture import capture_memory
from neurocore.interfaces.protocols import list_protocols, run_protocol
from neurocore.storage.in_memory import InMemoryStore


def build_config() -> NeuroCoreConfig:
    return NeuroCoreConfig(
        default_namespace="security-lab",
        allowed_buckets=("recon", "findings", "reports", "agents", "ops"),
        default_sensitivity="restricted",
        enable_multi_model_consensus=False,
    )


def test_run_protocol_cti_review_v1_returns_protocol_payload_with_required_sections():
    store = InMemoryStore()
    config = build_config()
    capture_memory(
        {
            "namespace": "security-lab",
            "bucket": "findings",
            "sensitivity": "restricted",
            "content": (
                "Critical finding. CVE-2026-1234 affects the review target. "
                "Next action: validate exposure and prioritize remediation."
            ),
            "content_format": "markdown",
            "source_type": "note",
            "tags": ["ciso-concern"],
        },
        store=store,
        config=config,
    )

    response = run_protocol(
        {
            "name": "cti-review-v1",
            "namespace": "security-lab",
            "query_text": "critical finding",
        },
        store=store,
        config=config,
    )

    assert response["protocol"]["name"] == "cti-review-v1"
    assert response["report"].startswith("## Overview")
    assert "## Findings" in response["report"]
    assert "## Actions" in response["report"]


def test_list_protocols_returns_supported_protocol_manifests():
    protocols = list_protocols()

    assert len(protocols) >= 1
    names = {protocol["name"] for protocol in protocols}
    assert "cti-review-v1" in names
