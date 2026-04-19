def test_import():
    from worldsim_world_builder import (  # noqa: F401
        run_location_detail,
        run_turn_update,
        run_world_init,
    )


def test_prompts_exist():
    from pathlib import Path

    p = Path(__file__).parent.parent / "prompts"
    assert (p / "world_init.md").exists()
    assert (p / "location_detail.md").exists()
    assert (p / "turn_update.md").exists()
