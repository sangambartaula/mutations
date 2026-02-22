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
    maxed_crops: str = Query("")  # Comma-separated list
) -> Dict[str, Any]:
    
    # Load Data
    bazaar_data = get_bazaar_prices()
    
    reader = csv.DictReader(io.StringIO(csv_data))
    raw_crop_cols = [c.strip() for c in reader.fieldnames if c.strip() not in ['Mutation/Drops', 'Base_Limit', 'Crop Fortune type', 'If u figure it out...']]
    
    # Parse maxed crops
    maxed_list = [c.strip() for c in maxed_crops.split(",") if c.strip()]
    active_reqs = {crop: DEFAULT_REQS.get(crop, 20_200_000) for crop in raw_crop_cols if crop not in maxed_list}
    if "Mushroom" in maxed_list:
        if "Red Mushroom " in active_reqs: del active_reqs["Red Mushroom "]
        if "Brown Mushroom" in active_reqs: del active_reqs["Brown Mushroom"]
    
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
            if ing_market.get('sellPrice', 0) > 0 and (ing_market.get('buyPrice', 0) / ing_market.get('sellPrice', 1)) > 2.0:
                ing_warning = True

        # Fetch Prices for Mutation itself
        mut_sell_price_value = get_item_price(mut_name, False, sell_mode)
        market_data = bazaar_data.get(mut_name, {"buyPrice": 0, "sellPrice": 0})
        mut_warning = False
        if market_data.get('sellPrice', 0) > 0 and (market_data.get('buyPrice', 0) / market_data.get('sellPrice', 1)) > 2.0:
            mut_warning = True
            
        # 2. Return per Batch (One Harvest)
        expected_drops_value = 0
        
        # Calculate dynamic growth stages & multipliers
        growth_stages = 30
        special_mult = 1.0
        
        if mut_name == 'Magic Jellybean':
            growth_stages = 120
            special_mult = 10.0
        elif mut_name == 'All-in Aloe':
            growth_stages = 14 # Optimal mathematical stage to harvest before it likely resets
            special_mult = 1.8
            
        estimated_time = growth_stages * cycle_time_hours
        
        yields = []
        
        for crop_col in raw_crop_cols:
            raw_val = cleaned_row.get(crop_col, "0.0")
            base_drop = float(raw_val) if raw_val and raw_val.strip() else 0.0
            
            if base_drop > 0:
                full_drops = base_drop * limit * calc_mult
                
                # Apply special mechanics
                if mut_name == 'Devourer':
                    expected_drops = 1 * limit
                    bd_display = 1.0
                    sm_display = 1.0
                else:
                    expected_drops = (full_drops * special_mult)
                    bd_display = base_drop
                    sm_display = special_mult
                    
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
                            "additive_yield": additive_base,
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
                    "additive_yield": 1.0,
                    "wart_buff": 1.0,
                    "fortune": 1.0,
                    "special": 1.0
                }
            })
        
        # 3. Simple Math
        profit_batch = total_cycle_revenue - opt_cost
        
        # 4. Scoring Logic
        score = 0
        if mode == "profit":
            score = profit_batch
        elif mode == "target" and target_crop:
            if target_crop == "Mushroom":
                score = (float(cleaned_row.get("Red Mushroom ", 0)) + float(cleaned_row.get("Brown Mushroom", 0))) * limit * calc_mult * special_mult
            else:
                score = float(cleaned_row.get(target_crop, 0)) * limit * calc_mult * special_mult
            
        elif mode == "smart":
            smart_score = 0
            for req_crop, req_amt in active_reqs.items():
                drop_rate = float(cleaned_row.get(req_crop, 0)) * special_mult
                if drop_rate > 0:
                    # Weight by the fraction of the requirement this drop fulfills
                    weight = 1.0 / req_amt if req_amt > 0 else 0
                    smart_score += drop_rate * weight
            # Multiply percentage progress by limit, calc_mult
            score = smart_score * limit * calc_mult * 10000000 # Scaling factor for readable display score
            
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
            "opt_cost": opt_cost,
            "revenue": total_cycle_revenue,
            "warning": mut_warning or ing_warning,
            "mut_price": mut_sell_price_value,
            "limit": limit,
            "breakdown": breakdown
        })

    leaderboard_data.sort(key=lambda x: x["score"], reverse=True)

    return {
        "leaderboard": leaderboard_data,
        "metadata": {
            "cycle_time_hours": cycle_time_hours
        }
    }
