import csv
import io
import math
from fastapi import FastAPI, Query
from typing import Dict, Any
try:
    from api.shared_data import RECIPES, NPC_PRICES, get_bazaar_prices, MUTATION_LIMITS_1_PLOT, csv_data
except ImportError:
    from shared_data import RECIPES, NPC_PRICES, get_bazaar_prices, MUTATION_LIMITS_1_PLOT, csv_data

app = FastAPI(title="Skyblock Mutations API")

@app.get("/api/ping")
def ping():
    return {"status": "ok"}

@app.get("/api/leaderboard")
def get_leaderboard(
    plots: int = Query(1, ge=1, le=3),
    fortune: int = Query(2500, ge=0),
    gh_upgrade: int = Query(9, ge=0, le=9),
    unique_crops: int = Query(12, ge=0, le=12)
) -> Dict[str, Any]:
    
    # Load Data
    bazaar_data = get_bazaar_prices()
    
    reader = csv.DictReader(io.StringIO(csv_data))
    raw_crop_cols = [c.strip() for c in reader.fieldnames if c.strip() not in ['Mutation/Drops', 'Base_Limit', 'Crop Fortune type', 'If u figure it out...']]
    
    # We need to clean up keys slightly because CSV reader keys might retain trailing whitespace
    # we'll map original keys to cleaned columns during iteration if needed, but standardizing works
    # Actually, Pandas `strip()` logic in get_processed_data() was needed. Let's do it dynamically.
    
    # Cycle Time Math
    base_cycle_hours = 4.0
    gh_reduction = (gh_upgrade / 9.0) * 0.25
    unique_reduction = (unique_crops / 12.0) * 0.30
    cycle_time_hours = base_cycle_hours * (1.0 - gh_reduction - unique_reduction)
    
    SPAWN_CHANCE = 0.25
    BATCH_LIFESPAN_HOURS = 120.0
    total_cycles_per_batch = BATCH_LIFESPAN_HOURS / cycle_time_hours
    
    leaderboard_data = []
    
    for row in reader:
        # Strip all keys to replicate Pandas string stripping
        cleaned_row = {k.strip(): v for k, v in row.items()}
        mut_name = cleaned_row.get('Mutation/Drops', '')
        
        if mut_name == 'Made by Zigzagbrain' or mut_name not in RECIPES: 
            continue
            
        limit = MUTATION_LIMITS_1_PLOT.get(mut_name, 1) * plots
        ingredients = RECIPES.get(mut_name, {})
        ing_prices = {}
        for item in ingredients:
            if item in NPC_PRICES:
                ing_prices[item] = NPC_PRICES[item]
            elif item in bazaar_data:
                ing_prices[item] = bazaar_data[item].get('sellPrice', 0)
                
        # Fetch Prices and Implement Spread Warnings
        market_data = bazaar_data.get(mut_name, {"buyPrice": 0, "sellPrice": 0})
        mut_sell_price = market_data.get('sellPrice', 0)
        mut_buy_price = market_data.get('buyPrice', 0)
        
        mut_warning = False
        if mut_sell_price > 0 and (mut_buy_price / mut_sell_price) > 2.0:
            mut_warning = True  # Insta-buy is >100% higher than Insta-sell

        # 1. Simplified Setup Cost (Limit * Recipe * Buy Order)
        recipe = RECIPES.get(mut_name, {})
        opt_cost = 0
        ing_warning = False
        
        if mut_name == 'Shellfruit':
            # 16 Blastberry + 84 Turtlellinis (override)
            blast = bazaar_data.get('Blastberry', {"buyPrice": 0, "sellPrice": 0})
            turt = bazaar_data.get('Turtlellini', {"buyPrice": 0, "sellPrice": 0})
            
            opt_cost += (16 * blast.get('buyPrice', blast.get('sellPrice', 0))) * plots
            opt_cost += (84 * turt.get('buyPrice', turt.get('sellPrice', 0))) * plots
            
            if (blast.get('sellPrice', 0) > 0 and (blast.get('buyPrice', 0) / blast.get('sellPrice', 1)) > 2.0) or \
               (turt.get('sellPrice', 0) > 0 and (turt.get('buyPrice', 0) / turt.get('sellPrice', 1)) > 2.0):
                ing_warning = True
        else:
            for ing, count in recipe.items():
                if count > 0:
                    ing_market = bazaar_data.get(ing, {"buyPrice": 0, "sellPrice": 0})
                    ing_buy = ing_market.get('buyPrice', ing_market.get('sellPrice', 0))
                    opt_cost += (count * limit * ing_buy) * plots
                    
                    if ing_market.get('sellPrice', 0) > 0 and (ing_market.get('buyPrice', 0) / ing_market.get('sellPrice', 1)) > 2.0:
                        ing_warning = True
            
        # 2. Simplified Return per Batch (One Harvest)
        expected_drops_value = 0
        calc_mult = (2.16 * 1.3) * ((fortune / 100) + 1)
        
        for crop_col in raw_crop_cols:
            raw_val = cleaned_row.get(crop_col, "0.0")
            base_drop = float(raw_val) if raw_val and raw_val.strip() else 0.0
            
            if base_drop > 0:
                full_drops = base_drop * limit * calc_mult
                
                # Apply special mechanics
                if mut_name == 'All-in Aloe':
                    expected_drops = (full_drops * 1.8) * SPAWN_CHANCE
                elif mut_name == 'Magic Jellybean':
                    expected_drops = (full_drops * 10.0) * SPAWN_CHANCE
                elif mut_name == 'Devourer':
                    expected_drops = 1 * limit * SPAWN_CHANCE
                else:
                    expected_drops = full_drops * SPAWN_CHANCE
                    
                crop_price = NPC_PRICES.get(crop_col, 0)
                if crop_col == "Red Mushroom " or crop_col == "Brown Mushroom": crop_price = 10
                expected_drops_value += expected_drops * crop_price
                
        expected_mut_val = limit * mut_sell_price * SPAWN_CHANCE
        total_cycle_revenue = expected_drops_value + expected_mut_val
        
        # 3. Simple Math
        profit_batch = total_cycle_revenue - opt_cost
        profit_hour = profit_batch / cycle_time_hours
        
        leaderboard_data.append({
            "mutation": mut_name,
            "profit_per_hour": profit_hour,
            "profit_per_batch": profit_batch,
            "setup_cost": opt_cost,
            "cycle_time_h": cycle_time_hours,
            "mut_warning": mut_warning,
            "ing_warning": ing_warning
        })
        
    # Sort by Most Profitable
    leaderboard_data.sort(key=lambda x: x["profit_per_batch"], reverse=True)
    
    return {
        "cycle_time_hours": cycle_time_hours,
        "total_cycles_per_batch": total_cycles_per_batch,
        "leaderboard": leaderboard_data
    }
