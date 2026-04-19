# worldsim-world-builder

Мир-движок. Единственный агент, который пишет в канон про мир:
локации, NPC, фракции, секреты, арки, plot_state, world_meta.

Часть мульти-агентной системы [worldsim](https://github.com/b3axap/worldsim-workspace).

## Три подрежима

| Функция | Когда зовётся | Что возвращает |
|---|---|---|
| `run_world_init(input, *, client, model)` | один раз при `new` | `WorldSnapshot`-подобный dict со всем стартовым каноном |
| `run_location_detail(input, *, client, model)` | при первом посещении локации | `Location` с заполненным `full_description` и `active_elements` |
| `run_turn_update(input, *, client, model)` | каждый ход игрока | `TurnPatch` с изменениями мира |

## Промпты

- `prompts/world_init.md`
- `prompts/location_detail.md`
- `prompts/turn_update.md`

Их вы и редактируете, если хотите изменить поведение агента.

## Границы

НЕ пишет в `player_progression`. Это зона `worldsim-personal-progression`.
