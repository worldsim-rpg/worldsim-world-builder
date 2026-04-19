"""Contract-тесты world-builder без реального LLM."""

import json
from unittest.mock import MagicMock, patch

import pytest

from worldsim_schemas import Location, TurnPatch
from worldsim_world_builder.agent import (
    WorldSnapshotDict,
    run_location_detail,
    run_turn_update,
    run_world_init,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

MINIMAL_WORLD = {
    "meta": {
        "id": "w_test",
        "title": "Тестовый мир",
        "genre": "фэнтези",
        "tone": [],
        "themes": [],
        "premise": "Тест.",
    },
    "settings": {},
    "locations": [
        {"id": "loc_a", "name": "Доки", "short_description": "Соль."}
    ],
    "characters": [
        {"id": "pc", "name": "Игрок", "is_player": True, "location_id": "loc_a"}
    ],
    "factions": [],
    "secrets": [],
    "arcs": [],
    "plot_state": {},
    "player_progression": {},
}

LOCATION_RESPONSE = {
    "id": "loc_a",
    "name": "Доки",
    "short_description": "Соль.",
    "full_description": "Широкая набережная, пропитанная запахом рыбы.",
}

TURN_PATCH_RESPONSE: dict = {
    "world_changes": [],
    "new_facts": ["игрок_осмотрел_доки"],
    "timeline_event": None,
    "narrative_summary": "Игрок огляделся.",
}


def _mock_client(response: str) -> MagicMock:
    client = MagicMock()
    client.complete.return_value = response
    return client


# ---------------------------------------------------------------------------
# run_world_init
# ---------------------------------------------------------------------------


def test_run_world_init_returns_snapshot_dict():
    client = _mock_client(json.dumps(MINIMAL_WORLD))
    with patch("worldsim_world_builder.agent.load_prompt", return_value="system"):
        result = run_world_init({"inspiration": {}, "world_id": "w_test"}, client=client, model="m")
    assert isinstance(result, WorldSnapshotDict)
    assert result.meta.id == "w_test"
    assert "loc_a" in result.locations
    assert "pc" in result.characters


def test_run_world_init_parses_markdown_json():
    raw = f"```json\n{json.dumps(MINIMAL_WORLD)}\n```"
    client = _mock_client(raw)
    with patch("worldsim_world_builder.agent.load_prompt", return_value="system"):
        result = run_world_init({}, client=client, model="m")
    assert result.meta.title == "Тестовый мир"


def test_run_world_init_empty_collections():
    world = {**MINIMAL_WORLD, "factions": [], "secrets": [], "arcs": []}
    client = _mock_client(json.dumps(world))
    with patch("worldsim_world_builder.agent.load_prompt", return_value="system"):
        result = run_world_init({}, client=client, model="m")
    assert result.factions == {}
    assert result.secrets == {}
    assert result.arcs == {}


def test_run_world_init_passes_params_to_client():
    client = _mock_client(json.dumps(MINIMAL_WORLD))
    with patch("worldsim_world_builder.agent.load_prompt", return_value="system_prompt"):
        run_world_init({"inspiration": {"genre": "sci-fi"}}, client=client, model="claude-opus-4-7")
    client.complete.assert_called_once()
    call_kwargs = client.complete.call_args[1]
    assert call_kwargs["model"] == "claude-opus-4-7"
    assert call_kwargs["system"] == "system_prompt"


# ---------------------------------------------------------------------------
# run_location_detail
# ---------------------------------------------------------------------------


def test_run_location_detail_returns_location():
    client = _mock_client(json.dumps(LOCATION_RESPONSE))
    with patch("worldsim_world_builder.agent.load_prompt", return_value="system"):
        result = run_location_detail({"location": {}, "context": {}}, client=client, model="m")
    assert isinstance(result, Location)
    assert result.full_description == "Широкая набережная, пропитанная запахом рыбы."


def test_run_location_detail_invalid_json_raises():
    client = _mock_client("Not JSON at all.")
    with patch("worldsim_world_builder.agent.load_prompt", return_value="system"):
        with pytest.raises(Exception):
            run_location_detail({}, client=client, model="m")


def test_run_location_detail_invalid_schema_raises():
    client = _mock_client('{"wrong": "field"}')
    with patch("worldsim_world_builder.agent.load_prompt", return_value="system"):
        with pytest.raises(Exception):
            run_location_detail({}, client=client, model="m")


# ---------------------------------------------------------------------------
# run_turn_update
# ---------------------------------------------------------------------------


def test_run_turn_update_returns_turn_patch():
    client = _mock_client(json.dumps(TURN_PATCH_RESPONSE))
    with patch("worldsim_world_builder.agent.load_prompt", return_value="system"):
        result = run_turn_update({"intent": {}, "context": {}}, client=client, model="m")
    assert isinstance(result, TurnPatch)
    assert "игрок_осмотрел_доки" in result.new_facts
    assert result.narrative_summary == "Игрок огляделся."


def test_run_turn_update_with_world_changes():
    response = {
        "world_changes": [
            {
                "entity_type": "character",
                "id": "npc_mira",
                "field": "attitude_to_player",
                "op": "set",
                "value": 0.3,
            }
        ],
        "new_facts": [],
        "timeline_event": None,
        "narrative_summary": "",
    }
    client = _mock_client(json.dumps(response))
    with patch("worldsim_world_builder.agent.load_prompt", return_value="system"):
        result = run_turn_update({}, client=client, model="m")
    assert len(result.world_changes) == 1
    assert result.world_changes[0].id == "npc_mira"


def test_run_turn_update_empty_patch():
    response = {"world_changes": [], "new_facts": [], "timeline_event": None, "narrative_summary": ""}
    client = _mock_client(json.dumps(response))
    with patch("worldsim_world_builder.agent.load_prompt", return_value="system"):
        result = run_turn_update({}, client=client, model="m")
    assert isinstance(result, TurnPatch)
    assert result.world_changes == []


# ---------------------------------------------------------------------------
# MANIFESTS contract
# ---------------------------------------------------------------------------


def test_manifests_exported():
    from worldsim_world_builder import MANIFESTS
    from worldsim_schemas import AgentPhase
    phases = {m.phase for m in MANIFESTS}
    assert AgentPhase.WORLD_INIT in phases
    assert AgentPhase.LOCATION_DETAIL in phases
    assert AgentPhase.WORLD_UPDATE in phases


def test_manifests_entrypoints_callable():
    from worldsim_world_builder import MANIFESTS
    import worldsim_world_builder as pkg
    for m in MANIFESTS:
        assert callable(getattr(pkg, m.entrypoint, None)), f"{m.entrypoint} not callable"
