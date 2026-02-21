import json
import re

with open("skymutations_logic.js", "r", encoding="utf-8") as f:
    js = f.read()

crops = ['PlantBoy Advance', 'Stoplight Petal', 'Phantomleaf', 'All-in Aloe',
    'Ashwreath', 'Blastberry', 'Cheesebite', 'Chloronite',
    'Chocoberry', 'Choconut', 'Chorus Fruit', 'Cindershade',
    'Coalroot', 'Creambloom', 'Devourer', 'Do-not-eat-shroom',
    'Duskbloom', 'Dustgrain', 'Glasscorn', 'Fleshtrap',
    'Jerryflower', 'Godseed', 'Lonelily', 'Gloomgourd',
    'Magic Jellybean', 'Noctilume', 'Puffercloud', 'Scourroot',
    'Shellfruit', 'Shadevine', 'Thornshade', 'Snoozling',
    'Soggybud', 'Startlevine', 'Thunderling', 'Timestalk',
    'Turtlellini', 'Veilshroom', 'Witherbloom', 'Zombud']

results = {}
for crop in crops:
    # Try looking for id:"Crop Name" or name:"Crop Name"
    idx = js.find(f'"{crop}"')
    if idx == -1:
        # maybe no quotes if it's an object key (unlikely with spaces)
        idx = js.find(crop)
    if idx != -1:
        # dump context
        ctx = js[max(0, idx-100) : min(len(js), idx+300)]
        results[crop] = ctx

with open("js_dump.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)
