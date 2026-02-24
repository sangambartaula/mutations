import math
from unittest.mock import patch

from api.index import get_leaderboard


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
        harvest_strategy="batch",
        batch_hours=24.0,
        boost_cost=100000.0,
        boosted_value_override=1200.0,
        per_harvest_cost=0.0,
    )

    assert "leaderboard" in result
    assert len(result["leaderboard"]) > 0

    sample = next((m for m in result["leaderboard"] if m["mutationName"] == "Magic Jellybean"), result["leaderboard"][0])
    pm = sample.get("profit_models")
    assert pm is not None

    for key in [
        "tau_hours",
        "p",
        "g",
        "N",
        "cycles_per_harvest_per_spot",
        "hours_per_harvest_per_spot",
        "harvests_per_cycle",
        "harvests_per_hour",
        "profit_per_cycle",
        "profit_per_hour",
        "batch",
        "warnings",
    ]:
        assert key in pm

    for key in [
        "tau_hours",
        "p",
        "g",
        "N",
        "cycles_per_harvest_per_spot",
        "hours_per_harvest_per_spot",
        "harvests_per_cycle",
        "harvests_per_hour",
        "profit_per_cycle",
        "profit_per_hour",
    ]:
        assert math.isfinite(pm[key])

    for key in ["H", "w", "teff_hours", "harvests_per_hour_batch", "harvests_per_cycle_batch", "boost_cost_hr", "profit_per_hour_batch", "profit_per_cycle_batch"]:
        assert key in pm["batch"]
        assert pm["batch"][key] is None or math.isfinite(pm["batch"][key])
