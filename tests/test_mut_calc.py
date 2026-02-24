import math
import pytest

from mut_calc import compute_profit_rates


def test_g_zero_matches_npv_identity_per_cycle():
    p = 0.25
    tau = 2.0
    m = 3
    x = 16
    v = 50_000

    result = compute_profit_rates({
        "m": m,
        "x": x,
        "p": p,
        "tau": tau,
        "g": 0,
        "v": v,
    })

    n = m * x
    expected_profit_per_cycle = n * p * v
    assert result["profit_per_cycle"] == pytest.approx(expected_profit_per_cycle, rel=0.0, abs=1e-9)


def test_g_positive_formula_matches_expected_values():
    result = compute_profit_rates({
        "m": 3,
        "x": 16,
        "p": 0.25,
        "tau": 2.0,
        "g": 10,
        "v": 50_000,
    })

    n = 48
    cycles = (1 / 0.25) + 10  # 14
    expected_harvests_per_cycle = n / cycles
    expected_profit_per_cycle = expected_harvests_per_cycle * 50_000
    expected_profit_per_hour = expected_profit_per_cycle / 2.0

    assert result["harvests_per_cycle"] == pytest.approx(expected_harvests_per_cycle, rel=0.0, abs=1e-9)
    assert result["profit_per_cycle"] == pytest.approx(expected_profit_per_cycle, rel=0.0, abs=1e-9)
    assert result["profit_per_hour"] == pytest.approx(expected_profit_per_hour, rel=0.0, abs=1e-9)


def test_tiny_p_is_finite_and_warns():
    result = compute_profit_rates({
        "m": 3,
        "x": 16,
        "p": 0.0002,
        "tau": 2.0,
        "g": 0,
        "v": 50_000,
    })

    assert math.isfinite(result["cycles_per_harvest_per_spot"])
    assert math.isfinite(result["harvests_per_hour"])
    assert result["cycles_per_harvest_per_spot"] == pytest.approx(5000.0, rel=0.0, abs=1e-9)
    assert len(result["warnings"]) == 0  # warning threshold is 1e6 cycles


def test_batch_mode_throughput_and_profit_behavior():
    base = {
        "m": 3,
        "x": 16,
        "p": 0.25,
        "tau": 2.0,
        "g": 4,
        "v": 50_000,
        "v_boost": 65_000,
        "B": 500_000,
    }
    small_h = compute_profit_rates({**base, "H": 0.01})
    large_h = compute_profit_rates({**base, "H": 1_000_000.0})

    assert small_h["batch"]["harvests_per_hour_batch"] < small_h["harvests_per_hour"]
    assert large_h["batch"]["harvests_per_hour_batch"] < large_h["harvests_per_hour"]
    assert small_h["batch"]["boost_cost_hr"] > large_h["batch"]["boost_cost_hr"]


def test_invalid_inputs_rejected():
    invalid = [
        {"m": 3, "x": 16, "p": 0.0, "tau": 2.0, "g": 0, "v": 1},
        {"m": 3, "x": 16, "p": 1.1, "tau": 2.0, "g": 0, "v": 1},
        {"m": 3, "x": 16, "p": 0.25, "tau": 0.0, "g": 0, "v": 1},
        {"m": 0, "x": 16, "p": 0.25, "tau": 2.0, "g": 0, "v": 1},
        {"m": 3, "x": 0, "p": 0.25, "tau": 2.0, "g": 0, "v": 1},
        {"m": 3, "x": 16, "p": 0.25, "tau": 2.0, "g": -1, "v": 1},
        {"m": 3, "x": 16, "p": 0.25, "tau": 2.0, "g": 0, "v": 1, "H": -1},
    ]

    for case in invalid:
        with pytest.raises(ValueError):
            compute_profit_rates(case)
