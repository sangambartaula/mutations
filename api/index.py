from fastapi import FastAPI, Query
from typing import Dict, Any
from app import compute_optimized_plot_cost, RECIPES, NPC_PRICES, get_bazaar_prices, get_processed_data, MUTATION_LIMITS_1_PLOT
import math

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
    df, raw_crop_cols = get_processed_data()
    
    # Cycle Time Math
    base_cycle_hours = 4.0
    gh_reduction = (gh_upgrade / 9.0) * 0.25
    unique_reduction = (unique_crops / 12.0) * 0.30
    cycle_time_hours = base_cycle_hours * (1.0 - gh_reduction - unique_reduction)
    
    SPAWN_CHANCE = 0.25
    BATCH_LIFESPAN_HOURS = 120.0
    total_cycles_per_batch = BATCH_LIFESPAN_HOURS / cycle_time_hours
    
    leaderboard_data = []
    
    for index, row in df.iterrows():
        mut_name = row['Mutation/Drops']
        if mut_name == 'Made by Zigzagbrain' or mut_name not in RECIPES: 
            continue
            
        limit = row['Base_Limit'] * plots
        ingredients = RECIPES.get(mut_name, {})
        ing_prices = {}
        for item in ingredients:
            if item in NPC_PRICES:
                ing_prices[item] = NPC_PRICES[item]
            elif item in bazaar_data:
                ing_prices[item] = bazaar_data[item].get('sellPrice', 0)
                
        # Run Mathematical Optimizer logic
        opt_counts = compute_optimized_plot_cost(mut_name, tuple(sorted(ing_prices.items())))
        opt_cost = 0
        for item, count in opt_counts.items():
            price = ing_prices.get(item, 0)
            if price == 0 and item in bazaar_data:
                price = bazaar_data[item].get('sellPrice', 0)
            opt_cost += price * (count * plots)
            
        # Hardcode manual overrides for Blastberry-radius crops
        # Blastberry destroys a 3x3 area (9 tiles). So a limit of 84 doesn't need 84 Blastberries, it needs ceil(84/9) = 10.
        if mut_name == 'Shellfruit':
            # 1 Blastberry + 1 Turtellini per 9 crops
            blast_price = bazaar_data.get('Blastberry', {}).get('sellPrice', 0)
            turt_price = bazaar_data.get('Turtlellini', {}).get('sellPrice', 0)
            real_cost_per_plot = (10 * blast_price) + (10 * turt_price)
            opt_cost = real_cost_per_plot * plots
            
        if mut_name == 'Startlevine':
            # 4 Blastberry + 4 Cheesebite per 9 crops is impossible, actually Startlevine just needs 4 Blastberry per plant directly? 
            # Or if it's radius based, let's just stick to the greedy optimizer unless specifically instructed otherwise.
            pass
            
        # Expected Value
        expected_cycle_value = 0
        calc_mult = (2.16 * 1.3) * ((fortune / 100) + 1)
        for crop_col in raw_crop_cols:
            base_drop = row[crop_col]
            if base_drop > 0:
                full_drops = base_drop * limit * calc_mult
                
                # Apply special mechanics
                if mut_name == 'All-in Aloe':
                    # Reddit Analysis: Expected multiplier per cycle is ~1.8x factoring in reset risks and time to reach stage 13
                    expected_drops = (full_drops * 1.8) * SPAWN_CHANCE
                elif mut_name == 'Magic Jellybean':
                    # Takes 120 stages (120 cycles) to get 10x drops. Average per cycle = 10/120 = 0.083x
                    expected_drops = (full_drops * (10.0 / 120.0)) * SPAWN_CHANCE
                else:
                    expected_drops = full_drops * SPAWN_CHANCE
                    
                crop_price = NPC_PRICES.get(crop_col, 0)
                if crop_col == "Red Mushroom " or crop_col == "Brown Mushroom": crop_price = 10
                expected_cycle_value += expected_drops * crop_price
                
        market_data = bazaar_data.get(mut_name, {"buyPrice": 0, "sellPrice": 0})
        expected_mut_val = limit * market_data.get('sellPrice', 0) * SPAWN_CHANCE
        expected_cycle_value += expected_mut_val
        
        # Batch = 1 Harvest Cycle
        # Destructive crops destroy their specific ingredients during mutation
        # So we MUST deduct the optimal layout setup cost from every single cycle!
        DESTRUCTIVE_CROPS = ['Devourer', 'Shellfruit', 'Zombud', 'Chloronite', 'Fleshtrap']
        
        cycles_in_lifespan = 120.0 / cycle_time_hours
        amortized_cost_per_cycle = opt_cost / max(1, cycles_in_lifespan)
        
        if mut_name in DESTRUCTIVE_CROPS:
            profit_batch = expected_cycle_value - opt_cost
        else:
            profit_batch = expected_cycle_value - amortized_cost_per_cycle
            
        profit_hour = profit_batch / cycle_time_hours
        
        leaderboard_data.append({
            "mutation": mut_name,
            "profit_per_hour": profit_hour,
            "profit_per_batch": profit_batch,
            "setup_cost": opt_cost,
            "cycle_time_h": cycle_time_hours
        })
        
    # Sort by Most Profitable
    leaderboard_data.sort(key=lambda x: x["profit_per_batch"], reverse=True)
    
    return {
        "cycle_time_hours": cycle_time_hours,
        "total_cycles_per_batch": total_cycles_per_batch,
        "leaderboard": leaderboard_data
    }
