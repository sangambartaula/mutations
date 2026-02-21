from api.index import RECIPES, MUTATION_LIMITS_1_PLOT
import json

def get_simple_reqs():
    lines = ["# Max Plot Requirements (Unshared, Limit * Recipe)\n"]
    for mut, limit in sorted(MUTATION_LIMITS_1_PLOT.items()):
        if mut not in RECIPES:
            continue
        
        recipe = RECIPES[mut]
        lines.append(f"### {mut} (Max Limit: {limit})")
        if mut == "Shellfruit":
            lines.append("- 16x Blastberry")
            lines.append(f"- {limit}x Turtlellini")
        else:
            for ing, count in recipe.items():
                if count > 0:
                    lines.append(f"- {count * limit}x {ing} ({count} per crop)")
        lines.append("")
        
    with open("C:/Users/Sangam Bartaula/.gemini/antigravity/brain/45fdb5a2-ce88-42b7-b4b6-277acf8009db/ingredients_list.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

if __name__ == "__main__":
    get_simple_reqs()
