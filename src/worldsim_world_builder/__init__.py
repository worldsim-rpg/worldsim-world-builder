from worldsim_schemas import AgentManifest, AgentPhase

from .agent import run_location_detail, run_turn_update, run_world_init

MANIFESTS: list[AgentManifest] = [
    AgentManifest(
        name="world-builder.init",
        package="worldsim_world_builder",
        entrypoint="run_world_init",
        phase=AgentPhase.WORLD_INIT,
        model_tier="heavy",
        description="Генерация стартового мира.",
    ),
    AgentManifest(
        name="world-builder.location",
        package="worldsim_world_builder",
        entrypoint="run_location_detail",
        phase=AgentPhase.LOCATION_DETAIL,
        model_tier="heavy",
        description="Ленивая детализация локации.",
    ),
    AgentManifest(
        name="world-builder.turn",
        package="worldsim_world_builder",
        entrypoint="run_turn_update",
        phase=AgentPhase.WORLD_UPDATE,
        model_tier="heavy",
        description="Обновление мира по интенту игрока.",
    ),
]

__all__ = [
    "run_world_init",
    "run_location_detail",
    "run_turn_update",
    "MANIFESTS",
]
