from typing import Any, Dict, List
import math

SMALL_P_WARNING_CYCLES = 1e6


def _safe_float(value: Any, name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number")


def _safe_int(value: Any, name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be an integer")


def format_warning_for_small_p(p: float) -> str:
    cycles = 1.0 / p
    return f"Expected spawn wait = 1/p cycles (~{cycles:.2f} cycles). Consider checking p value."


def _ensure_finite(value: float, name: str) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{name} became non-finite")
    return float(value)


def compute_profit_rates(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Compute expected mutation throughput and profit rates on a global growth-cycle model.

    Inputs:
    - m: plots
    - x: eligible spots per plot
    - p: spawn probability per empty spot per cycle, in (0,1]
    - tau: hours per global garden growth cycle
    - g: required growth cycles AFTER spawn until harvestable (g=0 instant)
    - v: gross coins per harvested mature mutation
    - per_harvest_cost: optional per harvested mutation cost (subtracted from v)
    Core formulas:
    - N = m * x
    - cycles_per_harvest_per_spot = 1/p + g
    - hours_per_harvest_per_spot = tau * (1/p + g)
    - harvests_per_hour = N / hours_per_harvest_per_spot
    - harvests_per_cycle = N / (1/p + g)
    - profit_per_hour = harvests_per_hour * (v - per_harvest_cost)
    - profit_per_cycle = harvests_per_cycle * (v - per_harvest_cost)

    """
    p = _safe_float(inputs.get("p"), "p")
    tau = _safe_float(inputs.get("tau"), "tau")
    m = _safe_int(inputs.get("m"), "m")
    x = _safe_int(inputs.get("x"), "x")
    g = _safe_int(inputs.get("g"), "g")
    v = _safe_float(inputs.get("v"), "v")
    per_harvest_cost = _safe_float(inputs.get("per_harvest_cost", 0.0), "per_harvest_cost")

    if p <= 0.0 or p > 1.0:
        raise ValueError("p must be in (0, 1]")
    if tau <= 0.0:
        raise ValueError("tau must be > 0")
    if m <= 0:
        raise ValueError("m must be > 0")
    if x <= 0:
        raise ValueError("x must be > 0")
    if g < 0:
        raise ValueError("g must be >= 0")

    warnings: List[str] = []
    inv_p = 1.0 / p
    if inv_p > SMALL_P_WARNING_CYCLES:
        warnings.append(format_warning_for_small_p(p))

    N = float(m * x)
    cycles_per_harvest_per_spot = inv_p + float(g)
    hours_per_harvest_per_spot = tau * cycles_per_harvest_per_spot

    v_net = v - per_harvest_cost

    harvests_per_hour = N / hours_per_harvest_per_spot
    harvests_per_cycle = N / cycles_per_harvest_per_spot
    profit_per_hour = harvests_per_hour * v_net
    profit_per_cycle = harvests_per_cycle * v_net

    N = _ensure_finite(N, "N")
    cycles_per_harvest_per_spot = _ensure_finite(cycles_per_harvest_per_spot, "cycles_per_harvest_per_spot")
    hours_per_harvest_per_spot = _ensure_finite(hours_per_harvest_per_spot, "hours_per_harvest_per_spot")
    harvests_per_hour = _ensure_finite(harvests_per_hour, "harvests_per_hour")
    harvests_per_cycle = _ensure_finite(harvests_per_cycle, "harvests_per_cycle")
    profit_per_hour = _ensure_finite(profit_per_hour, "profit_per_hour")
    profit_per_cycle = _ensure_finite(profit_per_cycle, "profit_per_cycle")

    return {
        "tau_hours": _ensure_finite(tau, "tau_hours"),
        "p": _ensure_finite(p, "p"),
        "g": float(g),
        "N": N,
        "cycles_per_harvest_per_spot": cycles_per_harvest_per_spot,
        "hours_per_harvest_per_spot": hours_per_harvest_per_spot,
        "harvests_per_cycle": harvests_per_cycle,
        "harvests_per_hour": harvests_per_hour,
        "profit_per_cycle": profit_per_cycle,
        "profit_per_hour": profit_per_hour,
        "v_net": _ensure_finite(v_net, "v_net"),
        "warnings": warnings,
    }
