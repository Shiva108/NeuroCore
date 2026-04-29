"""Connector metadata helpers for the reference app."""

from __future__ import annotations

import json
from pathlib import Path


def list_connector_statuses(repo_root: Path | None = None) -> list[dict[str, object]]:
    root = repo_root or Path(__file__).resolve().parents[3]
    integrations_dir = root / "integrations"
    connectors: list[dict[str, object]] = []
    for metadata_path in sorted(integrations_dir.glob("*/metadata.json")):
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        slug = metadata_path.parent.name
        connectors.append(
            {
                "slug": slug,
                "name": str(payload.get("name") or slug),
                "description": str(payload.get("description") or ""),
                "capabilities": list(payload.get("capabilities") or []),
                "runnable": bool((metadata_path.parent / "connector.py").exists()),
            }
        )
    return connectors
