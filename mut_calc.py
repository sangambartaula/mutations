from typing import Any, Dict, List
import math

MAX_FLOAT = 1e308
SMALL_P_WARNING_CYCLES = 1e6
LARGE_T0_WARNING_HOURS = 1e6


def _safe_float(value: Any, name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number")


def _safe_int_nonneg(value: Any, name: str) -> int:
    try:
        iv = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be an integer")
    if iv < 0:
        raise ValueError(f"{name} must be >= 0")
    return iv


def format_warning_for_small_p(p: float) -> str:
    cycles = 1.0 / p
    return f"Expected spawn wait = 1/p cycles (~{cycles:.2f} cycles). Consider checking p value."


def _finite_or_cap(value: float, warnings: List[str], label: str) -> float:
    if math.isnan(value):
        warnings.append(f"{label} was NaN; returning 0.")
        return 0.0
    if math.isinf(value):
        capped = MAX_FLOAT if value > 0 else -MAX_FLOAT
        warnings.append(f"{label} overflowed; capped to {capped:.3e}.")
        return capped
    if value > MAX_FLOAT:
        warnings.append(f"{label} exceeded max float; capped to {MAX_FLOAT:.3e}.")
        return MAX_FLOAT
    if value < -MAX_FLOAT:
        warnings.append(f"{label} exceeded min float; capped to {-MAX_FLOAT:.3e}.")
        return -MAX_FLOAT
    return float(value)


def compute_profit_rates(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Compute deterministic mutation profit rates using expected-value math.

    Formulas:
    - N = m * x
    - t0 = tau * (1/p + k)
    - rate_ready = N / t0
    - revenue_hr_ready = rate_ready * v
    - profit_hr_ready = revenue_hr_ready - (rate_ready * c)

    Batch strategy (computed only when H > 0):
    - w = H/2
    - teff = t0 + w
    - rate_batch = N / teff
    - revenue_hr_batch = rate_batch * v_boost
    - boost_cost_hr = B / H
    - profit_hr_batch = revenue_hr_batch - boost_cost_hr
    """

    p = _safe_float(inputs.get("p"), "p")
    tau = _safe_float(inputs.get("tau"), "tau")
    m = _safe_int_nonneg(inputs.get("m"), "m")
    x = _safe_int_nonneg(inputs.get("x"), "x")
    k_raw = inputs.get("k", 0)
    k = _safe_int_nonneg(k_raw, "k")
    v = _safe_float(inputs.get("v"), "v")
    v_boost = _safe_float(inputs.get("v_boost", v), "v_boost")
    B = _safe_float(inputs.get("B", 0.0), "B")
    H = _safe_float(inputs.get("H", 0.0), "H")
    c = _safe_float(inputs.get("c", 0.0), "c")

    if p <= 0.0 or p > 1.0:
        raise ValueError("p must be in (0, 1]")
    if tau <= 0.0:
        raise ValueError("tau must be > 0")
    if m <= 0:
        raise ValueError("m must be > 0")
    if x <= 0:
        raise ValueError("x must be > 0")
    if k < 0:
        raise ValueError("k must be >= 0")
    if H < 0.0:
        raise ValueError("H must be >= 0")

    warnings: List[str] = []

    inv_p = 1.0 / p
    if inv_p > SMALL_P_WARNING_CYCLES:
        warnings.append(
            "extremely low spawn probability - expected spawn wait = "
            f"1/p cycles (~{inv_p:.2f} cycles)"
        )
        warnings.append(format_warning_for_small_p(p))

    N = float(m * x)
    t0 = tau * (inv_p + float(k))

    if t0 > LARGE_T0_WARNING_HOURS:
        warnings.append(
            f"extremely low spawn probability - expected mature wait t0 is very large (~{t0:.2f} hours)"
        )

    rate_ready = N / t0
    revenue_hr_ready = rate_ready * v
    profit_hr_ready = revenue_hr_ready - (rate_ready * c)

    N = _finite_or_cap(N, warnings, "N")
    t0 = _finite_or_cap(t0, warnings, "t0")
    rate_ready = _finite_or_cap(rate_ready, warnings, "rate_ready")
    revenue_hr_ready = _finite_or_cap(revenue_hr_ready, warnings, "revenue_hr_ready")
    profit_hr_ready = _finite_or_cap(profit_hr_ready, warnings, "profit_hr_ready")

    w_out: float | None = None
    teff_out: float | None = None
    rate_batch_out: float | None = None
    revenue_hr_batch_out: float | None = None
    boost_cost_hr_out: float | None = None
    profit_hr_batch_out: float | None = None
    batch: Dict[str, Any]
    if H > 0.0:
        w = H / 2.0
        teff = t0 + w
        if teff <= 0.0:
            raise ValueError("teff must be > 0")

        rate_batch = N / teff
        revenue_hr_batch = rate_batch * v_boost
        boost_cost_hr = B / H
        profit_hr_batch = revenue_hr_batch - boost_cost_hr

        w_out = _finite_or_cap(w, warnings, "w")
        teff_out = _finite_or_cap(teff, warnings, "teff")
        rate_batch_out = _finite_or_cap(rate_batch, warnings, "rate_batch")
        revenue_hr_batch_out = _finite_or_cap(revenue_hr_batch, warnings, "revenue_hr_batch")
        boost_cost_hr_out = _finite_or_cap(boost_cost_hr, warnings, "boost_cost_hr")
        profit_hr_batch_out = _finite_or_cap(profit_hr_batch, warnings, "profit_hr_batch")

        batch = {
            "H": _finite_or_cap(H, warnings, "H"),
            "w": w_out,
            "teff": teff_out,
            "rate_batch": rate_batch_out,
            "revenue_hr_batch": revenue_hr_batch_out,
            "boost_cost_hr": boost_cost_hr_out,
            "profit_hr_batch": profit_hr_batch_out,
        }
    else:
        batch = {
            "H": None,
            "w": None,
            "teff": None,
            "rate_batch": None,
            "revenue_hr_batch": None,
            "boost_cost_hr": None,
            "profit_hr_batch": None,
        }

    return {
        "N": N,
        "t0": t0,
        "rate_ready": rate_ready,
        "revenue_hr_ready": revenue_hr_ready,
        "profit_hr_ready": profit_hr_ready,
        "teff": teff_out,
        "rate_batch": rate_batch_out,
        "revenue_hr_batch": revenue_hr_batch_out,
        "boost_cost_hr": boost_cost_hr_out,
        "profit_hr_batch": profit_hr_batch_out,
        "warning": warnings[0] if warnings else None,
        "batch": batch,
        "warnings": warnings,
    }
