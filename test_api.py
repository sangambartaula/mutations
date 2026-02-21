import urllib.request, json
try:
    res = urllib.request.urlopen('http://127.0.0.1:8000/api/leaderboard?plots=1')
    data = json.loads(res.read())
    print("Success! Top crop:", data["leaderboard"][0]["mutation"])
except Exception as e:
    import traceback
    traceback.print_exc()
