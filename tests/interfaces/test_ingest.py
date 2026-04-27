import json

from neurocore.core.config import NeuroCoreConfig
from neurocore.interfaces.ingest import ingest_discord_event, ingest_slack_event
from neurocore.storage.in_memory import InMemoryStore


def build_config(**overrides) -> NeuroCoreConfig:
    return NeuroCoreConfig(
        default_namespace="project-alpha",
        allowed_buckets=("research", "ops"),
        default_sensitivity="standard",
        max_atomic_tokens=6,
        **overrides,
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


def test_ingest_slack_applies_matching_profile_defaults(tmp_path):
    profile_path = tmp_path / "profiles.json"
    profile_path.write_text(
        json.dumps(
            {
                "version": "1",
                "profiles": [
                    {
                        "name": "slack-ops",
                        "source": "slack",
                        "match": {"team_id": "T123", "channel_id": "C123"},
                        "defaults": {
                            "bucket": "ops",
                            "tags": ["ops-profile"],
                            "sensitivity": "restricted",
                        },
                        "parsing_hints": {"parser": "ops-note"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    store = InMemoryStore()
    config = build_config(
        ingest_profile_path=str(profile_path),
        ingest_profiles=json.loads(profile_path.read_text(encoding="utf-8")),
    )

    response = ingest_slack_event(
        {
            "type": "event_callback",
            "team_id": "T123",
            "event": {
                "type": "message",
                "channel": "C123",
                "user": "U123",
                "text": "Profiled Slack message",
                "ts": "1713897900.000100",
            },
        },
        store=store,
        config=config,
    )

    record = store.get_record(response["capture"]["id"])
    assert record is not None
    assert record.bucket == "ops"
    assert record.sensitivity == "restricted"
    assert set(record.tags) == {"slack", "ops-profile"}
    assert record.metadata["matched_ingest_profile"] == "slack-ops"
    assert record.metadata["ingest_parsing_hints"] == {"parser": "ops-note"}


def test_ingest_discord_uses_more_specific_profile_over_source_default(tmp_path):
    profile_path = tmp_path / "profiles.json"
    profile_path.write_text(
        json.dumps(
            {
                "version": "1",
                "profiles": [
                    {
                        "name": "discord-default",
                        "source": "discord",
                        "match": {"guild_id": "g-123"},
                        "defaults": {
                            "bucket": "research",
                            "tags": ["guild-default"],
                            "sensitivity": "standard",
                        },
                        "parsing_hints": {"mode": "default"},
                    },
                    {
                        "name": "discord-channel-specific",
                        "source": "discord",
                        "match": {"guild_id": "g-123", "channel_id": "c-123"},
                        "defaults": {
                            "bucket": "ops",
                            "tags": ["channel-specific"],
                            "sensitivity": "restricted",
                        },
                        "parsing_hints": {"mode": "specific"},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    store = InMemoryStore()
    config = build_config(
        ingest_profile_path=str(profile_path),
        ingest_profiles=json.loads(profile_path.read_text(encoding="utf-8")),
    )

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
        },
        store=store,
        config=config,
    )

    record = store.get_record(response["capture"]["id"])
    assert record is not None
    assert record.bucket == "ops"
    assert record.sensitivity == "restricted"
    assert "channel-specific" in record.tags
    assert record.metadata["matched_ingest_profile"] == "discord-channel-specific"
    assert record.metadata["ingest_parsing_hints"] == {"mode": "specific"}


def test_ingest_explicit_request_values_override_profile_defaults(tmp_path):
    profile_path = tmp_path / "profiles.json"
    profile_path.write_text(
        json.dumps(
            {
                "version": "1",
                "profiles": [
                    {
                        "name": "slack-ops",
                        "source": "slack",
                        "match": {"team_id": "T123"},
                        "defaults": {
                            "bucket": "ops",
                            "tags": ["ops-profile"],
                            "sensitivity": "restricted",
                        },
                        "parsing_hints": {"parser": "ops-note"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    store = InMemoryStore()
    config = build_config(
        ingest_profile_path=str(profile_path),
        ingest_profiles=json.loads(profile_path.read_text(encoding="utf-8")),
    )

    response = ingest_slack_event(
        {
            "type": "event_callback",
            "team_id": "T123",
            "bucket": "research",
            "sensitivity": "standard",
            "event": {
                "type": "message",
                "channel": "C123",
                "user": "U123",
                "text": "Profiled Slack message",
                "ts": "1713897900.000100",
            },
        },
        store=store,
        config=config,
    )

    record = store.get_record(response["capture"]["id"])
    assert record is not None
    assert record.bucket == "research"
    assert record.sensitivity == "standard"
    assert set(record.tags) == {"slack", "ops-profile"}


def test_ingest_without_profiles_keeps_existing_behavior():
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

    record = store.get_record(response["capture"]["id"])
    assert record is not None
    assert record.bucket == "research"
    assert record.sensitivity == "standard"
    assert record.tags == ("slack",)
    assert "matched_ingest_profile" not in record.metadata
