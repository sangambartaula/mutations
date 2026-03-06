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
DEFAULT_METRIC_SPAWN_CHANCE = 0.25
LONELILY_METRIC_SPAWN_CHANCE = 0.0045
CHIP_LEVEL_CAP_BY_RARITY: Dict[str, int] = {
    "rare": 10,
    "epic": 15,
    "legendary": 20,
}
HYPERCHARGE_BONUS_PER_LEVEL: Dict[str, float] = {
    "rare": 0.03,
    "epic": 0.04,
    "legendary": 0.05,
}
EVERGREEN_BONUS_PER_LEVEL: Dict[str, float] = {
    "rare": 0.02,
    "epic": 0.025,
    "legendary": 0.03,
}
OVERDRIVE_BONUS_PER_LEVEL: Dict[str, float] = {
    "rare": 5.0,
    "epic": 6.0,
    "legendary": 7.0,
}


def normalized_chip_rarity(value: Any, default: str = "legendary") -> str:
    if not isinstance(value, str):
        return default
    rarity = value.strip().lower()
    if rarity in CHIP_LEVEL_CAP_BY_RARITY:
        return rarity
    return default


def clamp_chip_level(value: Any, *, rarity: str, default: int) -> int:
    max_level = CHIP_LEVEL_CAP_BY_RARITY[rarity]
    if isinstance(value, bool) or not isinstance(value, int):
        return max(0, min(max_level, default))
    return max(0, min(max_level, value))


def canonical_crop_name(name: str) -> str:
    cleaned = name.strip()
    if cleaned in {"Red Mushroom", "Brown Mushroom", "Mushroom"}:
        return "Mushroom"
    return cleaned


def has_wide_spread(price_a: float, price_b: float) -> bool:
    if price_a <= 0 or price_b <= 0:
        return False
    hi = max(price_a, price_b)
    lo = min(price_a, price_b)
    return (hi / lo) >= SPREAD_WARNING_RATIO


def metric_spawn_chance_for_mutation(mutation_name: str) -> float:
    if mutation_name == "Lonelily":
        return LONELILY_METRIC_SPAWN_CHANCE
    return DEFAULT_METRIC_SPAWN_CHANCE


def build_expected_cycle_profit_model(
    *,
    profit_per_harvest: float,
    spawn_chance: float,
    growth_stages: int,
    cycle_time_hours: float,
    batch_size: int,
) -> Dict[str, Any]:
    warnings: List[str] = []

    if not math.isfinite(profit_per_harvest):
        profit_per_harvest = 0.0
        warnings.append("Non-finite profit detected; expected-cycle profit metrics were reset to 0.")

    if not math.isfinite(spawn_chance) or spawn_chance <= 0.0:
        warnings.append("Non-positive spawn chance; expected-cycle metrics were reset to 0.")
        return {
            "tau_hours": max(0.0, cycle_time_hours if math.isfinite(cycle_time_hours) else 0.0),
            "p": 0.0,
            "g": float(growth_stages),
            "N": float(max(0, batch_size)),
            "expected_spawn_cycles": None,
            "expected_cycles": None,
            "expected_hours": None,
            "cycles_per_harvest_per_spot": None,
            "hours_per_harvest_per_spot": None,
            "harvests_per_cycle": None,
            "harvests_per_hour": None,
            "profit_per_cycle": None,
            "profit_per_hour": None,
            "v_net": profit_per_harvest,
            "warnings": warnings,
        }

    safe_cycle_time = cycle_time_hours if math.isfinite(cycle_time_hours) and cycle_time_hours > 0 else 0.0
    if safe_cycle_time == 0.0:
        warnings.append("Non-positive cycle time; hourly metrics were reset to 0.")

    expected_spawn_cycles = 1.0 / spawn_chance
    expected_cycles = expected_spawn_cycles + float(max(0, growth_stages))
    expected_hours = expected_cycles * safe_cycle_time if safe_cycle_time > 0.0 else None
    harvests_per_cycle = (1.0 / expected_cycles) if expected_cycles > 0.0 else None
    harvests_per_hour = (1.0 / expected_hours) if expected_hours and expected_hours > 0.0 else None
    profit_per_cycle = (profit_per_harvest / expected_cycles) if expected_cycles > 0.0 else None
    profit_per_hour = (profit_per_harvest / expected_hours) if expected_hours and expected_hours > 0.0 else None

    return {
        "tau_hours": safe_cycle_time,
        "p": float(spawn_chance),
        "g": float(growth_stages),
        "N": float(max(0, batch_size)),
        "expected_spawn_cycles": expected_spawn_cycles,
        "expected_cycles": expected_cycles,
        "expected_hours": expected_hours,
        "cycles_per_harvest_per_spot": expected_cycles,
        "hours_per_harvest_per_spot": expected_hours,
        "harvests_per_cycle": harvests_per_cycle,
        "harvests_per_hour": harvests_per_hour,
        "profit_per_cycle": profit_per_cycle,
        "profit_per_hour": profit_per_hour,
        "v_net": profit_per_harvest,
        "warnings": warnings,
    }


def build_warning_messages(mutation_name: str, market_warning: bool) -> List[str]:
    messages: List[str] = []
    if market_warning:
        messages.append("Market spreads are wide right now. Double check your buy and sell strategy before placing large orders.")
    if mutation_name == "Devourer":
        messages.append("Devourer can spread into nearby crops and destroy them if you do not isolate it.")
    if mutation_name == "Magic Jellybean":
        messages.append("Magic Jellybean has 120 growth stages and is best harvested fully grown so spawn wait is not wasted.")
    if mutation_name == "All-in Aloe":
        messages.append("All-in Aloe is evaluated at Stage 14. Its raw multiplier there is 60x, but the calculator uses the reset-adjusted expected multiplier of 9.37x.")
    return messages


@app.get("/api/ping")
def ping():
    return {"status": "ok"}

@app.get("/api/leaderboard")
def get_leaderboard(
    plots: int = Query(1, ge=1, le=3),
    fortune: int = Query(2500, ge=0),
    gh_upgrade: int | None = Query(None, ge=0, le=9),
    gh_yield_upgrade: int | None = Query(None, ge=0, le=9),
    gh_speed_upgrade: int | None = Query(None, ge=0, le=9),
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
    hypercharge_level: int | None = Query(None, ge=0, le=20),
    hypercharge_rarity: str = Query("legendary"),
    evergreen_chip_level: int | None = Query(None, ge=0, le=20),
    evergreen_chip_rarity: str = Query("legendary"),
    overdrive_chip_level: int | None = Query(None, ge=0, le=20),
    overdrive_chip_rarity: str = Query("legendary"),
    overdrive_crop: str | None = Query(None),
    per_harvest_cost: float = Query(0.0, ge=0.0),
) -> Dict[str, Any]:
    # Normalize FastAPI Query defaults when function is called directly in tests/scripts.
    def normalized_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            return default
        return max(minimum, min(maximum, value))

    if not isinstance(maxed_crops, str):
        maxed_crops = ""
    if not isinstance(mutation_chance, (int, float)):
        mutation_chance = 0.25
    if not isinstance(harvest_mode, str):
        harvest_mode = "full"
    if not isinstance(custom_time_hours, (int, float)):
        custom_time_hours = 24.0
    hypercharge_rarity = normalized_chip_rarity(hypercharge_rarity)
    evergreen_chip_rarity = normalized_chip_rarity(evergreen_chip_rarity)
    overdrive_chip_rarity = normalized_chip_rarity(overdrive_chip_rarity)
    hypercharge_level = clamp_chip_level(hypercharge_level, rarity=hypercharge_rarity, default=0)
    evergreen_chip_level = clamp_chip_level(evergreen_chip_level, rarity=evergreen_chip_rarity, default=20)
    overdrive_chip_level = clamp_chip_level(overdrive_chip_level, rarity=overdrive_chip_rarity, default=0)
    legacy_gh_upgrade = normalized_int(gh_upgrade, default=9, minimum=0, maximum=9)
    gh_yield_upgrade = normalized_int(gh_yield_upgrade, default=legacy_gh_upgrade, minimum=0, maximum=9)
    gh_speed_upgrade = normalized_int(gh_speed_upgrade, default=legacy_gh_upgrade, minimum=0, maximum=9)
    unique_crops = normalized_int(unique_crops, default=12, minimum=0, maximum=12)
    if not isinstance(per_harvest_cost, (int, float)):
        per_harvest_cost = 0.0
    normalized_overdrive_crop = canonical_crop_name(overdrive_crop) if isinstance(overdrive_crop, str) and overdrive_crop.strip() else None
    
    # Load Data
    bazaar_data = get_bazaar_prices()
    
    reader = csv.DictReader(io.StringIO(csv_data))
    raw_crop_cols = [c.strip() for c in reader.fieldnames if c.strip() not in ['Mutation/Drops', 'Base_Limit', 'Crop Fortune type', 'If u figure it out...']]
    
    # Parse maxed crops
    maxed_list = [c.strip() for c in maxed_crops.split(",") if c.strip()]
    missing_crops = [crop for crop in DEFAULT_REQS.keys() if crop not in maxed_list]
    
    # Cycle Time Math
    base_cycle_hours = 4.0
    gh_speed_reduction = (gh_speed_upgrade / 9.0) * 0.25
    unique_reduction = (unique_crops / 12.0) * 0.30
    cycle_time_hours = base_cycle_hours * (1.0 - gh_speed_reduction - unique_reduction)
    
    # Additive base yield is modeled as:
    # Base (1.0) + Evergreen Chip (up to +0.60) + Greenhouse Yield (up to +0.20)
    # + Unique Crops (up to +0.36).
    evergreen_buff = evergreen_chip_level * EVERGREEN_BONUS_PER_LEVEL[evergreen_chip_rarity]
    gh_buff = (gh_yield_upgrade / 9.0) * 0.20
    unique_buff = (unique_crops / 12.0) * 0.36
    additive_base = 1.0 + evergreen_buff + gh_buff + unique_buff
    
    # Buff fortune model:
    # Harvest Harbinger (+50) is unaffected by Hypercharge.
    # InfiniVacuum (+200) and Dark Cacao (+30) are affected by Hypercharge.
    affected_multiplier = 1.0 + (hypercharge_level * HYPERCHARGE_BONUS_PER_LEVEL[hypercharge_rarity])
    unaffected_bonus = 50.0 if harvest_harbinger else 0.0
    affected_bonus_base = (200.0 if infini_vacuum else 0.0) + (30.0 if dark_cacao else 0.0)
    total_bonus = unaffected_bonus + (affected_bonus_base * affected_multiplier)
    effective_fortune = fortune + total_bonus
    overdrive_bonus = overdrive_chip_level * OVERDRIVE_BONUS_PER_LEVEL[overdrive_chip_rarity]

    wart_buff = 1.3 if improved_harvest_boost else 1.0
    base_yield_mult = additive_base * wart_buff
    
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
            
        # Even instant-after-spawn mutations still need one garden cycle to realize value in practice.
        estimated_time = max(1, growth_stages) * cycle_time_hours
        
        yields = []
        
        for crop_col in raw_crop_cols:
            raw_val = cleaned_row.get(crop_col, "0.0")
            base_drop = float(raw_val) if raw_val and raw_val.strip() else 0.0
            
            if base_drop > 0:
                canonical_crop = canonical_crop_name(crop_col)
                crop_overdrive_bonus = overdrive_bonus if normalized_overdrive_crop and canonical_crop == normalized_overdrive_crop else 0.0
                crop_fortune_mult = (((effective_fortune + crop_overdrive_bonus) / 100) + 1)
                full_drops = base_drop * effective_limit * base_yield_mult * crop_fortune_mult
                
                expected_drops = (full_drops * effective_special_mult)
                bd_display = base_drop
                sm_display = effective_special_mult
                    
                crop_price = get_item_price(crop_col, False, sell_mode)
                if crop_col in {"Red Mushroom", "Red Mushroom ", "Brown Mushroom"}:
                    crop_price = 10
                expected_drops_value += expected_drops * crop_price
                
                display_name = "Mushroom" if crop_col in {"Red Mushroom", "Red Mushroom ", "Brown Mushroom"} else crop_col
                
                # Merge mushroom drops visually if multiple
                existing = next((item for item in yields if item["name"] == display_name), None)
                if existing:
                    existing["amount"] += expected_drops
                    existing["total_value"] += expected_drops * crop_price
                    if existing.get("math"):
                        existing["math"]["base"] += bd_display
                else:
                    yields.append({
                        "name": display_name,
                        "amount": expected_drops,
                        "unit_price": crop_price,
                        "total_value": expected_drops * crop_price,
                        "math": {
                            "base": bd_display,
                            "limit": effective_limit,
                            "evergreen_buff": evergreen_buff,
                            "gh_buff": gh_buff,
                            "unique_buff": unique_buff,
                            "wart_buff": wart_buff,
                            "fortune": crop_fortune_mult,
                            "overdrive_bonus": crop_overdrive_bonus,
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
                    "evergreen_buff": 0.0,
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

        metric_spawn_chance = metric_spawn_chance_for_mutation(mut_name)
        profit_models = build_expected_cycle_profit_model(
            profit_per_harvest=profit_batch,
            spawn_chance=metric_spawn_chance,
            growth_stages=growth_stages,
            cycle_time_hours=cycle_time_hours,
            batch_size=limit,
        )
        profit_per_growth_cycle = finite_or_none(profit_models.get("profit_per_cycle"))
        profit_per_hour = finite_or_zero(profit_models.get("profit_per_hour"))
        hourly_profit_selected = finite_or_none(profit_models.get("profit_per_hour"))
        warning_messages = build_warning_messages(mut_name, mut_warning or ing_warning)

        payback_hours_ready = (opt_cost / hourly_profit_selected) if (hourly_profit_selected is not None and hourly_profit_selected > 0) else None
        
        # 4. Scoring Logic
        score = 0
        if mode == "profit":
            score = profit_batch
        elif mode == "target" and target_crop:
            score = next((item["amount"] for item in yields if item["name"] == target_crop), 0.0)
            
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
            "profit_per_growth_cycle": profit_per_growth_cycle,
            "profit_per_hour": profit_per_hour,
            "opt_cost": opt_cost,
            "revenue": total_cycle_revenue,
            "warning": len(warning_messages) > 0,
            "warning_messages": warning_messages,
            "mut_price": mut_sell_price_value,
            "limit": limit,
            "smart_progress": smart_progress,
            "hourly": {
                "mutation_chance": metric_spawn_chance,
                "profit_per_hour_selected": hourly_profit_selected,
                "tau_hours": profit_models.get("tau_hours"),
                "p": profit_models.get("p"),
                "g": profit_models.get("g"),
                "N": profit_models.get("N"),
                "expected_spawn_cycles": profit_models.get("expected_spawn_cycles"),
                "expected_cycles": profit_models.get("expected_cycles"),
                "expected_hours": profit_models.get("expected_hours"),
                "cycles_per_harvest_per_spot": profit_models.get("cycles_per_harvest_per_spot"),
                "hours_per_harvest_per_spot": profit_models.get("hours_per_harvest_per_spot"),
                "harvests_per_cycle": profit_models.get("harvests_per_cycle"),
                "harvests_per_hour": profit_models.get("harvests_per_hour"),
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
                "hypercharge_rarity": hypercharge_rarity,
                "affected_multiplier": affected_multiplier,
            },
            "yield_breakdown": {
                "base_multiplier": 1.0,
                "evergreen_chip_level": evergreen_chip_level,
                "evergreen_chip_rarity": evergreen_chip_rarity,
                "evergreen_bonus": evergreen_buff,
                "greenhouse_yield_upgrade": gh_yield_upgrade,
                "greenhouse_yield_bonus": gh_buff,
                "unique_crops": unique_crops,
                "unique_crop_bonus": unique_buff,
                "wart_multiplier": wart_buff,
                "overdrive_chip_level": overdrive_chip_level,
                "overdrive_chip_rarity": overdrive_chip_rarity,
                "overdrive_crop": normalized_overdrive_crop,
                "overdrive_bonus": overdrive_bonus,
            },
            "speed_breakdown": {
                "greenhouse_speed_upgrade": gh_speed_upgrade,
                "greenhouse_speed_reduction": gh_speed_reduction,
                "unique_speed_reduction": unique_reduction,
            },
        }
    }
