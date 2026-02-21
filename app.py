import streamlit as st
import pandas as pd
import io
import json
import os
import requests
import time

# ---------------------------------------------------------
# 1. CONFIGURATION & MAPPING
# ---------------------------------------------------------
USER_DATA_FILE = "user_data.json"
CACHE_FILE = "max_drops_cache_v5.json"

# Mappings
MUSHROOM_KEY = "Mushroom" 

# Hypixel Bazaar IDs
MUTATION_IDS = {
    'All-in Aloe': 'ALL_IN_ALOE',
    'Ashwreath': 'ASHWREATH',
    'Blastberry': 'BLASTBERRY',
    'Cheesebite': 'CHEESEBITE',
    'Chloronite': 'CHLORONITE',
    'Chocoberry': 'CHOCOBERRY',
    'Choconut': 'CHOCONUT',
    'Chorus Fruit': 'CHORUS_FRUIT',
    'Cindershade': 'CINDERSHADE',
    'Coalroot': 'COALROOT',
    'Creambloom': 'CREAMBLOOM',
    'Devourer': 'DEVOURER',
    'Do-not-eat-shroom': 'DO_NOT_EAT_SHROOM',
    'Duskbloom': 'DUSKBLOOM',
    'Dustgrain': 'DUSTGRAIN',
    'Fleshtrap': 'FLESHTRAP',
    'Glasscorn': 'GLASSCORN',
    'Gloomgourd': 'GLOOMGOURD',
    'Godseed': 'GODSEED',
    'Jerryflower': 'JERRYFLOWER', 
    'Lonelily': 'LONELILY',
    'Magic Jellybean': 'MAGIC_JELLYBEAN',
    'Noctilume': 'NOCTILUME',
    'Phantomleaf': 'PHANTOMLEAF',
    'PlantBoy Advance': 'PLANTBOY_ADVANCE',
    'Puffercloud': 'PUFFERCLOUD',
    'Scourroot': 'SCOURROOT',
    'Shadevine': 'SHADEVINE',
    'Shellfruit': 'SHELLFRUIT',
    'Snoozling': 'SNOOZLING',
    'Soggybud': 'SOGGYBUD',
    'Startlevine': 'STARTLEVINE',
    'Stoplight Petal': 'STOPLIGHT_PETAL',
    'Thornshade': 'THORNSHADE',
    'Thunderling': 'THUNDERLING',
    'Timestalk': 'TIMESTALK',
    'Turtlellini': 'TURTLELLINI',
    'Veilshroom': 'VEILSHROOM',
    'Witherbloom': 'WITHERBLOOM',
    'Zombud': 'ZOMBUD',
    # Ingredients
    'Fermento': 'FERMENTO',
    'Dead Bush': 'DEAD_BUSH',
    'Fire': 'FIRE' 
}

# Base limits for 1 Plot (from SkyMutations.eu optimal layouts)
MUTATION_LIMITS_1_PLOT = {
    'PlantBoy Advance': 4, 'Stoplight Petal': 4, 'Phantomleaf': 16, 'All-in Aloe': 16,
    'Ashwreath': 52, 'Blastberry': 16, 'Cheesebite': 16, 'Chloronite': 16,
    'Chocoberry': 16, 'Choconut': 52, 'Chorus Fruit': 16, 'Cindershade': 16,
    'Coalroot': 16, 'Creambloom': 16, 'Devourer': 16, 'Do-not-eat-shroom': 16,
    'Duskbloom': 16, 'Dustgrain': 52, 'Glasscorn': 9, 'Fleshtrap': 16,
    'Jerryflower': 1, 'Godseed': 4, 'Lonelily': 25, 'Gloomgourd': 72,
    'Magic Jellybean': 16, 'Noctilume': 9, 'Puffercloud': 11, 'Scourroot': 52,
    'Shellfruit': 84, 'Shadevine': 52, 'Thornshade': 16, 'Snoozling': 4,
    'Soggybud': 16, 'Startlevine': 16, 'Thunderling': 13, 'Timestalk': 16,
    'Turtlellini': 16, 'Veilshroom': 52, 'Witherbloom': 16, 'Zombud': 16
}

# Physical sizes of mutations/ingredients (default 1x1)
CROP_SIZES = {
    'Noctilume': 2, 'PlantBoy Advance': 2, 'Glasscorn': 2,
    'Snoozling': 3, 'Godseed': 3,
}

# ---------------------------------------------------------
# GREENHOUSE LAYOUT OPTIMIZER
# ---------------------------------------------------------
def _get_neighbors(r, c, gs=10):
    """Get 8 neighbors (Chebyshev distance 1) within grid."""
    return [(r+dr, c+dc) for dr in [-1,0,1] for dc in [-1,0,1]
            if (dr or dc) and 0 <= r+dr < gs and 0 <= c+dc < gs]

@st.cache_data(ttl=3600)
def compute_optimized_plot_cost(mutation_name, _ingredient_prices_tuple):
    """
    Compute optimized ingredient totals for a full greenhouse plot (10x10).
    Uses greedy layout optimization: starts with all tiles as mutations, 
    iteratively converts the most strategically valuable tiles to ingredients.
    Expensive ingredients are placed in high-sharing positions first.
    
    Returns: dict {ingredient_name: total_tiles_needed}
    """
    ingredient_prices = dict(_ingredient_prices_tuple)
    recipe = RECIPES.get(mutation_name, {})
    limit = MUTATION_LIMITS_1_PLOT.get(mutation_name, 16)
    gs = 10
    
    total_needed = sum(recipe.values())
    if total_needed == 0:
        return {}
    
    blocked = {(0, 0)}
    all_tiles = set((r, c) for r in range(gs) for c in range(gs)) - blocked
    n_to_convert = len(all_tiles) - limit
    
    if n_to_convert <= 0:
        return {k: v * limit for k, v in recipe.items()}
    
    # Precompute neighbors
    nbrs = {t: set((nr, nc) for nr, nc in _get_neighbors(t[0], t[1], gs) if (nr, nc) in all_tiles)
            for t in all_tiles}
    
    sorted_ings = sorted([i for i in recipe if recipe[i] > 0],
                         key=lambda x: ingredient_prices.get(x, 0), reverse=True)
    
    is_mut = {t: True for t in all_tiles}
    ing_type = {}
    
    def get_needs(mt):
        n = dict(recipe)
        for nb in nbrs[mt]:
            if not is_mut[nb] and nb in ing_type:
                ig = ing_type[nb]
                if n.get(ig, 0) > 0: n[ig] -= 1
        return n
    
    def unmet_for(mt):
        return sum(max(0, v) for v in get_needs(mt).values())
    
    # Phase 1: Greedily convert mutations to ingredients
    for _ in range(n_to_convert):
        best_t, best_i, best_s = None, None, -1
        for cand in [t for t in all_tiles if is_mut[t]]:
            own = unmet_for(cand)
            for ing in sorted_ings:
                benefit = sum(1 for nb in nbrs[cand] if is_mut[nb] and get_needs(nb).get(ing, 0) > 0)
                score = own + benefit
                if score > best_s:
                    best_s, best_t, best_i = score, cand, ing
        if best_t is None: break
        is_mut[best_t] = False
        ing_type[best_t] = best_i
    
    # Phase 2: Improve ingredient type assignments
    def total_unmet():
        return sum(unmet_for(t) for t in all_tiles if is_mut[t])
    
    for _ in range(10):
        if total_unmet() == 0: break
        improved = False
        for tile in list(ing_type):
            curr = ing_type[tile]
            cu = total_unmet()
            for ni in sorted_ings:
                if ni == curr: continue
                ing_type[tile] = ni
                if total_unmet() < cu:
                    improved = True; break
                ing_type[tile] = curr
        if not improved: break
    
    counts = {}
    for t, i in ing_type.items():
        counts[i] = counts.get(i, 0) + 1
    return counts

# NPC Sell Prices (For Cost Calc)
NPC_PRICES = {
    'Wheat': 3, 'Carrot': 3, 'Potato': 3, 'Pumpkin': 10, 'Sugar Cane': 4,
    'Melon': 2, 'Cactus': 4, 'Cocoa Beans': 3, 'Nether Wart': 4,
    'Sunflower': 20, 'Moonflower': 20, 'Wild Rose': 20, 
    'Red Mushroom': 10, 'Brown Mushroom': 10,
    MUSHROOM_KEY: 10
}

# Growth Stages
GROWTH_STAGES = {
    'Ashwreath': 0, 'Choconut': 0, 'Dustgrain': 0, 'Gloomgourd': 0, 'Lonelily': 0,
    'Scourroot': 0, 'Shadevine': 0, 'Veilshroom': 0, 'Witherbloom': 0,
    'Shellfruit': 0, 'Turtlellini': 0,
    'Noctilume': 4,
    'Chocoberry': 6, 'Blastberry': 6,
    'Thornshade': 8, 'Do-not-eat-shroom': 8, 'Cindershade': 8, 'Coalroot': 8, 'Duskbloom': 8,
    'Cheesebite': 10, 'Chloronite': 10, 'Soggybud': 10, 'Jerryflower': 10,
    'Chorus Fruit': 12, 'PlantBoy Advance': 12, 'Startlevine': 12, 'Stoplight Petal': 12,
    'Fleshtrap': 14, 'Puffercloud': 14, 'Timestalk': 14,
    'Phantomleaf': 15,
    'Thunderling': 16, 'Zombud': 16,
    'Snoozling': 20,
    'All-in Aloe': 27,
    'Godseed': 40,
    'Magic Jellybean': 120,
    'Creambloom': 6, 
    'Glasscorn': 9,
    'Devourer': 16
}

# Recipes
RECIPES = {
    'Ashwreath': {'Nether Wart': 2, 'Fire': 2},
    'Choconut': {'Cocoa Beans': 2},
    'Dustgrain': {'Wheat': 2},
    'Gloomgourd': {'Pumpkin': 1, 'Melon': 1},
    'Lonelily': {'Adjacent Crops': 0}, 
    'Scourroot': {'Potato': 1, 'Carrot': 1},
    'Shadevine': {'Cactus': 2, 'Sugar Cane': 2},
    'Veilshroom': {'Red Mushroom': 1, 'Brown Mushroom': 1},
    'Witherbloom': {'Dead Bush': 8},
    
    'Chocoberry': {'Choconut': 6, 'Gloomgourd': 2},
    'Creambloom': {'Choconut': 8},
    'Cindershade': {'Ashwreath': 4, 'Witherbloom': 4},
    'Coalroot': {'Ashwreath': 5, 'Scourroot': 3},
    'Duskbloom': {'Moonflower': 2, 'Shadevine': 2, 'Sunflower': 2, 'Dustgrain': 2},
    
    'Thornshade': {'Wild Rose': 4, 'Veilshroom': 4},
    'Do-not-eat-shroom': {'Veilshroom': 4, 'Scourroot': 4},
    'Blastberry': {'Chocoberry': 5, 'Ashwreath': 3},
    'Cheesebite': {'Creambloom': 4, 'Fermento': 4},
    'Chloronite': {'Coalroot': 6, 'Thornshade': 2},
    'Fleshtrap': {'Cindershade': 4, 'Lonelily': 4},
    'Magic Jellybean': {'Sugar Cane': 5, 'Duskbloom': 3},
    'Noctilume': {'Duskbloom': 6, 'Lonelily': 6},
    'Snoozling': {'Creambloom': 4, 'Dustgrain': 3, 'Witherbloom': 3, 'Duskbloom': 3, 'Thornshade': 3},
    'Soggybud': {'Melon': 8},
    'Chorus Fruit': {'Chloronite': 5, 'Magic Jellybean': 3},
    'PlantBoy Advance': {'Snoozling': 6, 'Thunderling': 6},
    'Puffercloud': {'Snoozling': 2, 'Do-not-eat-shroom': 6},
    'Shellfruit': {'Turtlellini': 1, 'Blastberry': 1}, 
    'Startlevine': {'Blastberry': 4, 'Cheesebite': 4},
    'Stoplight Petal': {'Snoozling': 4, 'Noctilume': 4},
    'Thunderling': {'Soggybud': 5, 'Noctilume': 3},
    'Turtlellini': {'Soggybud': 4, 'Choconut': 4},
    'Zombud': {'Dead Bush': 4, 'Cindershade': 2, 'Fleshtrap': 2},
    'All-in Aloe': {'Magic Jellybean': 6, 'PlantBoy Advance': 2},
    'Glasscorn': {'Startlevine': 6, 'Chloronite': 6},
    'Godseed': {'Unique Crops': 12}, 
    'Jerryflower': {'Jerry Seed': 1},
    'Phantomleaf': {'Chorus Fruit': 4, 'Shellfruit': 4},
    'Timestalk': {'Stoplight Petal': 4, 'Chorus Fruit': 2, 'Shellfruit': 2},
    'Devourer': {'Puffercloud': 4, 'Zombud': 4}
}

DEFAULT_REQS = {
    'Wheat': 20_200_000, 'Carrot': 66_200_000, 'Potato': 66_200_000, 'Pumpkin': 20_200_000,
    'Sugar Cane': 40_400_000, 'Melon': 105_000_000, 'Cactus': 40_400_000,
    'Cocoa Beans': 64_560_000, 'Nether Wart': 20_200_000, 'Sunflower': 20_200_000,
    'Moonflower': 20_200_000, 'Wild Rose': 40_400_000, MUSHROOM_KEY: 20_200_000
}

# CSV Data
csv_data = """Mutation/Drops,Wheat,Carrot,Potato,Pumpkin,Sugar cane,Melon ,Cactus,Coco Bean,Nether Wart,Sunflower,Moonflower ,Wild Rose,Red Mushroom ,Brown Mushroom
Ashwreath,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,720.0,0.0,0.0,0.0,0.0,0.0
Choconut,0.0,0.0,0.0,0.0,0.0,0.0,0.0,400.0,0.0,0.0,0.0,0.0,0.0,0.0
Dustgrain,200.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
Gloomgourd,0.0,0.0,0.0,60.0,0.0,280.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
Lonelily,0.0,700.0,600.0,340.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
Scourroot,0.0,245.0,210.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
Shadevine,0.0,0.0,0.0,0.0,180.0,0.0,135.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
Veilshroom,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,66.0,66.0
Witherbloom,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,600.0,0.0,0.0
Chocoberry,0.0,0.0,0.0,170.0,0.0,1600.0,0.0,400.0,0.0,0.0,0.0,0.0,0.0,0.0
Cindershade,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,1200.0,0.0,0.0,800.0,0.0,0.0
Coalroot,0.0,1400.0,600.0,0.0,0.0,0.0,0.0,0.0,600.0,0.0,0.0,0.0,0.0,0.0
Creambloom,0.0,0.0,0.0,0.0,0.0,0.0,0.0,1600.0,0.0,0.0,0.0,0.0,0.0,0.0
Duskbloom,267.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,533.0,533.0,0.0,0.0,0.0
Thornshade,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,800.0,190.0,190.0
Blastberry,0.0,0.0,0.0,0.0,0.0,0.0,0.0,1200.0,1800.0,0.0,0.0,0.0,0.0,0.0
Cheesebite,0.0,0.0,0.0,0.0,800.0,0.0,600.0,0.0,0.0,0.0,0.0,0.0,190.0,190.0
Chloronite,0.0,700.0,600.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,400.0,95.0,95.0
Do-not-eat-shroom,0.0,1400.0,1200.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,380.0,380.0
Fleshtrap,0.0,1400.0,1200.0,680.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
Magic Jellybean,0.0,0.0,0.0,0.0,1200.0,0.0,0.0,0.0,0.0,600.0,600.0,0.0,0.0,0.0
Noctilume,0.0,0.0,0.0,0.0,0.0,0.0,1200.0,0.0,0.0,0.0,0.0,1600.0,0.0,0.0
Snoozling,0.0,0.0,0.0,0.0,800.0,0.0,600.0,0.0,0.0,800.0,800.0,0.0,0.0,0.0
Soggybud,0.0,0.0,0.0,0.0,0.0,3200.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
Chorus Fruit,0.0,1750.0,1500.0,0.0,2000.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
PlantBoy Advance,1200.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,1200.0,1200.0,0.0,0.0,0.0
Puffercloud,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,1400.0,1400.0,0.0,665.0,665.0
Shellfruit,0.0,0.0,0.0,0.0,0.0,4000.0,0.0,2000.0,0.0,0.0,0.0,0.0,0.0,0.0
Startlevine,0.0,0.0,0.0,0.0,2000.0,0.0,1500.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
Stoplight Petal,0.0,0.0,0.0,0.0,0.0,0.0,2400.0,0.0,0.0,0.0,0.0,3200.0,0.0,0.0
Thunderling,0.0,0.0,0.0,0.0,0.0,2400.0,900.0,0.0,0.0,0.0,0.0,2400.0,0.0,0.0
Turtlellini,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
Zombud,0.0,0.0,0.0,1190.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,2800.0,0.0,0.0
All-in Aloe,200.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,200.0,200.0,0.0,0.0,0.0
Devourer,0.0,0.0,0.0,1700.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,950.0,950.0
Glasscorn,0.0,0.0,4800.0,0.0,0.0,0.0,2400.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
Godseed,246.0,862.0,738.0,209.0,492.0,985.0,369.0,492.0,738.0,492.0,492.0,492.0,117.0,117.0
Jerryflower,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
Phantomleaf,0.0,5600.0,4800.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
Timestalk,0.0,0.0,0.0,0.0,4000.0,0.0,3000.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
Made by Zigzagbrain,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
"""

def format_big_number(num):
    if num >= 1_000_000: return f"{num/1_000_000:.2f}m"
    elif num >= 1_000: return f"{num/1_000:.1f}k"
    else: return f"{num:,.0f}"

# ---------------------------------------------------------
# 2. API & LOGIC
# ---------------------------------------------------------
def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_user_data(data):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f)

@st.cache_data(ttl=600)
def get_bazaar_prices():
    try:
        url = "https://api.hypixel.net/v2/skyblock/bazaar"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                products = data['products']
                prices = {}
                for name, pid in MUTATION_IDS.items():
                    if pid in products:
                        qs = products[pid].get('quick_status', {})
                        if qs:
                            prices[name] = {
                                "buyPrice": qs.get("buyPrice", 0), 
                                "sellPrice": qs.get("sellPrice", 0) 
                            }
                        else:
                             prices[name] = {"buyPrice": 0, "sellPrice": 0}
                return prices
    except Exception as e:
        pass
    return {}

def get_processed_data():
    df = pd.read_csv(io.StringIO(csv_data))
    df.columns = df.columns.str.strip()
    
    rename_map = {'Sugar cane': 'Sugar Cane', 'Coco Bean': 'Cocoa Beans'}
    df = df.rename(columns=rename_map)
    
    df['Base_Limit'] = df['Mutation/Drops'].map(MUTATION_LIMITS_1_PLOT).fillna(1).astype(int)
    
    raw_cols = [c for c in df.columns if c not in ['Mutation/Drops', 'Base_Limit', 'Crop Fortune type', 'If u figure it out...']]
    for crop in raw_cols:
        df[crop] = pd.to_numeric(df[crop], errors='coerce').fillna(0)
    return df, raw_cols

df, raw_crop_cols = get_processed_data()
user_prefs = load_user_data()
bazaar_data = get_bazaar_prices()

# ---------------------------------------------------------
# 3. STREAMLIT UI
# ---------------------------------------------------------
st.set_page_config(page_title="Skyblock Mutation Manager", page_icon="🌱", layout="wide")

st.markdown("""
<style>
    @keyframes fadeIn { 0% { opacity: 0; transform: translateY(10px); } 100% { opacity: 1; transform: translateY(0); } }
    div[data-testid="stMetric"] { background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .card-highlight { animation: fadeIn 0.6s ease-out; border-left: 5px solid #28a745; background: linear-gradient(to right, #e8f5e9, #ffffff); padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
    .card-title { color: #155724; font-size: 1.5em; font-weight: 700; margin-bottom: 5px; }
    .stat-badge { background-color: #c3e6cb; color: #155724; padding: 4px 8px; border-radius: 6px; font-weight: bold; font-size: 0.9em; }
    .recipe-row { padding: 10px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
    .cost-text { color: #666; font-size: 0.9em; font-style: italic; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. SIDEBAR
# ---------------------------------------------------------
st.sidebar.title("⚙️ Settings")
saved_plots = user_prefs.get("plots", 1)
plots = st.sidebar.select_slider("Number of Plots", options=[1, 2, 3], value=saved_plots)
saved_fortune = user_prefs.get("fortune", 2500)
fortune = st.sidebar.number_input("Farming Fortune", value=saved_fortune, step=50)

st.sidebar.markdown("---")
st.sidebar.subheader("Time & Upgrade Settings")
saved_gh_upg = user_prefs.get("gh_upgrade", 9)
gh_upgrade = st.sidebar.slider("Greenhouse Upgrade Level", 0, 9, saved_gh_upg, help="-25% cycle time at max")
saved_unique = user_prefs.get("unique_crops", 12)
unique_crops = st.sidebar.slider("Unique Crops Placed", 0, 12, saved_unique, help="-30% cycle time at max")

# Calculate Cycle Time
base_cycle_hours = 4.0
gh_reduction = (gh_upgrade / 9.0) * 0.25
unique_reduction = (unique_crops / 12.0) * 0.30
cycle_time_hours = base_cycle_hours * (1.0 - gh_reduction - unique_reduction)

# Standard spawn chance per cycle
SPAWN_CHANCE = 0.25
# 5 days (120 hours) lifespan
BATCH_LIFESPAN_HOURS = 120.0
total_cycles_per_batch = BATCH_LIFESPAN_HOURS / cycle_time_hours

# ---------------------------------------------------------
# 5. TABS
# ---------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📊 Optimizer", "📖 Recipes & Costs", "🏆 Profit Leaderboard"])

# =========================================================
# TAB 1: OPTIMIZER
# =========================================================
with tab1:
    st.sidebar.markdown("---")
    saved_mode = user_prefs.get("mode", "Best Overall Value (Smart)")
    mode_options = ["Best Overall Value (Smart)", "Optimize for ONE Crop"]
    mode_index = mode_options.index(saved_mode) if saved_mode in mode_options else 0
    mode = st.sidebar.radio("Optimization Mode", mode_options, index=mode_index)
    
    if fortune != saved_fortune or mode != saved_mode or plots != saved_plots or gh_upgrade != saved_gh_upg or unique_crops != saved_unique:
        user_prefs["fortune"] = fortune
        user_prefs["mode"] = mode
        user_prefs["plots"] = plots
        user_prefs["gh_upgrade"] = gh_upgrade
        user_prefs["unique_crops"] = unique_crops
        save_user_data(user_prefs)

    st.title("🏆 Crop Milestones")
    st.markdown("Toggle: <span style='color:green'>**Maxed**</span> vs <span style='color:#d9534f'>**Needed**</span>.", unsafe_allow_html=True)
    display_crops = ['Wheat', 'Carrot', 'Potato', 'Pumpkin', 'Sugar Cane', 'Melon', 'Cactus', 'Cocoa Beans', 'Nether Wart', 'Sunflower', 'Moonflower', 'Wild Rose', MUSHROOM_KEY]
    saved_status = user_prefs.get("maxed_crops", {})
    cols = st.columns(4)
    active_reqs = {}
    for i, crop in enumerate(display_crops):
        with cols[i % 4]:
            is_maxed = saved_status.get(crop, False)
            new_status = st.toggle(f"{'✅' if is_maxed else '⚡'} {crop}", value=is_maxed, key=f"t_{crop}")
            if new_status != is_maxed:
                saved_status[crop] = new_status
                user_prefs["maxed_crops"] = saved_status
                save_user_data(user_prefs)
                st.rerun()
            if not new_status:
                active_reqs[crop] = DEFAULT_REQS.get(crop, 20_200_000)

    st.divider()
    
    fixed_mult = 2.16 * 1.3
    fortune_mult = (fortune / 100) + 1
    final_mult = fixed_mult * fortune_mult
    results_list = []

    if mode == "Optimize for ONE Crop":
        target = st.selectbox("Select Target Crop", display_crops)
        best_yield = -1
        best_mut = None
        best_limit = 0
        for index, row in df.iterrows():
            mut_name = row['Mutation/Drops']
            if mut_name == 'Made by Zigzagbrain': continue
            limit = row['Base_Limit'] * plots
            base_drop = (row.get('Red Mushroom', 0) + row.get('Brown Mushroom', 0)) if target == MUSHROOM_KEY else row.get(target, 0)
            if base_drop > 0:
                total_yield = base_drop * limit * final_mult
                if total_yield > best_yield:
                    best_yield = total_yield
                    best_mut = mut_name
                    best_limit = limit
        if best_mut:
            st.markdown(f"<div class='card-highlight'><div class='card-title'>🎯 {best_mut}</div><div>Yield: <b>{format_big_number(best_yield)}</b> items (Limit: {best_limit})</div></div>", unsafe_allow_html=True)
    else:
        for index, row in df.iterrows():
            mut_name = row['Mutation/Drops']
            if mut_name == 'Made by Zigzagbrain': continue
            limit = row['Base_Limit'] * plots
            points_sum, distinct = 0, 0
            details = []
            crops_hit = []
            for crop, req in active_reqs.items():
                base_drop = (row.get('Red Mushroom', 0) + row.get('Brown Mushroom', 0)) if crop == MUSHROOM_KEY else row.get(crop, 0)
                if base_drop > 0:
                    distinct += 1
                    crops_hit.append(crop)
                    total = base_drop * limit * final_mult
                    points = (total / req) * 100
                    points_sum += points
                    details.append(f"{crop}: {format_big_number(total)} ({points:.2f}%)")
            if distinct > 0:
                score = points_sum * (1.0 + (0.2 * (distinct - 1)))
                results_list.append({"name": mut_name, "score": score, "limit": limit, "count": distinct, "crops": crops_hit, "details": details})
        
        results_list.sort(key=lambda x: x['score'], reverse=True)
        if results_list:
            winner = results_list[0]
            st.markdown(f"""
            <div class='card-highlight'>
                <div class='card-title'>{winner['name']}</div>
                <div>Covers <b>{winner['count']}</b> crops: {', '.join(winner['crops'])}</div>
                <div style='margin-top:10px'><span class='stat-badge'>Score: {winner['score']:.2f}</span> <span class='stat-badge'>Limit: {winner['limit']}</span></div>
            </div>""", unsafe_allow_html=True)
            d_cols = st.columns(3)
            for i, d in enumerate(winner['details']): d_cols[i % 3].metric(d.split(":")[0], d.split(":")[1])
            st.divider()
            st.write("### 🥈 Top Alternatives")
            for r in results_list[1:6]:
                with st.expander(f"{r['name']} (Score: {r['score']:.2f})"):
                    st.write(f"**Yields:** {', '.join(r['details'])}")

# =========================================================
# TAB 2: RECIPES & COSTS
# =========================================================
with tab2:
    st.header("📖 Mutation Recipes & Setup Costs")
    st.markdown("Costs calculated using **NPC Sell Prices** for common crops and **Bazaar Buy Offers** for rare items.")
    
    col_r1, col_r2 = st.columns([1, 2])
    with col_r1:
        selected_recipe_mut = st.selectbox("Select Mutation to view details", sorted(RECIPES.keys()))
        
    if selected_recipe_mut:
        ingredients = RECIPES.get(selected_recipe_mut, {})
        limit = MUTATION_LIMITS_1_PLOT.get(selected_recipe_mut, 16) * plots
        growth = GROWTH_STAGES.get(selected_recipe_mut, "?")
        
        market_data = bazaar_data.get(selected_recipe_mut, {"buyPrice": 0, "sellPrice": 0})
        current_val = market_data.get('buyPrice', 0)
        
        st.subheader(f"{selected_recipe_mut} (Growth Stage: {growth})")
        if current_val > 0:
            st.caption(f"Current Bazaar Insta-Buy Price: {current_val:,.1f} coins")
        
        unit_cost = 0
        ingredients_display = []
        for item, qty in ingredients.items():
            price = 0
            if item in NPC_PRICES:
                price = NPC_PRICES[item]
            elif item in bazaar_data:
                price = bazaar_data[item].get('sellPrice', 0)
            elif item in MUTATION_IDS and item in bazaar_data:
                price = bazaar_data[item].get('sellPrice', 0)
            
            item_total = price * qty
            unit_cost += item_total
            price_str = f"{item_total:,.0f} coins" if price > 0 else "Free/Hidden"
            # FIX: Use proper HTML tags, NO MARKDOWN
            ingredients_display.append(f"<b>{qty}x {item}</b> <span class='cost-text'>{price_str}</span>")
        
        total_setup_cost = unit_cost * limit

        # --- OPTIMIZED PLOT COST ---
        # Build ingredient prices dict for the optimizer
        ing_prices = {}
        for item in ingredients:
            if item in NPC_PRICES:
                ing_prices[item] = NPC_PRICES[item]
            elif item in bazaar_data:
                ing_prices[item] = bazaar_data[item].get('sellPrice', 0)
        
        # Compute optimized layout for 1 plot, then scale by plots
        opt_counts = compute_optimized_plot_cost(selected_recipe_mut, tuple(sorted(ing_prices.items())))
        
        # Calculate optimized cost
        opt_cost = 0
        opt_display = []
        for item, count in opt_counts.items():
            price = ing_prices.get(item, 0)
            if price == 0 and item in bazaar_data:
                price = bazaar_data[item].get('sellPrice', 0)
            total_for_item = count * plots
            item_cost = price * total_for_item
            opt_cost += item_cost
            price_str = f"{item_cost:,.0f} coins" if price > 0 else "Free/Hidden"
            opt_display.append(f"<b>{total_for_item}x {item}</b> <span class='cost-text'>{price_str}</span>")
        
        savings = total_setup_cost - opt_cost if total_setup_cost > 0 else 0
        savings_pct = (savings / total_setup_cost * 100) if total_setup_cost > 0 else 0

        # --- ESTIMATED RETURN (Per Cycle vs Per Batch) ---
        row = df[df['Mutation/Drops'] == selected_recipe_mut].iloc[0] if not df[df['Mutation/Drops'] == selected_recipe_mut].empty else None
        return_details = []
        expected_cycle_value = 0
        
        if row is not None:
            # 2.16 = base fortune mult? We scale drop value by spawn chance (0.25)
            calc_mult = (2.16 * 1.3) * ((fortune / 100) + 1)
            for crop_col in raw_crop_cols:
                base_drop = row[crop_col]
                if base_drop > 0:
                    # Total raw drops per harvest if it spawns
                    full_drops = base_drop * limit * calc_mult
                    
                    # Apply special mechanics per crop
                    if selected_recipe_mut == 'All-in Aloe':
                        # Reddit Analysis: Stage 13 is optimal, providing ~41x multiplier on drops
                        expected_drops = (full_drops * 41.0) * SPAWN_CHANCE
                    elif selected_recipe_mut == 'Magic Jellybean':
                        # Scales 1x per 12 stages up to 120 stages (10x drops at max)
                        expected_drops = (full_drops * 10.0) * SPAWN_CHANCE
                    else:
                        # Standard 25% spawn chance
                        expected_drops = full_drops * SPAWN_CHANCE
                    
                    crop_price = NPC_PRICES.get(crop_col, 0)
                    if crop_col == "Red Mushroom " or crop_col == "Brown Mushroom": crop_price = 10
                    
                    val = expected_drops * crop_price
                    expected_cycle_value += val
                    
                    return_details.append(f"~{format_big_number(expected_drops)} {crop_col} <span class='cost-text'>({format_big_number(val)} coins/cycle)</span>")
        
        mut_unit_price = market_data.get('sellPrice', 0)
        # Expected mutation drop value per cycle
        expected_mut_val = limit * mut_unit_price * SPAWN_CHANCE
        expected_cycle_value += expected_mut_val
        
        # Batch metrics
        batch_return_value = expected_cycle_value * total_cycles_per_batch
        profit_per_batch = batch_return_value - opt_cost
        profit_per_hour = profit_per_batch / BATCH_LIFESPAN_HOURS
        
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.markdown(f"""
            <div style="background: white; padding: 20px; border-radius: 10px; border: 1px solid #ddd;">
                <h4>🛒 Setup Cost</h4>
                <div style="margin-bottom:10px;">
                    <b>Per Plant:</b> {', '.join([f'{qty}x {item}' for item, qty in ingredients.items()])}
                </div>
                <div><b>Naive Cost (no overlap):</b> <span style="text-decoration: line-through; color: #999;">{format_big_number(total_setup_cost)} coins</span></div>
                <div style="margin-top:8px;">
                    <b>Optimized Plot Cost:</b>
                </div>
                <ul>{''.join([f'<li>{x}</li>' for x in opt_display])}</ul>
                <hr>
                <div style="font-size:1.1em;"><b style="color:#28a745;">Actual Cost: {format_big_number(opt_cost)} coins</b></div>
                <div style="margin-top:3px;"><span style="background:#c3e6cb; color:#155724; padding:2px 8px; border-radius:6px; font-size:0.85em; font-weight:bold;">Saves {savings_pct:.0f}% with overlap</span></div>
                <small>For {limit} placements ({plots} Plots) valid for 5 days</small>
            </div>
            """, unsafe_allow_html=True)
            
        with col_d2:
            st.markdown(f"""
            <div style="background: white; padding: 20px; border-radius: 10px; border: 1px solid #28a745;">
                <h4 style="color:#155724;">💰 Expected Return (Per {cycle_time_hours:.2f}h Cycle)</h4>
                <div style="margin-bottom:10px;">
                    <b>You get:</b> ~{limit * SPAWN_CHANCE:.1f}x {selected_recipe_mut} <span class='cost-text'>({format_big_number(expected_mut_val)} coins)</span>
                </div>
                <small style="color:red; font-weight:bold;">↳ Estimates factor in 25% drop chance</small>
                <ul style="margin-top:10px;">{''.join([f'<li>{x}</li>' for x in return_details])}</ul>
                <hr>
                <div style="font-size:1.2em;"><b>Expected Cycle Value: {format_big_number(expected_cycle_value)} coins</b></div>
                <small>With {fortune} Fortune | {total_cycles_per_batch:.1f} cycles in 5 days</small>
            </div>
            """, unsafe_allow_html=True)
            
        st.info(f"**Profit / Batch (5 Days):** {format_big_number(profit_per_batch)} coins | **Profit / Hour:** {format_big_number(profit_per_hour)} coins")

# =========================================================
# TAB 3: PROFIT LEADERBOARD
# =========================================================
with tab3:
    st.header("🏆 Profit Leaderboard")
    st.markdown("Sort all mutations by **Profit / Hour** or **Profit / Batch (5 Days)**.")
    
    if st.button("Calculate Leaderboard (Takes a few seconds)"):
        with st.spinner("Crunching numbers..."):
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
                
                # Optimized Cost
                opt_counts = compute_optimized_plot_cost(mut_name, tuple(sorted(ing_prices.items())))
                opt_cost = 0
                for item, count in opt_counts.items():
                    price = ing_prices.get(item, 0)
                    if price == 0 and item in bazaar_data:
                        price = bazaar_data[item].get('sellPrice', 0)
                    opt_cost += price * (count * plots)
                
                # Expected Cycle Value
                expected_cycle_value = 0
                calc_mult = (2.16 * 1.3) * ((fortune / 100) + 1)
                for crop_col in raw_crop_cols:
                    base_drop = row[crop_col]
                    if base_drop > 0:
                        full_drops = base_drop * limit * calc_mult
                        
                        # Apply special mechanics
                        if mut_name == 'All-in Aloe':
                            expected_drops = (full_drops * 41.0) * SPAWN_CHANCE
                        elif mut_name == 'Magic Jellybean':
                            expected_drops = (full_drops * 10.0) * SPAWN_CHANCE
                        else:
                            expected_drops = full_drops * SPAWN_CHANCE
                        crop_price = NPC_PRICES.get(crop_col, 0)
                        if crop_col == "Red Mushroom " or crop_col == "Brown Mushroom": crop_price = 10
                        expected_cycle_value += expected_drops * crop_price
                
                market_data = bazaar_data.get(mut_name, {"buyPrice": 0, "sellPrice": 0})
                expected_mut_val = limit * market_data.get('sellPrice', 0) * SPAWN_CHANCE
                expected_cycle_value += expected_mut_val
                
                batch_return = expected_cycle_value * total_cycles_per_batch
                profit_batch = batch_return - opt_cost
                profit_hour = profit_batch / BATCH_LIFESPAN_HOURS
                
                leaderboard_data.append({
                    "Mutation": mut_name,
                    "Profit / Hour": profit_hour,
                    "Profit / Batch": profit_batch,
                    "Setup Cost": opt_cost,
                    "Cycle Time (h)": cycle_time_hours
                })
                
            ldf = pd.DataFrame(leaderboard_data)
            # Format display
            def fm(x): return f"{x:,.0f}"
            st.dataframe(
                ldf.style.format({
                    "Profit / Hour": fm,
                    "Profit / Batch": fm,
                    "Setup Cost": fm,
                    "Cycle Time (h)": "{:.2f}"
                }),
                height=600,
                use_container_width=True
            )