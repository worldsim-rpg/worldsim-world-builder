# CLAUDE.md — worldsim-world-builder

Правила для Claude Code в этом репо.

## Что это

Мир-движок. Три публичных функции: `run_world_init`, `run_location_detail`,
`run_turn_update`.

## Границы

- Пишет изменения: locations, characters (NPC), factions, secrets, arcs,
  plot_state, world_meta.
- НЕ пишет: `player_progression` — это зона `worldsim-personal-progression`.
  Если появляется соблазн добавить патч на `player_progression` —
  остановись, это нарушение разделения ответственности.

## Изменение поведения

- **Чаще всего нужно править промпт** в `prompts/*.md`, а не код.
- Код в `agent.py` — это тонкий клей между промптом и pydantic-схемой.
- Новые виды патчей (новое поле в канон) — добавлять в
  `worldsim-workspace/packages/schemas/`, потом `sync-all.sh`.

## Тесты

`python -m pytest -q`. Интеграционные (с реальным LLM) — только при
`ANTHROPIC_API_KEY` в окружении, иначе skip.
