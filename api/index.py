import csv
import io
import os
import json
import time
import math
from collections import defaultdict, deque
from threading import Lock
from typing import Dict, Any, Deque, List

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from mut_calc import compute_profit_rates

try:
    from api.shared_data import NPC_PRICES, get_bazaar_prices, csv_data, DEFAULT_REQS
except ImportError:
    from shared_data import NPC_PRICES, get_bazaar_prices, csv_data, DEFAULT_REQS

app = FastAPI(title="Skyblock Mutations API")


def _allowed_origins_from_env() -> List[str]:
    raw_origins = os.getenv("ALLOWED_ORIGINS", "").strip()
    origins: List[str] = []
    if raw_origins:
        origins.extend([o.strip() for o in raw_origins.split(",") if o.strip()])
    else:
        origins.extend([
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ])

    frontend_url = os.getenv("FRONTEND_URL", "").strip()
    if frontend_url:
        origins.append(frontend_url)

    vercel_url = os.getenv("VERCEL_URL", "").strip()
    if vercel_url:
        origins.append(f"https://{vercel_url}")

    # Preserve order while de-duplicating.
    deduped: List[str] = []
    seen = set()
    for origin in origins:
        if origin not in seen:
            seen.add(origin)
            deduped.append(origin)
    return deduped


app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins_from_env(),
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "120"))
_rate_limit_buckets: Dict[str, Deque[float]] = defaultdict(deque)
_rate_limit_lock = Lock()


def _client_ip_from_request(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        # First IP in the chain is the original client.
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


@app.middleware("http")
async def _rate_limit_leaderboard(request: Request, call_next):
    if request.url.path == "/api/leaderboard":
        client_ip = _client_ip_from_request(request)
        now = time.monotonic()
        with _rate_limit_lock:
            bucket = _rate_limit_buckets[client_ip]
            cutoff = now - RATE_LIMIT_WINDOW_SECONDS
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Try again shortly."},
                    headers={
                        "Retry-After": str(RATE_LIMIT_WINDOW_SECONDS),
                        "X-RateLimit-Limit": str(RATE_LIMIT_MAX_REQUESTS),
                        "X-RateLimit-Window": str(RATE_LIMIT_WINDOW_SECONDS),
                    },
                )
            bucket.append(now)

    response = await call_next(request)
    if request.url.path == "/api/leaderboard":
        response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_MAX_REQUESTS)
        response.headers["X-RateLimit-Window"] = str(RATE_LIMIT_WINDOW_SECONDS)
    return response


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' data: https:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; "
        "connect-src 'self' https:; "
        "object-src 'none'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    # HSTS is ignored by browsers on HTTP; safe to set globally.
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Load manual data
MANUAL_DATA = {}
try:
    json_path = os.path.join(os.path.dirname(__file__), "..", "mutation_ingredient_list.json")
    with open(json_path, "r", encoding="utf-8") as f:
        MANUAL_DATA = json.load(f)
except Exception as e:
    print(f"Error loading manual data json: {e}")

DEFAULT_GROWTH_STAGE_BY_MUTATION = {
    "Magic Jellybean": 120,
    "All-in Aloe": 14,
}

DEFAULT_SPECIAL_MULTIPLIER_BY_MUTATION = {
    "Magic Jellybean": 10.0,
    "All-in Aloe": 1.8,
}

SPREAD_WARNING_RATIO = 2.0  # 100% difference => 2x between two prices.


def has_wide_spread(price_a: float, price_b: float) -> bool:
    if price_a <= 0 or price_b <= 0:
        return False
    hi = max(price_a, price_b)
    lo = min(price_a, price_b)
    return (hi / lo) >= SPREAD_WARNING_RATIO

@app.get("/api/ping")
def ping():
    return {"status": "ok"}

@app.get("/api/leaderboard")
def get_leaderboard(
    plots: int = Query(1, ge=1, le=3),
    fortune: int = Query(2500, ge=0),
    gh_upgrade: int = Query(9, ge=0, le=9),
    unique_crops: int = Query(12, ge=0, le=12),
    mode: str = Query("profit"),  # "profit", "smart", "target"
    setup_mode: str = Query("insta_buy"), # "insta_buy" or "buy_order"
    sell_mode: str = Query("sell_offer"), # "insta_sell" or "sell_offer"
    target_crop: str = Query(None),
    maxed_crops: str = Query(""),  # Comma-separated list
    mutation_chance: float = Query(0.25, gt=0.0, lt=1.0),
    harvest_mode: str = Query("full"),  # "full" or "custom_time"
    custom_time_hours: float = Query(24.0, gt=0.0),
    harvest_harbinger: bool = Query(False),
    infini_vacuum: bool = Query(False),
    dark_cacao: bool = Query(False),
    improved_harvest_boost: bool = Query(True),
    hypercharge_level: int = Query(0, ge=0, le=20),
    per_harvest_cost: float = Query(0.0, ge=0.0),
) -> Dict[str, Any]:
    # Normalize FastAPI Query defaults when function is called directly in tests/scripts.
    if not isinstance(maxed_crops, str):
        maxed_crops = ""
    if not isinstance(mutation_chance, (int, float)):
        mutation_chance = 0.25
    if not isinstance(harvest_mode, str):
        harvest_mode = "full"
    if not isinstance(custom_time_hours, (int, float)):
        custom_time_hours = 24.0
    if not isinstance(hypercharge_level, int):
        hypercharge_level = 0
    if not isinstance(per_harvest_cost, (int, float)):
        per_harvest_cost = 0.0
    
    # Load Data
    bazaar_data = get_bazaar_prices()
    
    reader = csv.DictReader(io.StringIO(csv_data))
    raw_crop_cols = [c.strip() for c in reader.fieldnames if c.strip() not in ['Mutation/Drops', 'Base_Limit', 'Crop Fortune type', 'If u figure it out...']]
    
    # Parse maxed crops
    maxed_list = [c.strip() for c in maxed_crops.split(",") if c.strip()]
    missing_crops = [crop for crop in DEFAULT_REQS.keys() if crop not in maxed_list]
    
    # Cycle Time Math
    base_cycle_hours = 4.0
    gh_reduction = (gh_upgrade / 9.0) * 0.25
    unique_reduction = (unique_crops / 12.0) * 0.30
    cycle_time_hours = base_cycle_hours * (1.0 - gh_reduction - unique_reduction)
    
    # Additive Base (1.0) + Microchip (0.6) = 1.6
    # GH Upgrades scales to +0.20, Unique Crops scales to +0.36 max (Total +0.56)
    gh_buff = (gh_upgrade / 9.0) * 0.20
    unique_buff = (unique_crops / 12.0) * 0.36
    additive_base = 1.6 + gh_buff + unique_buff
    
    # Buff fortune model:
    # Harvest Harbinger (+50) is unaffected by Hypercharge.
    # InfiniVacuum (+200) and Dark Cacao (+30) are affected by Hypercharge.
    affected_multiplier = 1.0 + (max(0, min(20, hypercharge_level)) / 20.0)
    unaffected_bonus = 50.0 if harvest_harbinger else 0.0
    affected_bonus_base = (200.0 if infini_vacuum else 0.0) + (30.0 if dark_cacao else 0.0)
    total_bonus = unaffected_bonus + (affected_bonus_base * affected_multiplier)
    effective_fortune = fortune + total_bonus

    wart_buff = 1.3 if improved_harvest_boost else 1.0
    fortune_mult = ((effective_fortune / 100) + 1)
    
    calc_mult = additive_base * wart_buff * fortune_mult
    
    leaderboard_data = []
    
    def get_item_price(item: str, is_buying: bool, mode_str: str):
        if item in NPC_PRICES:
            return NPC_PRICES[item]
        market = bazaar_data.get(item, {"buyPrice": 0, "sellPrice": 0})
        if is_buying:
            if mode_str == "insta_buy":
                return market.get('buyPrice', market.get('sellPrice', 0))
            else: # buy_order
                return market.get('sellPrice', market.get('buyPrice', 0))
        else:
            if mode_str == "insta_sell":
                return market.get('sellPrice', market.get('buyPrice', 0))
            else: # sell_offer
                return market.get('buyPrice', market.get('sellPrice', 0))

    def finite_or_none(value: Any) -> float | None:
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            return float(value)
        return None

    def finite_or_zero(value: Any) -> float:
        finite = finite_or_none(value)
        return finite if finite is not None else 0.0
                
    for row in reader:
        cleaned_row = {k.strip(): v for k, v in row.items()}
        mut_name = cleaned_row.get('Mutation/Drops', '')
        
        if mut_name not in MANUAL_DATA: 
            continue
            
        m_data = MANUAL_DATA[mut_name]
        base_limit = m_data.get("count", 1)
        limit = base_limit * plots
        ingredients = m_data.get("ingredients", {})
        mutation_chance_effective = float(m_data.get("mutation_chance_override", mutation_chance))
        
        # 1. Setup Cost
        opt_cost = 0
        ing_warning = False
        ingredient_costs = []
        
        for ing, qty_per_plot in ingredients.items():
            total_qty = qty_per_plot * plots
            cost_per_ing = get_item_price(ing, True, setup_mode)
            total_cost = total_qty * cost_per_ing
            opt_cost += total_cost
            ingredient_costs.append({
                "name": ing,
                "amount": total_qty,
                "unit_price": cost_per_ing,
                "total_cost": total_cost
            })
            
            # Warning logic if spread is bad
            ing_market = bazaar_data.get(ing, {"buyPrice": 0, "sellPrice": 0})
            if has_wide_spread(ing_market.get('buyPrice', 0), ing_market.get('sellPrice', 0)):
                ing_warning = True

        # Fetch Prices for Mutation itself
        mut_sell_price_value = get_item_price(mut_name, False, sell_mode)
        market_data = bazaar_data.get(mut_name, {"buyPrice": 0, "sellPrice": 0})
        mut_warning = False
        if has_wide_spread(market_data.get('buyPrice', 0), market_data.get('sellPrice', 0)):
            mut_warning = True
            
        # 2. Return per Batch (One Harvest)
        expected_drops_value = 0
        
        # Growth stage and special multiplier can be overridden per mutation in mutation_ingredient_list.json
        growth_stages = max(0, int(m_data.get("growth_stages", DEFAULT_GROWTH_STAGE_BY_MUTATION.get(mut_name, 30))))
        special_mult = float(m_data.get("special_multiplier", DEFAULT_SPECIAL_MULTIPLIER_BY_MUTATION.get(mut_name, 1.0)))
        effective_special_mult = float(m_data.get("effective_special_multiplier", special_mult))
        spawn_fill_fraction = 1.0
        if "mutation_chance_override" in m_data:
            spawn_fill_fraction = 1.0 - ((1.0 - mutation_chance_effective) ** growth_stages)
        effective_limit = limit * spawn_fill_fraction
            
        estimated_time = growth_stages * cycle_time_hours
        
        yields = []
        
        for crop_col in raw_crop_cols:
            raw_val = cleaned_row.get(crop_col, "0.0")
            base_drop = float(raw_val) if raw_val and raw_val.strip() else 0.0
            
            if base_drop > 0:
                full_drops = base_drop * effective_limit * calc_mult
                
                expected_drops = (full_drops * effective_special_mult)
                bd_display = base_drop
                sm_display = effective_special_mult
                    
                crop_price = get_item_price(crop_col, False, sell_mode)
                if crop_col == "Red Mushroom " or crop_col == "Brown Mushroom": crop_price = 10
                expected_drops_value += expected_drops * crop_price
                
                display_name = "Mushroom" if (crop_col == "Red Mushroom " or crop_col == "Brown Mushroom") else crop_col
                
                # Merge mushroom drops visually if multiple
                existing = next((item for item in yields if item["name"] == display_name), None)
                if existing:
                    existing["amount"] += expected_drops
                    existing["total_value"] += expected_drops * crop_price
                else:
                    yields.append({
                        "name": display_name,
                        "amount": expected_drops,
                        "unit_price": crop_price,
                        "total_value": expected_drops * crop_price,
                        "math": {
                            "base": bd_display,
                            "limit": effective_limit,
                            "gh_buff": gh_buff,
                            "unique_buff": unique_buff,
                            "wart_buff": wart_buff,
                            "fortune": fortune_mult,
                            "special": sm_display
                        }
                    })
                
        expected_mut_drops = effective_limit
        expected_mut_val = expected_mut_drops * mut_sell_price_value
        total_cycle_revenue = expected_drops_value + expected_mut_val
        
        if expected_mut_drops > 0:
            yields.append({
                "name": mut_name,
                "amount": expected_mut_drops,
                "unit_price": mut_sell_price_value,
                "total_value": expected_mut_val,
                "math": {
                    "base": 1.0,
                    "limit": effective_limit,
                    "gh_buff": 0.0,
                    "unique_buff": 0.0,
                    "wart_buff": 1.0,
                    "fortune": 1.0,
                    "special": 1.0
                }
            })
        
        crop_yields_by_name = {y["name"]: y["amount"] for y in yields if y["name"] in DEFAULT_REQS}
        smart_progress = {}
        for req_crop in missing_crops:
            req_amt = DEFAULT_REQS.get(req_crop, 0)
            if req_amt <= 0:
                continue
            progress_pct = (crop_yields_by_name.get(req_crop, 0) / req_amt) * 100.0
            if progress_pct > 0:
                smart_progress[req_crop] = progress_pct

        # 3. Profit metrics
        profit_batch = total_cycle_revenue - opt_cost

        # Growth-stage mapping from product requirements:
        # growth_stages is cycles AFTER spawn until harvestable, so g = growth_stages exactly.
        try:
            # Include harvest-time multiplier in v so renewal model v_net captures conditional bonuses.
            harvest_value_with_multiplier = mut_sell_price_value * effective_special_mult
            profit_models = compute_profit_rates({
                "m": plots,
                "x": int(base_limit),
                "p": mutation_chance_effective,
                "tau": cycle_time_hours,
                "g": growth_stages,
                "v": harvest_value_with_multiplier,
                "per_harvest_cost": per_harvest_cost,
            })
        except ValueError as exc:
            # Keep API resilient per mutation and surface validation context in warnings.
            profit_models = {
                "tau_hours": cycle_time_hours,
                "p": mutation_chance_effective,
                "g": float(growth_stages),
                "N": None,
                "cycles_per_harvest_per_spot": None,
                "hours_per_harvest_per_spot": None,
                "harvests_per_cycle": None,
                "harvests_per_hour": None,
                "profit_per_cycle": None,
                "profit_per_hour": None,
                "v_net": None,
                "warnings": [f"profit model error: {exc}"],
            }
        profit_per_cycle = finite_or_zero(profit_models.get("profit_per_cycle"))
        profit_per_hour = finite_or_zero(profit_models.get("profit_per_hour"))
        hourly_profit_selected = finite_or_none(profit_models.get("profit_per_hour"))

        payback_hours_ready = (opt_cost / hourly_profit_selected) if (hourly_profit_selected is not None and hourly_profit_selected > 0) else None
        
        # 4. Scoring Logic
        score = 0
        if mode == "profit":
            score = profit_batch
        elif mode == "target" and target_crop:
            if target_crop == "Mushroom":
                score = (float(cleaned_row.get("Red Mushroom ", 0)) + float(cleaned_row.get("Brown Mushroom", 0))) * effective_limit * calc_mult * effective_special_mult
            else:
                score = float(cleaned_row.get(target_crop, 0)) * effective_limit * calc_mult * effective_special_mult
            
        elif mode == "smart":
            score = sum(smart_progress.values())
            if score <= 0:
                continue
        elif mode == "hourly":
            score = hourly_profit_selected if hourly_profit_selected is not None else float("-inf")
            
        breakdown = {
            "base_limit": base_limit,
            "ingredients": ingredient_costs,
            "yields": yields,
            "total_setup_cost": opt_cost,
            "total_revenue": total_cycle_revenue,
            "growth_stages": growth_stages,
            "estimated_time_hours": estimated_time
        }
            
        leaderboard_data.append({
            "mutationName": mut_name,
            "score": score,
            "profit": profit_batch,
            "profit_per_cycle": profit_per_cycle,
            "profit_per_hour": profit_per_hour,
            "opt_cost": opt_cost,
            "revenue": total_cycle_revenue,
            "warning": mut_warning or ing_warning,
            "mut_price": mut_sell_price_value,
            "limit": limit,
            "smart_progress": smart_progress,
            "hourly": {
                "mutation_chance": mutation_chance_effective,
                "profit_per_hour_selected": hourly_profit_selected,
                "tau_hours": profit_models.get("tau_hours"),
                "p": profit_models.get("p"),
                "g": profit_models.get("g"),
                "N": profit_models.get("N"),
                "cycles_per_harvest_per_spot": profit_models.get("cycles_per_harvest_per_spot"),
                "hours_per_harvest_per_spot": profit_models.get("hours_per_harvest_per_spot"),
                "harvests_per_cycle": profit_models.get("harvests_per_cycle"),
                "harvests_per_hour": profit_models.get("harvests_per_hour"),
                "profit_per_cycle": profit_models.get("profit_per_cycle"),
                "profit_per_hour": profit_models.get("profit_per_hour"),
                "warnings": profit_models.get("warnings", []),
                "payback_hours_ready": payback_hours_ready,
                # Legacy fields retained for backward compatibility:
                "harvest_mode": harvest_mode,
                "custom_time_hours": custom_time_hours if harvest_mode == "custom_time" else None,
                "harvest_time_hours": None,
                "completed_cycles": None,
                "expected_mutations": None,
                "expected_revenue": None,
                "expected_profit": None,
                "expected_profit_per_hour": hourly_profit_selected,
            },
            "profit_models": profit_models,
            "breakdown": breakdown
        })

    leaderboard_data.sort(key=lambda x: x["score"], reverse=True)

    return {
        "leaderboard": leaderboard_data,
        "metadata": {
            "cycle_time_hours": cycle_time_hours,
            "missing_crops": missing_crops,
            "fortune_breakdown": {
                "base_fortune": fortune,
                "effective_fortune": effective_fortune,
                "bonus_total": total_bonus,
                "harvest_harbinger": harvest_harbinger,
                "infini_vacuum": infini_vacuum,
                "dark_cacao": dark_cacao,
                "hypercharge_level": hypercharge_level,
                "affected_multiplier": affected_multiplier,
            },
        }
    }
