"""
world-builder — три подрежима: init, location detail, turn update.

Каждая функция принимает простой dict как input (сериализуется в
user-message) и возвращает pydantic-модель или обычный dict.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from worldsim_prompts import AnthropicClient, call_json, load_prompt
from worldsim_schemas import (
    Arc,
    Character,
    Faction,
    GameSettings,
    Location,
    PlayerProgression,
    PlotState,
    Secret,
    TurnPatch,
    WorldMeta,
)

_PROMPTS = Path(__file__).parent.parent.parent / "prompts"


def _user_block(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def run_world_init(
    input: dict[str, Any], *, client: AnthropicClient, model: str
) -> "WorldSnapshotDict":
    """
    Генерирует стартовый мир из вдохновения.

    input: {"inspiration": {...}, "world_id": "...", "settings": {...}}
    Возвращает: dataclass-подобный объект со всеми коллекциями канона.

    Мы возвращаем объект с dict-коллекциями (id → pydantic model), чтобы
    orchestrator мог напрямую передать его в `WorldSnapshot`.
    """

    system = load_prompt(_PROMPTS / "world_init.md")
    raw = client.complete(
        model=model,
        system=system,
        user=_user_block(input),
        max_tokens=8192,
        temperature=0.8,
    )
    from worldsim_prompts import extract_json

    parsed = extract_json(raw)
    return _assemble_snapshot(parsed)


def run_location_detail(
    input: dict[str, Any], *, client: AnthropicClient, model: str
) -> Location:
    """input: {"location": {...}, "context": {...}}"""

    system = load_prompt(_PROMPTS / "location_detail.md")
    return call_json(
        client,
        system=system,
        user=_user_block(input),
        model=model,
        schema=Location,
        max_tokens=1200,
        temperature=0.7,
    )


def run_turn_update(
    input: dict[str, Any], *, client: AnthropicClient, model: str
) -> TurnPatch:
    """input: {"intent": {...}, "npc_response": ..., "context": {...}}"""

    system = load_prompt(_PROMPTS / "turn_update.md")
    return call_json(
        client,
        system=system,
        user=_user_block(input),
        model=model,
        schema=TurnPatch,
        max_tokens=2400,
        temperature=0.7,
    )


# --- сборка init-результата в структуру, удобную orchestrator'у ----------


class WorldSnapshotDict:
    """
    Лёгкая обёртка, которую orchestrator оборачивает в свой WorldSnapshot.
    Хранит pydantic-модели уже проверенными.
    """

    def __init__(
        self,
        meta: WorldMeta,
        settings: GameSettings,
        locations: dict[str, Location],
        characters: dict[str, Character],
        factions: dict[str, Faction],
        secrets: dict[str, Secret],
        arcs: dict[str, Arc],
        plot_state: PlotState,
        player_progression: PlayerProgression,
    ):
        self.meta = meta
        self.settings = settings
        self.locations = locations
        self.characters = characters
        self.factions = factions
        self.secrets = secrets
        self.arcs = arcs
        self.plot_state = plot_state
        self.player_progression = player_progression


def _assemble_snapshot(parsed: dict) -> WorldSnapshotDict:
    meta = WorldMeta.model_validate(parsed["meta"])
    settings = GameSettings.model_validate(parsed.get("settings") or {})

    def as_dict(items: list[dict], model_cls):
        return {it["id"]: model_cls.model_validate(it) for it in items}

    return WorldSnapshotDict(
        meta=meta,
        settings=settings,
        locations=as_dict(parsed.get("locations", []), Location),
        characters=as_dict(parsed.get("characters", []), Character),
        factions=as_dict(parsed.get("factions", []), Faction),
        secrets=as_dict(parsed.get("secrets", []), Secret),
        arcs=as_dict(parsed.get("arcs", []), Arc),
        plot_state=PlotState.model_validate(parsed.get("plot_state") or {}),
        player_progression=PlayerProgression.model_validate(
            parsed.get("player_progression") or {}
        ),
    )
