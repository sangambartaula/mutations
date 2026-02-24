import math
import pytest

from mut_calc import compute_profit_rates


def test_ready_strategy_exact_values():
    result = compute_profit_rates({
        "p": 0.25,
        "tau": 2.0,
        "k": 0,
        "m": 3,
        "x": 16,
        "v": 50000,
    })

    assert result["N"] == pytest.approx(48.0, rel=0.0, abs=1e-12)
    assert result["t0"] == pytest.approx(8.0, rel=0.0, abs=1e-12)
    assert result["rate_ready"] == pytest.approx(6.0, rel=0.0, abs=1e-12)
    assert result["profit_hr_ready"] == pytest.approx(300000.0, rel=0.0, abs=1e-9)


def test_rare_probability_is_finite_and_stable():
    result = compute_profit_rates({
        "p": 0.0002,
        "tau": 2.0,
        "k": 0,
        "m": 3,
        "x": 16,
        "v": 50000,
    })

    assert math.isfinite(result["t0"])
    assert math.isfinite(result["rate_ready"])
    assert result["t0"] == pytest.approx(10000.0, rel=0.0, abs=1e-6)
    assert result["rate_ready"] < 1e-2


def test_batch_strategy_h_sanity():
    base_inputs = {
        "p": 0.25,
        "tau": 2.0,
        "k": 0,
        "m": 3,
        "x": 16,
        "v": 50000,
        "v_boost": 60000,
        "B": 500000,
    }

    small_h = compute_profit_rates({**base_inputs, "H": 0.01})
    large_h = compute_profit_rates({**base_inputs, "H": 1_000_000.0})

    assert small_h["batch"]["boost_cost_hr"] > large_h["batch"]["boost_cost_hr"]
    assert large_h["batch"]["revenue_hr_batch"] < 10.0


def test_invalid_inputs_raise_value_error():
    invalid_cases = [
        {"p": 0.0, "tau": 2.0, "k": 0, "m": 3, "x": 16, "v": 1},
        {"p": 1.1, "tau": 2.0, "k": 0, "m": 3, "x": 16, "v": 1},
        {"p": 0.25, "tau": 0.0, "k": 0, "m": 3, "x": 16, "v": 1},
        {"p": 0.25, "tau": 2.0, "k": 0, "m": 0, "x": 16, "v": 1},
        {"p": 0.25, "tau": 2.0, "k": 0, "m": 3, "x": 0, "v": 1},
        {"p": 0.25, "tau": 2.0, "k": -1, "m": 3, "x": 16, "v": 1},
    ]

    for case in invalid_cases:
        with pytest.raises(ValueError):
            compute_profit_rates(case)
