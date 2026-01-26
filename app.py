import streamlit as st
import pandas as pd
import io
import json
import os
import time

# ---------------------------------------------------------
# 1. CONFIGURATION & MAPPING
# ---------------------------------------------------------
USER_DATA_FILE = "user_data.json"
CACHE_FILE = "max_drops_cache_v2.json" # Changed name to force refresh cache

# Combined Mushroom Logic
MUSHROOM_KEY = "Mushroom" 

# Base limits for 1 Plot
MUTATION_LIMITS_1_PLOT = {
    'PlantBoy Advance': 4, 'Stoplight Petal': 4, 'Phantomleaf': 16, 'All-in Aloe': 16,
    'Ashwreath': 16, 'Blastberry': 16, 'Cheesebite': 16, 'Chloronite': 16,
    'Chocoberry': 16, 'Choconut': 52, 'Chorus Fruit': 16, 'Cindershade': 16,
    'Coalroot': 16, 'Creambloom': 16, 'Devourer': 16, 'Do-not-eat-shroom': 16,
    'Duskbloom': 16, 'Dustgrain': 52, 'Glasscorn': 9, 'Fleshtrap': 16,
    'Jerryflower': 1, 'Godseed': 4, 'Lonelily': 25, 'Gloomgourd': 72,
    'Magic Jellybean': 16, 'Noctilume': 9, 'Puffercloud': 11, 'Scourroot': 52,
    'Shellfruit': 84, 'Shadevine': 52, 'Thornshade': 16, 'Snoozling': 4,
    'Soggybud': 16, 'Startlevine': 16, 'Thunderling': 13, 'Timestalk': 16,
    'Turtlellini': 16, 'Veilshroom': 52, 'Witherbloom': 16, 'Zombud': 16
}

# UPDATED Requirements with CLEAN names
DEFAULT_REQS = {
    'Wheat': 20_200_000,
    'Carrot': 66_200_000,
    'Potato': 66_200_000,
    'Pumpkin': 20_200_000,
    'Sugar Cane': 40_400_000,  # Fixed Name
    'Melon': 105_000_000,      # Fixed Space
    'Cactus': 40_400_000,
    'Cocoa Beans': 64_560_000, # Fixed Name
    'Nether Wart': 20_200_000,
    'Sunflower': 20_200_000,
    'Moonflower': 20_200_000,  # Fixed Space
    'Wild Rose': 40_400_000,
    MUSHROOM_KEY: 20_200_000
}

# Raw Data
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
# 2. PERSISTENCE & DATA LOADING
# ---------------------------------------------------------
def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_user_data(data):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f)

def get_processed_data():
    df = pd.read_csv(io.StringIO(csv_data))
    
    # 1. Clean Columns: Strip whitespace
    df.columns = df.columns.str.strip()
    
    # 2. Rename specific columns
    rename_map = {
        'Sugar cane': 'Sugar Cane',
        'Coco Bean': 'Cocoa Beans'
    }
    df = df.rename(columns=rename_map)
    
    # 3. Base Limits
    df['Base_Limit'] = df['Mutation/Drops'].map(MUTATION_LIMITS_1_PLOT).fillna(1).astype(int)
    
    # 4. Clean Numeric Data
    raw_cols = [c for c in df.columns if c not in ['Mutation/Drops', 'Base_Limit', 'Crop Fortune type', 'If u figure it out...']]
    for crop in raw_cols:
        df[crop] = pd.to_numeric(df[crop], errors='coerce').fillna(0)
        
    return df, raw_cols

df, raw_crop_cols = get_processed_data()
user_prefs = load_user_data()

# ---------------------------------------------------------
# 3. STREAMLIT UI & STYLING
# ---------------------------------------------------------
st.set_page_config(page_title="Skyblock Mutation Manager", page_icon="🌱", layout="wide")

# Custom CSS for Animations and Colors
st.markdown("""
<style>
    /* Fade In Animation */
    @keyframes fadeIn {
        0% { opacity: 0; transform: translateY(10px); }
        100% { opacity: 1; transform: translateY(0); }
    }
    
    /* Global Background tweaks (optional, keeps it clean) */
    .stApp {
        background: linear-gradient(to bottom right, #ffffff, #f8f9fa);
    }

    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        transition: transform 0.2s;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        border-color: #28a745;
    }

    /* Highlight Card for Winner */
    .card-highlight {
        animation: fadeIn 0.6s ease-out;
        border-left: 5px solid #28a745;
        background: linear-gradient(to right, #e8f5e9, #ffffff);
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }
    
    .card-title {
        color: #155724;
        font-size: 1.5em;
        font-weight: 700;
        margin-bottom: 5px;
    }
    
    .card-subtitle {
        color: #444;
        font-size: 1.0em;
        margin-bottom: 10px;
    }

    .stat-badge {
        background-color: #c3e6cb;
        color: #155724;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 0.9em;
    }
    
    /* Toggle Switch Styling override (subtle) */
    div[data-testid="stMarkdownContainer"] p {
        font-size: 1.05em;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. SIDEBAR SETTINGS
# ---------------------------------------------------------
st.sidebar.title("⚙️ Settings")

# Plot Selector
saved_plots = user_prefs.get("plots", 1)
plots = st.sidebar.select_slider("Number of Plots", options=[1, 2, 3], value=saved_plots)

# Fortune
saved_fortune = user_prefs.get("fortune", 2500)
fortune = st.sidebar.number_input("Farming Fortune", value=saved_fortune, step=50)

# Mode
saved_mode = user_prefs.get("mode", "Best Overall Value (Smart)")
mode_options = ["Best Overall Value (Smart)", "Optimize for ONE Crop"]
mode_index = 0
if saved_mode in mode_options:
    mode_index = mode_options.index(saved_mode)
mode = st.sidebar.radio("Optimization Mode", mode_options, index=mode_index)

# Save Logic
if fortune != saved_fortune or mode != saved_mode or plots != saved_plots:
    user_prefs["fortune"] = fortune
    user_prefs["mode"] = mode
    user_prefs["plots"] = plots
    save_user_data(user_prefs)

st.sidebar.markdown(f"**Configuration:**<br>Plots: `{plots}`<br>Fortune: `{fortune}`", unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. MILESTONE SELECTION
# ---------------------------------------------------------
st.title("🏆 Crop Milestones")
st.markdown("Toggle crops to update your needs. <span style='color:green'>**Green**</span> = Maxed (Ignored). <span style='color:#d9534f'>**Red**</span> = Needed.", unsafe_allow_html=True)

# Clean Display List
display_crops = ['Wheat', 'Carrot', 'Potato', 'Pumpkin', 'Sugar Cane', 'Melon', 'Cactus', 'Cocoa Beans', 'Nether Wart', 'Sunflower', 'Moonflower', 'Wild Rose', MUSHROOM_KEY]

saved_status = user_prefs.get("maxed_crops", {})
cols = st.columns(4)
active_reqs = {}

for i, crop in enumerate(display_crops):
    with cols[i % 4]:
        is_maxed = saved_status.get(crop, False)
        # Visual Emoji Logic
        label = f"✅ {crop}" if is_maxed else f"⚡ {crop}"
        
        new_status = st.toggle(label, value=is_maxed, key=f"toggle_{crop}")
        
        if new_status != is_maxed:
            saved_status[crop] = new_status
            user_prefs["maxed_crops"] = saved_status
            save_user_data(user_prefs)
            st.rerun() # Immediate refresh
            
        if not new_status:
            active_reqs[crop] = DEFAULT_REQS.get(crop, 20_200_000)

st.divider()

# ---------------------------------------------------------
# 6. CALCULATION ENGINE
# ---------------------------------------------------------
fixed_mult = 2.16 * 1.3
fortune_mult = (fortune / 100) + 1
final_mult = fixed_mult * fortune_mult

results_list = []

# --- MODE 1: OPTIMIZE FOR ONE CROP ---
if mode == "Optimize for ONE Crop":
    target = st.selectbox("Select Target Crop", display_crops)
    best_yield = -1
    best_mut = None
    best_limit = 0
    
    for index, row in df.iterrows():
        mut_name = row['Mutation/Drops']
        if mut_name == 'Made by Zigzagbrain': continue
        
        limit = row['Base_Limit'] * plots
        
        # Handle Mushroom split in DataFrame
        if target == MUSHROOM_KEY:
            base_drop = row.get('Red Mushroom', 0) + row.get('Brown Mushroom', 0)
        else:
            base_drop = row.get(target, 0)
             
        if base_drop > 0:
            total_yield = base_drop * limit * final_mult
            if total_yield > best_yield:
                best_yield = total_yield
                best_mut = mut_name
                best_limit = limit
    
    if best_mut:
        st.markdown(f"""
        <div class="card-highlight">
            <div class="card-title">🎯 {best_mut}</div>
            <div class="card-subtitle">Best source for <b>{target}</b></div>
            <div>Yield: <span class="stat-badge">{format_big_number(best_yield)}</span> items</div>
            <div>Limit: <b>{best_limit}</b> placed</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("No mutation found for this crop.")

# --- MODE 2: SMART ALGORITHM (Points + Diversity Bonus) ---
else:
    for index, row in df.iterrows():
        mut_name = row['Mutation/Drops']
        if mut_name == 'Made by Zigzagbrain': continue
        
        limit = row['Base_Limit'] * plots
        
        points_sum = 0
        distinct_crops_hit = 0
        details = []
        crops_hit_names = []
        
        for crop, req in active_reqs.items():
            # Get base drop logic
            base_drop = 0
            if crop == MUSHROOM_KEY:
                base_drop = row.get('Red Mushroom', 0) + row.get('Brown Mushroom', 0)
            else:
                base_drop = row.get(crop, 0)
            
            if base_drop > 0:
                distinct_crops_hit += 1
                crops_hit_names.append(crop)
                
                # Yield
                total_yield = base_drop * limit * final_mult
                
                # Points = % of milestone
                points = (total_yield / req) * 100
                points_sum += points
                
                details.append(f"{crop}: {format_big_number(total_yield)} ({points:.2f}%)")
        
        if distinct_crops_hit > 0:
            # ALGORITHM:
            # Score = Raw Points * Bonus Multiplier
            # Bonus = 1.0 + (0.2 * (extra_crops))
            bonus_mult = 1.0 + (0.2 * (distinct_crops_hit - 1))
            final_score = points_sum * bonus_mult
            
            results_list.append({
                "name": mut_name,
                "score": final_score,
                "raw_pts": points_sum,
                "count": distinct_crops_hit,
                "bonus": bonus_mult,
                "limit": limit,
                "details": details,
                "crops": crops_hit_names
            })

    # Sort Results
    results_list.sort(key=lambda x: x['score'], reverse=True)

    if not active_reqs:
        st.success("🎉 You have maxed everything! Select a manual crop mode if you want to farm for coins.")
    elif not results_list:
        st.warning("No mutations found for selected needs.")
    else:
        winner = results_list[0]
        
        st.subheader("🥇 Best Recommendation")
        
        # Pretty Card HTML
        st.markdown(f"""
        <div class="card-highlight">
            <div class="card-title">{winner['name']}</div>
            <div class="card-subtitle">
                Targets <b>{winner['count']}</b> needed crops: {', '.join(winner['crops'])}
            </div>
            <div style="display:flex; gap:15px; margin-top:10px;">
                <span class="stat-badge">Limit: {winner['limit']}</span>
                <span class="stat-badge">Score: {winner['score']:.2f}</span>
                <span class="stat-badge">Bonus: {winner['bonus']}x</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Metrics Grid
        st.write("**Est. Yields (Per Harvest):**")
        d_cols = st.columns(3)
        for i, d in enumerate(winner['details']):
            d_cols[i % 3].metric(label=d.split(":")[0], value=d.split(":")[1])

        # Alternatives Table
        st.divider()
        st.write("### 🥈 Top Alternatives")
        for r in results_list[1:6]:
            with st.expander(f"{r['name']} (Score: {r['score']:.2f})"):
                st.write(f"**Crops ({r['count']}):** {', '.join(r['crops'])}")
                st.write(f"**Yields:** {', '.join(r['details'])}")