import re
import json

with open("skymutations_logic.js", "r", encoding="utf-8") as f:
    js_content = f.read()

# Try to find the array of mutations or objects that contain 'mutations'
# Common patterns in minified react/vue apps for data blocks
matches = re.finditer(r'\{[^}]*"id":"([^"]+)"[^}]*"materials":(\[[^\]]+\])', js_content)
all_mutations = {}
for m in matches:
    mut_id = m.group(1)
    # the materials array might be complex, let's just dump what we find
    all_mutations[mut_id] = m.group(2)

print(f"Found {len(all_mutations)} mutation objects by regex 1")

if len(all_mutations) == 0:
    # Alternative heuristic: search for 'Blastberry' to see its neighborhood
    idx = js_content.find('"Shellfruit"')
    if idx != -1:
        print("Shellfruit found at idx:", idx)
        print("Context around Shellfruit:")
        print(js_content[max(0, idx-500) : min(len(js_content), idx+1000)])
