import concurrent.futures
import json
import re
import os
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE1 = os.path.join(BASE_DIR, "spotify_urls.txt")
FILE2 = os.path.join(BASE_DIR, "spotify_urls_account2.txt")
OUTPUT_JSON = os.path.join(BASE_DIR, "resolved_songs.json")

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})

def resolve_track(url: str):
    url = url.strip()
    if not url:
        return None
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
    existing = {}
    if os.path.exists(OUTPUT_JSON):
        with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
            for s in json.load(f):
                existing[s["url"]] = s

    urls1 = [l.strip() for l in open(FILE1, "r", encoding="utf-8") if l.strip()] if os.path.exists(FILE1) else []
    urls2 = [l.strip() for l in open(FILE2, "r", encoding="utf-8") if l.strip()] if os.path.exists(FILE2) else []

    all_raw_urls = urls1 + urls2
    unique_urls = list(dict.fromkeys(all_raw_urls))

    print(f"Total raw URLs: {len(all_raw_urls)} (Account 1: {len(urls1)}, Account 2: {len(urls2)})")
    print(f"Unique URLs after link deduplication: {len(unique_urls)}")

    urls_to_fetch = [u for u in unique_urls if u not in existing]
    print(f"Already resolved: {len(unique_urls) - len(urls_to_fetch)}. New tracks to resolve: {len(urls_to_fetch)}...")

    if urls_to_fetch:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            for res in executor.map(resolve_track, urls_to_fetch):
                if res:
                    existing[res["url"]] = res
                    print(f"[+] Resolved: {res['title']} - {res['artists']}")

    # Final list of resolved songs
    final_songs = []
    seen_titles = set()
    for u in unique_urls:
        if u in existing:
            s = existing[u]
            # Secondary deduplication by title + artist
            norm_key = f"{s['title'].strip().lower()} - {s['artists'].strip().lower()}"
            if norm_key not in seen_titles:
                seen_titles.add(norm_key)
                final_songs.append(s)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(final_songs, f, indent=2, ensure_ascii=False)

    print(f"\n==========================================")
    print(f" Merged & Deduplicated Total:")
    print(f" Final unique songs ready for import: {len(final_songs)}")
    print(f" Saved to {OUTPUT_JSON}")
    print(f"==========================================")

if __name__ == "__main__":
    main()
