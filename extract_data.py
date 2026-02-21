import inspect
import textwrap

import app

with open("api/shared_data.py", "w") as f:
    f.write("import requests\n\n")
    f.write(f"MUSHROOM_KEY = {repr(app.MUSHROOM_KEY)}\n\n")
    f.write(f"MUTATION_IDS = {repr(app.MUTATION_IDS)}\n\n")
    f.write(f"MUTATION_LIMITS_1_PLOT = {repr(app.MUTATION_LIMITS_1_PLOT)}\n\n")
    f.write(f"NPC_PRICES = {repr(app.NPC_PRICES)}\n\n")
    f.write(f"RECIPES = {repr(app.RECIPES)}\n\n")
    f.write("csv_data = \"\"\"" + app.csv_data + "\"\"\"\n\n")
    
    # Write the get_bazaar_prices function
    source = inspect.getsource(app.get_bazaar_prices)
    # remove the @st.cache_data decorator
    source = "\n".join([line for line in source.split("\n") if not line.strip().startswith("@st.cache_data")])
    f.write(source + "\n")
