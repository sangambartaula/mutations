import requests
import re

url = "https://skymutations.eu/greenhouse"
response = requests.get(url)
js_files = re.findall(r'src="([^"]*\.js)"', response.text)

for js in js_files:
    js_url = f"https://skymutations.eu{js}" if js.startswith('/') else f"https://skymutations.eu/{js}"
    print(f"Fetching {js_url}")
    js_resp = requests.get(js_url)
    if "Puffercloud" in js_resp.text:
        print(f"Found Puffercloud in {js}")
        # Save it to a file for analysis
        with open("skymutations_logic.js", "w", encoding="utf-8") as f:
            f.write(js_resp.text)
        break
