import csv
import io
import math
import os
import json
from fastapi import FastAPI, Query
from typing import Dict, Any

try:
    from api.shared_data import NPC_PRICES, get_bazaar_prices, csv_data, DEFAULT_REQS
except ImportError:
    from shared_data import NPC_PRICES, get_bazaar_prices, csv_data, DEFAULT_REQS

app = FastAPI(title="Skyblock Mutations API")

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
    custom_time_hours: float = Query(24.0, gt=0.0)
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
    
    wart_buff = 1.3
    fortune_mult = ((fortune / 100) + 1)
    
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
        growth_stages = max(1, int(m_data.get("growth_stages", DEFAULT_GROWTH_STAGE_BY_MUTATION.get(mut_name, 30))))
        special_mult = float(m_data.get("special_multiplier", DEFAULT_SPECIAL_MULTIPLIER_BY_MUTATION.get(mut_name, 1.0)))
        effective_special_mult = float(m_data.get("effective_special_multiplier", special_mult))
            
        estimated_time = growth_stages * cycle_time_hours
        
        yields = []
        
        for crop_col in raw_crop_cols:
            raw_val = cleaned_row.get(crop_col, "0.0")
            base_drop = float(raw_val) if raw_val and raw_val.strip() else 0.0
            
            if base_drop > 0:
                full_drops = base_drop * limit * calc_mult
                
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
                            "limit": limit,
                            "gh_buff": gh_buff,
                            "unique_buff": unique_buff,
                            "wart_buff": wart_buff,
                            "fortune": fortune_mult,
                            "special": sm_display
                        }
                    })
                
        expected_mut_drops = limit
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
                    "limit": limit,
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

        # 3. Simple Math
        profit_batch = total_cycle_revenue - opt_cost
        profit_per_cycle = (profit_batch / estimated_time) if estimated_time > 0 else 0.0

        # Deterministic expected-value model for mutation-spawn profitability over time.
        if harvest_mode == "custom_time":
            harvest_time_hours = custom_time_hours
            completed_cycles = int(harvest_time_hours // cycle_time_hours) if cycle_time_hours > 0 else 0
        else:
            if base_limit > 1 and mutation_chance_effective < 1:
                t_cycles = math.log(1.0 / base_limit) / math.log(1.0 - mutation_chance_effective)
            else:
                t_cycles = 1.0
            harvest_time_hours = max(cycle_time_hours, t_cycles * cycle_time_hours)
            completed_cycles = int(harvest_time_hours // cycle_time_hours) if cycle_time_hours > 0 else 0

        expected_mutations_per_plot = base_limit * (1.0 - ((1.0 - mutation_chance_effective) ** completed_cycles))
        expected_total_mutations = plots * expected_mutations_per_plot
        expected_mutation_revenue = expected_total_mutations * mut_sell_price_value
        expected_profit = expected_mutation_revenue - opt_cost
        profit_per_hour = (expected_profit / harvest_time_hours) if harvest_time_hours > 0 else 0.0
        
        # 4. Scoring Logic
        score = 0
        if mode == "profit":
            score = profit_batch
        elif mode == "target" and target_crop:
            if target_crop == "Mushroom":
                score = (float(cleaned_row.get("Red Mushroom ", 0)) + float(cleaned_row.get("Brown Mushroom", 0))) * limit * calc_mult * effective_special_mult
            else:
                score = float(cleaned_row.get(target_crop, 0)) * limit * calc_mult * effective_special_mult
            
        elif mode == "smart":
            score = sum(smart_progress.values())
            if score <= 0:
                continue
        elif mode == "hourly":
            score = profit_per_hour
            
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
                "harvest_mode": harvest_mode,
                "custom_time_hours": custom_time_hours if harvest_mode == "custom_time" else None,
                "harvest_time_hours": harvest_time_hours,
                "completed_cycles": completed_cycles,
                "expected_mutations": expected_total_mutations,
                "expected_revenue": expected_mutation_revenue,
                "expected_profit": expected_profit
            },
            "breakdown": breakdown
        })

    leaderboard_data.sort(key=lambda x: x["score"], reverse=True)

    return {
        "leaderboard": leaderboard_data,
        "metadata": {
            "cycle_time_hours": cycle_time_hours,
            "missing_crops": missing_crops
        }
    }
