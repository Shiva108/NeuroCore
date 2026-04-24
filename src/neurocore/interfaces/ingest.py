"""External event ingestion interfaces for NeuroCore."""

from __future__ import annotations

from datetime import UTC, datetime
import re

from neurocore.core.config import NeuroCoreConfig
from neurocore.interfaces.capture import capture_memory
from neurocore.storage.base import BaseStore


def ingest_slack_event(
    payload: dict[str, object], store: BaseStore, config: NeuroCoreConfig
) -> dict[str, object]:
    """Normalize a Slack event payload into a capture request."""
    if payload.get("type") == "url_verification":
        return {
            "source": "slack",
            "ignored": True,
            "challenge": payload.get("challenge"),
            "reason": "url_verification",
        }

    event = dict(payload.get("event", {}))
    if payload.get("type") != "event_callback" or event.get("type") != "message":
        return {"source": "slack", "ignored": True, "reason": "unsupported_event"}
    if event.get("subtype"):
        return {"source": "slack", "ignored": True, "reason": "unsupported_subtype"}

    capture = capture_memory(
        {
            "namespace": _external_namespace(
                payload.get("namespace"),
                payload.get("team_id"),
                prefix="slack",
                fallback=config.default_namespace,
            ),
            "bucket": str(payload.get("bucket") or config.allowed_buckets[0]),
            "sensitivity": str(
                payload.get("sensitivity") or config.default_sensitivity
            ),
            "content": str(event.get("text") or ""),
            "content_format": "markdown",
            "source_type": "slack_message",
            "created_at": _slack_timestamp_to_iso(event.get("ts")),
            "external_id": event.get("client_msg_id") or event.get("ts"),
            "metadata": {
                "platform": "slack",
                "team_id": payload.get("team_id"),
                "channel_id": event.get("channel"),
                "user_id": event.get("user"),
                "event_type": event.get("type"),
            },
            "tags": ["slack"],
            "title": f"Slack {event.get('channel')}",
        },
        store=store,
        config=config,
    )
    return {"source": "slack", "ignored": False, "capture": capture}


def ingest_discord_event(
    payload: dict[str, object], store: BaseStore, config: NeuroCoreConfig
) -> dict[str, object]:
    """Normalize a Discord message payload into a capture request."""
    envelope_type = payload.get("t")
    data = dict(payload.get("d", payload))
    if envelope_type and envelope_type != "MESSAGE_CREATE":
        return {"source": "discord", "ignored": True, "reason": "unsupported_event"}

    content = str(data.get("content") or "")
    if not content.strip():
        return {"source": "discord", "ignored": True, "reason": "empty_message"}

    author = dict(data.get("author", {}))
    capture = capture_memory(
        {
            "namespace": _external_namespace(
                payload.get("namespace"),
                data.get("guild_id"),
                prefix="discord",
                fallback=config.default_namespace,
            ),
            "bucket": str(payload.get("bucket") or config.allowed_buckets[0]),
            "sensitivity": str(
                payload.get("sensitivity") or config.default_sensitivity
            ),
            "content": content,
            "content_format": "markdown",
            "source_type": "discord_message",
            "created_at": data.get("timestamp"),
            "external_id": data.get("id"),
            "metadata": {
                "platform": "discord",
                "guild_id": data.get("guild_id"),
                "channel_id": data.get("channel_id"),
                "author_id": author.get("id"),
                "author_username": author.get("username"),
            },
            "tags": ["discord"],
            "title": f"Discord {data.get('channel_id')}",
        },
        store=store,
        config=config,
    )
    return {"source": "discord", "ignored": False, "capture": capture}


def _slack_timestamp_to_iso(value: object) -> str | None:
    """Convert a Slack floating-point timestamp into an ISO 8601 string."""
    if value is None:
        return None
    return datetime.fromtimestamp(float(str(value)), tz=UTC).isoformat()


def _external_namespace(
    explicit_namespace: object,
    external_identifier: object,
    *,
    prefix: str,
    fallback: str,
) -> str:
    """Derive a stable namespace for events coming from external platforms."""
    if explicit_namespace is not None and str(explicit_namespace).strip():
        return str(explicit_namespace)
    if external_identifier is None:
        return fallback
    normalized = re.sub(r"[^a-z0-9_-]+", "-", str(external_identifier).strip().lower())
    normalized = normalized.strip("-")
    if not normalized:
        return fallback
    return f"{prefix}-{normalized}"
