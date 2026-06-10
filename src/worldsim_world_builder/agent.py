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
        max_tokens=16000,
        temperature=0.8,
    )
    from worldsim_prompts import extract_json

    parsed = extract_json(raw)
    if not isinstance(parsed, dict):
        raise ValueError(
            f"world-builder вернул {type(parsed).__name__} вместо dict. "
            f"Начало ответа LLM: {raw[:300]}"
        )
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


_LIST_FIELDS = ("goals", "public_traits", "hidden_traits", "knowledge",
                "resources", "known_by", "involved_entities",
                "possible_escalations", "possible_revelations")


def _coerce_item(it: dict, model_cls, *, first_location_id: str = "") -> dict:
    """Нормализует поля, которые LLM иногда возвращает в упрощённом виде."""
    it = dict(it)

    # None → [] для всех полей-списков
    for f in _LIST_FIELDS:
        if it.get(f) is None:
            it[f] = []

    # goals: list[str] → list[Goal]
    if it.get("goals") and isinstance(it["goals"][0], str):
        it["goals"] = [{"text": g, "priority": 0.5} for g in it["goals"]]

    if model_cls is Character:
        # location_id обязателен — подставляем первую локацию если не задана
        if not it.get("location_id") and first_location_id:
            it["location_id"] = first_location_id

    if model_cls is Faction:
        # public_role обязателен
        if not it.get("public_role"):
            it["public_role"] = it.get("description", "неизвестно")

    if model_cls is Arc:
        # LLM иногда использует 'name' вместо 'title'
        if not it.get("title") and it.get("name"):
            it["title"] = it["name"]
        # involved_entities может прийти как dict {'characters': [...], 'factions': [...]}
        inv = it.get("involved_entities", [])
        if isinstance(inv, dict):
            flat = []
            for v in inv.values():
                if isinstance(v, list):
                    flat.extend(v)
            it["involved_entities"] = flat

    return it


def _assemble_snapshot(parsed: dict) -> WorldSnapshotDict:
    meta = WorldMeta.model_validate(parsed["meta"])
    settings = GameSettings.model_validate(parsed.get("settings") or {})

    first_loc = parsed.get("locations", [{}])[0].get("id", "") if parsed.get("locations") else ""

    def as_dict(items: list[dict], model_cls):
        return {
            it["id"]: model_cls.model_validate(_coerce_item(it, model_cls, first_location_id=first_loc))
            for it in items
        }

    raw_plot = dict(parsed.get("plot_state") or {})
    if "active_arcs" in raw_plot and isinstance(raw_plot["active_arcs"], list):
        raw_plot["active_arcs"] = [
            _coerce_item(a, Arc) if isinstance(a, dict) else a
            for a in raw_plot["active_arcs"]
        ]

    return WorldSnapshotDict(
        meta=meta,
        settings=settings,
        locations=as_dict(parsed.get("locations", []), Location),
        characters=as_dict(parsed.get("characters", []), Character),
        factions=as_dict(parsed.get("factions", []), Faction),
        secrets=as_dict(parsed.get("secrets", []), Secret),
        arcs=as_dict(parsed.get("arcs", []), Arc),
        plot_state=PlotState.model_validate(raw_plot),
        player_progression=PlayerProgression.model_validate(
            parsed.get("player_progression") or {}
        ),
    )
