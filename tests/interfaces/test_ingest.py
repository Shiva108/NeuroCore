from neurocore.core.config import NeuroCoreConfig
from neurocore.interfaces.ingest import ingest_discord_event, ingest_slack_event
from neurocore.storage.in_memory import InMemoryStore


def build_config() -> NeuroCoreConfig:
    return NeuroCoreConfig(
        default_namespace="project-alpha",
        allowed_buckets=("research", "ops"),
        default_sensitivity="standard",
        max_atomic_tokens=6,
    )


def test_ingest_slack_message_captures_memory_record():
    store = InMemoryStore()

    response = ingest_slack_event(
        {
            "type": "event_callback",
            "team_id": "T123",
            "event": {
                "type": "message",
                "channel": "C123",
                "user": "U123",
                "text": "Slack message for memory",
                "ts": "1713897900.000100",
            },
            "bucket": "research",
        },
        store=store,
        config=build_config(),
    )

    assert response["ignored"] is False
    assert response["capture"]["kind"] == "record"
    assert store.get_record(response["capture"]["id"]) is not None


def test_ingest_discord_message_create_captures_memory_record():
    store = InMemoryStore()

    response = ingest_discord_event(
        {
            "t": "MESSAGE_CREATE",
            "d": {
                "id": "m-123",
                "guild_id": "g-123",
                "channel_id": "c-123",
                "author": {"id": "u-123", "username": "alice"},
                "content": "Discord message for memory",
                "timestamp": "2026-04-23T10:00:00+00:00",
            },
            "bucket": "ops",
        },
        store=store,
        config=build_config(),
    )

    assert response["ignored"] is False
    assert response["capture"]["kind"] == "record"
    assert store.get_record(response["capture"]["id"]) is not None
