import concurrent.futures
import json
import re
import sys
import requests

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
URLS_FILE = os.path.join(BASE_DIR, "spotify_urls.txt")
OUTPUT_JSON = os.path.join(BASE_DIR, "resolved_songs.json")

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})

def resolve_track(url: str):
    url = url.strip()
    if not url:
        return None
    # Ensure embed url
    track_id = url.split("/track/")[-1].split("?")[0]
    embed_url = f"https://open.spotify.com/embed/track/{track_id}"

    try:
        r = session.get(embed_url, timeout=10)
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text)
        if m:
            data = json.loads(m.group(1))
            entity = data.get("props", {}).get("pageProps", {}).get("state", {}).get("data", {}).get("entity", {})
            title = entity.get("name")
            artists = ", ".join([a["name"] for a in entity.get("artists", [])])
            if title:
                return {
                    "url": url,
                    "title": title,
                    "artists": artists,
                    "query": f"{title} {artists}"
                }
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None

def main():
    with open(URLS_FILE, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"Resolving {len(urls)} Spotify tracks...")
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for res in executor.map(resolve_track, urls):
            if res:
                results.append(res)
                print(f"[{len(results)}/{len(urls)}] {res['title']} - {res['artists']}")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Resolved {len(results)} out of {len(urls)} songs.")
    print(f"Saved to {OUTPUT_JSON}.")

if __name__ == "__main__":
    main()
