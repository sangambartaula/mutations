import requests

MUSHROOM_KEY = 'Mushroom'

MUTATION_IDS = {'All-in Aloe': 'ALL_IN_ALOE', 'Ashwreath': 'ASHWREATH', 'Blastberry': 'BLASTBERRY', 'Cheesebite': 'CHEESEBITE', 'Chloronite': 'CHLORONITE', 'Chocoberry': 'CHOCOBERRY', 'Choconut': 'CHOCONUT', 'Chorus Fruit': 'CHORUS_FRUIT', 'Cindershade': 'CINDERSHADE', 'Coalroot': 'COALROOT', 'Creambloom': 'CREAMBLOOM', 'Devourer': 'DEVOURER', 'Do-not-eat-shroom': 'DO_NOT_EAT_SHROOM', 'Duskbloom': 'DUSKBLOOM', 'Dustgrain': 'DUSTGRAIN', 'Fleshtrap': 'FLESHTRAP', 'Glasscorn': 'GLASSCORN', 'Gloomgourd': 'GLOOMGOURD', 'Godseed': 'GODSEED', 'Jerryflower': 'JERRYFLOWER', 'Lonelily': 'LONELILY', 'Magic Jellybean': 'MAGIC_JELLYBEAN', 'Noctilume': 'NOCTILUME', 'Phantomleaf': 'PHANTOMLEAF', 'PlantBoy Advance': 'PLANTBOY_ADVANCE', 'Puffercloud': 'PUFFERCLOUD', 'Scourroot': 'SCOURROOT', 'Shadevine': 'SHADEVINE', 'Shellfruit': 'SHELLFRUIT', 'Snoozling': 'SNOOZLING', 'Soggybud': 'SOGGYBUD', 'Startlevine': 'STARTLEVINE', 'Stoplight Petal': 'STOPLIGHT_PETAL', 'Thornshade': 'THORNSHADE', 'Thunderling': 'THUNDERLING', 'Timestalk': 'TIMESTALK', 'TURTLELLINI': 'TURTLELLINI', 'Veilshroom': 'VEILSHROOM', 'Witherbloom': 'WITHERBLOOM', 'Zombud': 'ZOMBUD', 'Fermento': 'FERMENTO', 'Dead Bush': 'DEAD_BUSH', 'Fire': 'FIRE'}

MUTATION_LIMITS_1_PLOT = {'PlantBoy Advance': 4, 'Stoplight Petal': 4, 'Phantomleaf': 16, 'All-in Aloe': 16, 'Ashwreath': 52, 'Blastberry': 16, 'Cheesebite': 16, 'Chloronite': 16, 'Chocoberry': 16, 'Choconut': 52, 'Chorus Fruit': 16, 'Cindershade': 16, 'Coalroot': 16, 'Creambloom': 16, 'Devourer': 16, 'Do-not-eat-shroom': 16, 'Duskbloom': 16, 'Dustgrain': 52, 'Glasscorn': 9, 'Fleshtrap': 16, 'Jerryflower': 1, 'Godseed': 4, 'Lonelily': 25, 'Gloomgourd': 72, 'Magic Jellybean': 16, 'Noctilume': 9, 'Puffercloud': 11, 'Scourroot': 52, 'Shellfruit': 84, 'Shadevine': 52, 'Thornshade': 16, 'Snoozling': 4, 'Soggybud': 16, 'Startlevine': 16, 'Thunderling': 13, 'Timestalk': 16, 'TURTLELLINI': 16, 'Veilshroom': 52, 'Witherbloom': 16, 'Zombud': 16}

NPC_PRICES = {'Wheat': 6, 'Carrot': 3, 'Potato': 3, 'Pumpkin': 10, 'Sugar cane': 4, 'Melon': 2.0, 'Cactus': 4, 'Coco Bean': 3, 'Nether Wart': 4, 'Sunflower': 4, 'Moonflower': 4, 'Wild Rose': 4, 'Red Mushroom': 10, 'Brown Mushroom': 10, 'Mushroom': 10}

RECIPES = {'Ashwreath': {'Nether Wart': 2, 'Fire': 2}, 'Choconut': {'Coco Bean': 2}, 'Dustgrain': {'Wheat': 2}, 'Gloomgourd': {'Pumpkin': 1, 'Melon': 1}, 'Lonelily': {'Adjacent Crops': 0}, 'Scourroot': {'Potato': 1, 'Carrot': 1}, 'Shadevine': {'Cactus': 2, 'Sugar cane': 2}, 'Veilshroom': {'Red Mushroom': 1, 'Brown Mushroom': 1}, 'Witherbloom': {'Dead Bush': 8}, 'Chocoberry': {'Choconut': 6, 'Gloomgourd': 2}, 'Creambloom': {'Choconut': 8}, 'Cindershade': {'Ashwreath': 4, 'Witherbloom': 4}, 'Coalroot': {'Ashwreath': 5, 'Scourroot': 3}, 'Duskbloom': {'Moonflower': 2, 'Shadevine': 2, 'Sunflower': 2, 'Dustgrain': 2}, 'Thornshade': {'Wild Rose': 4, 'Veilshroom': 4}, 'Do-not-eat-shroom': {'Veilshroom': 4, 'Scourroot': 4}, 'Blastberry': {'Chocoberry': 5, 'Ashwreath': 3}, 'Cheesebite': {'Creambloom': 4, 'Fermento': 4}, 'Chloronite': {'Coalroot': 6, 'Thornshade': 2}, 'Fleshtrap': {'Cindershade': 4, 'Lonelily': 4}, 'Magic Jellybean': {'Sugar cane': 5, 'Duskbloom': 3}, 'Noctilume': {'Duskbloom': 6, 'Lonelily': 6}, 'Snoozling': {'Creambloom': 4, 'Dustgrain': 3, 'Witherbloom': 3, 'Duskbloom': 3, 'Thornshade': 3}, 'Soggybud': {'Melon': 8}, 'Chorus Fruit': {'Chloronite': 5, 'Magic Jellybean': 3}, 'PlantBoy Advance': {'Snoozling': 6, 'Thunderling': 6}, 'Puffercloud': {'Snoozling': 2, 'Do-not-eat-shroom': 6}, 'Shellfruit': {'TURTLELLINI': 1, 'Blastberry': 1}, 'Startlevine': {'Blastberry': 4, 'Cheesebite': 4}, 'Stoplight Petal': {'Snoozling': 4, 'Noctilume': 4}, 'Thunderling': {'Soggybud': 5, 'Noctilume': 3}, 'TURTLELLINI': {'Soggybud': 4, 'Choconut': 4}, 'Zombud': {'Dead Bush': 4, 'Cindershade': 2, 'Fleshtrap': 2}, 'All-in Aloe': {'Magic Jellybean': 6, 'PlantBoy Advance': 2}, 'Glasscorn': {'Startlevine': 6, 'Chloronite': 6}, 'Godseed': {'Unique Crops': 12}, 'Jerryflower': {'Jerry Seed': 1}, 'Phantomleaf': {'Chorus Fruit': 4, 'Shellfruit': 4}, 'Timestalk': {'Stoplight Petal': 4, 'Chorus Fruit': 2, 'Shellfruit': 2}, 'Devourer': {'Puffercloud': 4, 'Zombud': 4}}

DEFAULT_REQS = {
    'Wheat': 20_200_000, 'Carrot': 66_200_000, 'Potato': 66_200_000, 'Pumpkin': 20_200_000,
    'Sugar cane': 40_400_000, 'Melon': 105_000_000, 'Cactus': 40_400_000,
    'Coco Bean': 64_560_000, 'Nether Wart': 20_200_000, 'Sunflower': 20_200_000,
    'Moonflower': 20_200_000, 'Wild Rose': 40_400_000, 'Mushroom': 20_200_000
}

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
TURTLELLINI,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
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

