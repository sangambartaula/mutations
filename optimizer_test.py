"""
Greenhouse Layout Optimizer v6 - Iterative with aggressive repair.

Radius 1 (8-neighbor Chebyshev) confirmed by matching user's known result.
Uses iterative construction + aggressive local search to achieve 0 unmet.
"""

GRID_SIZE = 10


def get_neighbors(r, c, grid_size=GRID_SIZE):
    """Get 8 neighbors (Chebyshev distance 1)."""
    result = []
    for dr in [-1, 0, 1]:
        for dc in [-1, 0, 1]:
            if dr == 0 and dc == 0: continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < grid_size and 0 <= nc < grid_size:
                result.append((nr, nc))
    return result


def optimize(recipe, limit, ingredient_costs, grid_size=GRID_SIZE, blocked=None):
    """
    Main optimizer. Returns (tile_counts, unmet, n_mutations).
    """
    if blocked is None:
        blocked = set()
    
    total_needed_per = sum(recipe.values())
    if total_needed_per == 0:
        return {}, 0, limit
    
    all_tiles = set((r, c) for r in range(grid_size) for c in range(grid_size)) - blocked
    n_to_convert = len(all_tiles) - limit
    
    if n_to_convert <= 0:
        return {k: v * limit for k, v in recipe.items()}, 0, limit
    
    # Precompute neighbors
    nbrs = {}
    for t in all_tiles:
        nbrs[t] = set(get_neighbors(t[0], t[1], grid_size)) & all_tiles
    
    # Sort ingredients expensive first
    sorted_ings = sorted(
        [ing for ing in recipe if recipe[ing] > 0],
        key=lambda x: ingredient_costs.get(x, 0),
        reverse=True
    )
    
    # Start: all are mutations
    is_mutation = {t: True for t in all_tiles}
    ing_type = {}  # tile -> ingredient name (only for non-mutations)
    
    def get_needs(m_tile):
        """What does this mutation still need?"""
        n = dict(recipe)
        for nb in nbrs[m_tile]:
            if not is_mutation[nb] and nb in ing_type:
                ing = ing_type[nb]
                if n.get(ing, 0) > 0:
                    n[ing] -= 1
        return n
    
    def total_unmet():
        return sum(max(0, v) for t in all_tiles if is_mutation[t] 
                   for v in get_needs(t).values())
    
    def score_conversion(tile, ingredient):
        """Score for converting tile from mutation to ingredient of given type."""
        # Benefit: removes this tile's unmet + satisfies neighbor mutations
        own_unmet = sum(max(0, v) for v in get_needs(tile).values())
        neighbor_benefit = 0
        for nb in nbrs[tile]:
            if is_mutation[nb]:
                n = get_needs(nb)
                if n.get(ingredient, 0) > 0:
                    neighbor_benefit += 1
        return own_unmet + neighbor_benefit
    
    # Phase 1: Greedily convert mutations to ingredients
    for step in range(n_to_convert):
        best_tile = None
        best_ing = None
        best_score = -1
        
        mutations_list = [t for t in all_tiles if is_mutation[t]]
        
        for candidate in mutations_list:
            for ingredient in sorted_ings:
                s = score_conversion(candidate, ingredient)
                if s > best_score:
                    best_score = s
                    best_tile = candidate
                    best_ing = ingredient
        
        if best_tile is None:
            break
        
        is_mutation[best_tile] = False
        ing_type[best_tile] = best_ing
    
    # Phase 2: Aggressive repair - swap ingredient types to reduce unmet
    for iteration in range(20):
        unmet = total_unmet()
        if unmet == 0:
            break
        
        improved = False
        
        # Try reassigning ingredient types
        for tile in list(ing_type.keys()):
            current = ing_type[tile]
            current_unmet = total_unmet()
            
            for new_ing in sorted_ings:
                if new_ing == current: continue
                ing_type[tile] = new_ing
                new_unmet = total_unmet()
                if new_unmet < current_unmet:
                    improved = True
                    break
                ing_type[tile] = current
        
        if not improved:
            # Try swapping a mutation with an ingredient position
            for m_tile in [t for t in all_tiles if is_mutation[t]]:
                m_needs = get_needs(m_tile)
                m_unmet = sum(max(0, v) for v in m_needs.values())
                if m_unmet == 0:
                    continue
                
                # Try swapping with each neighboring ingredient
                for nb in nbrs[m_tile]:
                    if is_mutation[nb] or nb not in ing_type:
                        continue
                    
                    # Swap: m_tile becomes ingredient, nb becomes mutation
                    old_ing = ing_type[nb]
                    old_unmet = total_unmet()
                    
                    is_mutation[m_tile] = False
                    is_mutation[nb] = True
                    del ing_type[nb]
                    
                    # Try different ingredient types for m_tile
                    best_new_ing = None
                    best_new_unmet = old_unmet
                    
                    for try_ing in sorted_ings:
                        ing_type[m_tile] = try_ing
                        new_unmet = total_unmet()
                        if new_unmet < best_new_unmet:
                            best_new_unmet = new_unmet
                            best_new_ing = try_ing
                    
                    if best_new_ing is not None:
                        ing_type[m_tile] = best_new_ing
                        improved = True
                        break
                    else:
                        # Revert
                        is_mutation[m_tile] = True
                        is_mutation[nb] = False
                        ing_type[nb] = old_ing
                        if m_tile in ing_type:
                            del ing_type[m_tile]
                
                if improved:
                    break
        
        if not improved:
            break
    
    # Final counts
    unmet = total_unmet()
    tile_counts = {}
    for t, ing in ing_type.items():
        tile_counts[ing] = tile_counts.get(ing, 0) + 1
    
    n_mutations = sum(1 for t in all_tiles if is_mutation[t])
    return tile_counts, unmet, n_mutations


if __name__ == "__main__":
    print("=" * 70)
    print("ASHWREATH (Revamped: 2W+2F, Limit=52)")
    print("Expected: 26 Wart + 21 Fire = 47 total")
    print("=" * 70)
    
    # Test both cost orderings
    for label, costs in [("Wart expensive", {'Nether Wart': 100, 'Fire': 4}),
                          ("Fire expensive", {'Nether Wart': 4, 'Fire': 100})]:
        tiles, unmet, placed = optimize({'Nether Wart': 2, 'Fire': 2}, 52, costs, blocked={(0,0)})
        total = sum(tiles.values())
        print(f"  {label}: {tiles} total={total} unmet={unmet} placed={placed}")
    
    print("\n" + "=" * 70)
    print("OTHER MUTATIONS")
    print("=" * 70)
    
    approx = {'Cocoa Beans': 3, 'Wheat': 3, 'Pumpkin': 10, 'Melon': 2,
              'Potato': 3, 'Carrot': 3, 'Dead Bush': 50}
    
    tests = [
        ('Choconut', {'Cocoa Beans': 4}, 52),
        ('Dustgrain', {'Wheat': 4}, 52),
        ('Gloomgourd', {'Pumpkin': 1, 'Melon': 1}, 72),
        ('Scourroot', {'Potato': 2, 'Carrot': 2}, 52),
        ('Witherbloom', {'Dead Bush': 8}, 16),
    ]
    
    for name, rec, lim in tests:
        naive = sum(v * lim for v in rec.values())
        tiles, unmet, placed = optimize(rec, lim, approx, blocked={(0,0)})
        total = sum(tiles.values())
        save = (1 - total / naive) * 100 if naive > 0 else 0
        status = "OK" if unmet == 0 else f"FAIL(unmet={unmet})"
        ing = ", ".join(f"{v} {k}" for k, v in sorted(tiles.items(), key=lambda x: -x[1]))
        print(f"  {status:20s} {name:20s} | {placed}/{lim} | "
              f"opt={total} naive={naive} save={save:.0f}% | {ing}")
