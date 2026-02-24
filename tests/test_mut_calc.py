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


def test_known_case_matches_renewal_formula():
    result = compute_profit_rates({
        "m": 10,
        "x": 10,  # N = 100
        "p": 0.25,
        "tau": 2.0,
        "g": 1,
        "v": 10_000,
    })

    assert result["profit_per_cycle"] == pytest.approx(200_000.0, rel=0.0, abs=1e-9)


def test_p_zero_returns_zero_rates():
    result = compute_profit_rates({
        "m": 3,
        "x": 16,
        "p": 0.0,
        "tau": 2.0,
        "g": 0,
        "v": 50_000,
    })

    assert result["profit_per_cycle"] == pytest.approx(0.0, rel=0.0, abs=1e-9)
    assert result["profit_per_hour"] == pytest.approx(0.0, rel=0.0, abs=1e-9)
    assert result["harvests_per_cycle"] == pytest.approx(0.0, rel=0.0, abs=1e-9)


def test_multiplier_is_applied_in_v_before_profit_per_cycle():
    p = 0.25
    m = 4
    x = 25
    g = 1
    base_value = 1_000.0
    multiplier = 10.0
    per_harvest_cost = 100.0

    result = compute_profit_rates({
        "m": m,
        "x": x,
        "p": p,
        "tau": 1.0,
        "g": g,
        "v": base_value * multiplier,
        "per_harvest_cost": per_harvest_cost,
    })

    n = m * x
    expected_harvests_per_cycle = n / ((1 / p) + g)
    expected_v_net = (base_value * multiplier) - per_harvest_cost
    expected_profit_per_cycle = expected_harvests_per_cycle * expected_v_net

    assert result["v_net"] == pytest.approx(expected_v_net, rel=0.0, abs=1e-9)
    assert result["profit_per_cycle"] == pytest.approx(expected_profit_per_cycle, rel=0.0, abs=1e-9)


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


def test_invalid_inputs_rejected():
    invalid = [
        {"m": 3, "x": 16, "p": "x", "tau": 2.0, "g": 0, "v": 1},
        {"m": 3, "x": 16, "p": 0.25, "tau": "oops", "g": 0, "v": 1},
        {"m": "bad", "x": 16, "p": 0.25, "tau": 2.0, "g": 0, "v": 1},
        {"m": 3, "x": "bad", "p": 0.25, "tau": 2.0, "g": 0, "v": 1},
        {"m": 3, "x": 16, "p": 0.25, "tau": 2.0, "g": -1, "v": 1},
    ]

    for case in invalid:
        with pytest.raises(ValueError):
            compute_profit_rates(case)
