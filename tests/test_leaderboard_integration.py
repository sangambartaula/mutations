import math
from unittest.mock import patch

from api.index import DEFAULT_METRIC_SPAWN_CHANCE, get_leaderboard


@patch("api.index.get_bazaar_prices", return_value={"Magic Jellybean": {"buyPrice": 1000, "sellPrice": 900}})
def test_leaderboard_exposes_profit_models_and_no_nan(_mock_prices):
    result = get_leaderboard(
        plots=3,
        fortune=2500,
        gh_upgrade=9,
        unique_crops=12,
        mode="profit",
        setup_mode="buy_order",
        sell_mode="sell_offer",
        target_crop=None,
        maxed_crops="",
        mutation_chance=0.0002,
        per_harvest_cost=0.0,
    )

    assert "leaderboard" in result
    assert len(result["leaderboard"]) > 0
    assert result["metadata"]["yield_breakdown"]["greenhouse_yield_upgrade"] == 9
    assert result["metadata"]["yield_breakdown"]["evergreen_chip_level"] == 20
    assert result["metadata"]["yield_breakdown"]["evergreen_chip_rarity"] == "legendary"
    assert result["metadata"]["yield_breakdown"]["overdrive_chip_level"] == 0
    assert result["metadata"]["speed_breakdown"]["greenhouse_speed_upgrade"] == 9
    assert result["metadata"]["fortune_breakdown"]["hypercharge_rarity"] == "legendary"

    sample = next((m for m in result["leaderboard"] if m["mutationName"] == "Magic Jellybean"), result["leaderboard"][0])
    pm = sample.get("profit_models")
    assert pm is not None
    assert "profit_per_growth_cycle" in sample
    assert math.isfinite(sample["profit_per_growth_cycle"])
    expected_cycles = (1.0 / DEFAULT_METRIC_SPAWN_CHANCE) + sample["breakdown"]["growth_stages"]
    assert sample["profit_per_growth_cycle"] == sample["profit"] / expected_cycles
    assert "warning_messages" in sample
    assert "profit_per_cycle" not in sample
    assert "break_even_cycles" not in sample
    assert "break_even_cycles_display" not in sample
    assert "profit_per_cycle" not in sample["hourly"]
    assert "break_even_cycles" not in sample["hourly"]
    assert "break_even_cycles_display" not in sample["hourly"]

    for key in [
        "tau_hours",
        "p",
        "g",
        "N",
        "expected_spawn_cycles",
        "expected_cycles",
        "expected_hours",
        "cycles_per_harvest_per_spot",
        "hours_per_harvest_per_spot",
        "harvests_per_cycle",
        "harvests_per_hour",
        "profit_per_cycle",
        "profit_per_hour",
        "warnings",
    ]:
        assert key in pm

    for key in [
        "tau_hours",
        "p",
        "g",
        "N",
        "expected_spawn_cycles",
        "expected_cycles",
        "expected_hours",
        "cycles_per_harvest_per_spot",
        "hours_per_harvest_per_spot",
        "harvests_per_cycle",
        "harvests_per_hour",
        "profit_per_cycle",
        "profit_per_hour",
    ]:
        assert math.isfinite(pm[key])

    assert "batch" not in pm
