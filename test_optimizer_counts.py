from api.index import compute_optimized_plot_cost, RECIPES, MUTATION_LIMITS_1_PLOT
import json

def test_all():
    results = {}
    for mut, limit in MUTATION_LIMITS_1_PLOT.items():
        if mut not in RECIPES:
            continue
            
        recipe = RECIPES[mut]
        # fake prices to just get counts
        fake_prices = tuple(sorted([(ing, 1) for ing in recipe.keys()]))
        
        counts = compute_optimized_plot_cost(mut, fake_prices)
        results[mut] = {
            "limit": limit,
            "ingredients": counts
        }
        
    with open('optimizer_dump_clean.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    test_all()
