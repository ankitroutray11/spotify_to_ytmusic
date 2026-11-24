import requests
import re
import json

url = "https://open.spotify.com/embed/track/7BjQqiOJio4RdPL33yALKE"
r = requests.get(url)
m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text)
if m:
    data = json.loads(m.group(1))
    entity = data.get("props", {}).get("pageProps", {}).get("state", {}).get("data", {}).get("entity", {})
    title = entity.get("name")
    artists = ", ".join([a["name"] for a in entity.get("artists", [])])
    print(f"Title: {title}")
    print(f"Artists: {artists}")
else:
    print("Not found")
