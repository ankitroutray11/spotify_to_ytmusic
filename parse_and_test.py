import os
import re
import json
from ytmusicapi import YTMusic
from ytmusicapi.auth.browser import initialize_headers

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
headers_file = os.path.join(BASE_DIR, "headers.txt")
with open(headers_file, "r", encoding="utf-8") as f:
    curl_text = f.read()

headers = dict(initialize_headers())

# Extract -H headers
matches = re.findall(r"-H\s+['\"]([^:]+?):\s*(.+?)['\"]", curl_text)
for k, v in matches:
    headers[k.strip().lower()] = v.strip()

# Extract -b cookie
cookie_m = re.search(r"-b\s+['\"](.+?)['\"]", curl_text)
if cookie_m:
    headers["cookie"] = cookie_m.group(1).strip()

headers["origin"] = "https://music.youtube.com"

# Clean unwanted
for ig in ["host", "content-length", "accept-encoding"]:
    headers.pop(ig, None)

out_file = os.path.join(BASE_DIR, "browser.json")
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(headers, f, indent=4)

print("Saved browser.json! Testing connection...")
ytm = YTMusic(out_file)
history = ytm.get_history()
print("SUCCESS! Retrieved history items:", len(history))

# Try creating the playlist or checking user
user = ytm.get_account_info() if hasattr(ytm, "get_account_info") else "OK"
print("User info:", user)
