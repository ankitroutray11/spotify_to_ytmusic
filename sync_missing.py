import json
import os
import time
from ytmusicapi import YTMusic

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SONGS_FILE = os.path.join(BASE_DIR, "resolved_songs.json")
AUTH_FILE = os.path.join(BASE_DIR, "browser.json")
CACHE_FILE = os.path.join(BASE_DIR, "video_cache.json")
PLAYLIST_ID = "PLAxqNydnc_HY"

ytm = YTMusic(AUTH_FILE)

# 1. Load or build video cache
cache = {}
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        cache = json.load(f)

with open(SONGS_FILE, "r", encoding="utf-8") as f:
    songs = json.load(f)

print(f"Total songs to sync: {len(songs)}")

# Search for any not in cache
updated_cache = False
for idx, s in enumerate(songs, 1):
    q = s.get("query", f"{s['title']} {s['artists']}")
    if q not in cache or not cache[q]:
        try:
            res = ytm.search(q, filter="songs")
            if not res:
                res = ytm.search(q)
            if res and "videoId" in res[0]:
                cache[q] = res[0]["videoId"]
                updated_cache = True
                print(f"[{idx}/{len(songs)}] Found: {s['title']} -> {res[0]['videoId']}")
            else:
                print(f"[{idx}/{len(songs)}] Not found: {s['title']}")
        except Exception as e:
            print(f"[{idx}/{len(songs)}] Error searching {s['title']}: {e}")
        time.sleep(0.1)

if updated_cache or not os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)

# 2. Get current tracks in playlist
print("\nFetching current tracks in playlist...")
playlist = ytm.get_playlist(PLAYLIST_ID, limit=None)
current_tracks = playlist.get("tracks", [])
current_vids = set()
for t in current_tracks:
    if t.get("videoId"):
        current_vids.add(t["videoId"])

print(f"Currently in playlist: {len(current_tracks)} tracks ({len(current_vids)} unique video IDs)")

# 3. Find missing video IDs
missing_vids = []
for s in songs:
    q = s.get("query", f"{s['title']} {s['artists']}")
    vid = cache.get(q)
    if vid and vid not in current_vids:
        missing_vids.append((s["title"], vid))
        current_vids.add(vid)  # Avoid adding duplicates within missing set

print(f"Tracks missing from playlist: {len(missing_vids)}")

# 4. Add missing tracks with duplicates=True in chunks of 20
if missing_vids:
    print("\nAdding missing tracks to playlist...")
    vids_only = [v for _, v in missing_vids]
    chunk_size = 20

    for i in range(0, len(vids_only), chunk_size):
        chunk = vids_only[i:i + chunk_size]
        try:
            res = ytm.add_playlist_items(PLAYLIST_ID, chunk, duplicates=True)
            added_count = min(i + chunk_size, len(vids_only))
            print(f"    Added batch {added_count} / {len(vids_only)}...")
        except Exception as e:
            print(f"    Batch error ({e}), retrying individually...")
            for title, vid in missing_vids[i:i + chunk_size]:
                try:
                    ytm.add_playlist_items(PLAYLIST_ID, [vid], duplicates=True)
                    print(f"        + Added: {title}")
                except Exception as err:
                    print(f"        - Failed: {title} ({err})")
                time.sleep(0.3)
        time.sleep(1)

# 5. Verify final count
final_p = ytm.get_playlist(PLAYLIST_ID, limit=None)
print("\n==========================================")
print(f" Final Playlist Status:")
print(f" Track count: {final_p.get('trackCount')}")
print(f" URL: https://music.youtube.com/playlist?list={PLAYLIST_ID}")
print("==========================================")
