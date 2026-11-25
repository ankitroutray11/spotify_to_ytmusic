"""
Import Local Music Collection to YouTube Music and Shutdown PC
"""

import argparse
import os
import sys
import json
import time
import re
import mutagen
from ytmusicapi import YTMusic

MUSIC_DIR = os.getenv("LOCAL_MUSIC_DIR", os.path.join(os.path.expanduser("~"), "Music"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUTH_FILE = os.path.join(BASE_DIR, "browser.json")
CACHE_FILE = os.path.join(BASE_DIR, "local_video_cache.json")
SUMMARY_FILE = os.path.join(BASE_DIR, "local_import_summary.json")
UNMATCHED_FILE = os.path.join(BASE_DIR, "local_unmatched.txt")
AUDIO_EXTS = {".mp3", ".m4a", ".flac", ".ogg", ".wma", ".aac", ".wav"}


def clean_filename(fname: str) -> str:
    name, _ = os.path.splitext(fname)
    name = re.sub(r"\[.*?\]|\(.*?\)", "", name)
    name = re.sub(r"^\d+[\s\.\-_]+", "", name)
    name = re.sub(r"[-_]+", " ", name)
    return " ".join(name.split()).strip()


def scan_local_tracks():
    print("[1/5] Scanning local music files...")
    tracks_by_category = {}
    for root, _, files in os.walk(MUSIC_DIR):
        cat = os.path.relpath(root, MUSIC_DIR).split(os.sep)[0]
        if cat == "." or not cat:
            cat = "General"
        
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in AUDIO_EXTS:
                fp = os.path.join(root, f)
                title, artist = None, None
                try:
                    m = mutagen.File(fp, easy=True)
                    if m:
                        title = m.get("title", [None])[0]
                        artist = m.get("artist", [None])[0]
                except Exception:
                    pass

                if not title:
                    title = clean_filename(f)
                
                query = f"{title} {artist}" if artist else title
                item = {
                    "path": fp,
                    "filename": f,
                    "category": cat,
                    "title": title,
                    "artist": artist,
                    "query": query,
                }
                tracks_by_category.setdefault(cat, []).append(item)

    total_count = sum(len(v) for v in tracks_by_category.values())
    print(f"Scanned {total_count} tracks across {len(tracks_by_category)} categories.")
    return tracks_by_category


def search_track(ytm: YTMusic, query: str, cache: dict):
    if query in cache:
        return cache[query]

    try:
        res = ytm.search(query, filter="songs")
        if not res:
            res = ytm.search(query)
        if res and "videoId" in res[0]:
            vid = res[0]["videoId"]
            cache[query] = vid
            return vid
    except Exception as e:
        print(f"    Search error for '{query}': {e}")

    cache[query] = None
    return None


def add_to_playlist_robust(ytm: YTMusic, playlist_id: str, video_ids: list, chunk_size: int = 25):
    for i in range(0, len(video_ids), chunk_size):
        chunk = video_ids[i:i + chunk_size]
        try:
            ytm.add_playlist_items(playlist_id, chunk, duplicates=True)
        except Exception:
            # Fallback to individual
            for vid in chunk:
                try:
                    ytm.add_playlist_items(playlist_id, [vid], duplicates=True)
                except Exception:
                    pass
        time.sleep(0.5)


def main():
    parser = argparse.ArgumentParser(description="Import local music collection to YouTube Music.")
    parser.add_argument("--shutdown", action="store_true", help="Shut down PC 60 seconds after import completes.")
    args = parser.parse_args()

    print("==================================================")
    print(" Local Music Importer -> YouTube Music")
    print("==================================================")

    # 1. Initialize YTMusic
    if not os.path.exists(AUTH_FILE):
        print(f"[!] Error: {AUTH_FILE} not found. Cannot authenticate.")
        return

    ytm = YTMusic(AUTH_FILE)
    print(f"Authenticated as: {ytm.get_account_info().get('accountName')}")

    # 2. Scan files
    tracks_by_cat = scan_local_tracks()

    # Load cache
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            pass

    # 3. Create Master Playlist & Category Playlists
    print("\n[2/5] Creating playlists...")
    master_playlist_id = ytm.create_playlist(
        "Local - All Songs Collection",
        "Complete local library collection imported from PC"
    )
    print(f"Created Master Playlist: 'Local - All Songs Collection' ({master_playlist_id})")

    playlist_ids = {}
    for cat in sorted(tracks_by_cat.keys()):
        p_name = f"Local - {cat}"
        p_id = ytm.create_playlist(p_name, f"Local {cat} music imported from PC")
        playlist_ids[cat] = p_id
        print(f"Created category playlist '{p_name}': {p_id}")

    # 4. Search and add
    print("\n[3/5] Matching tracks and adding to playlists...")
    all_matched_vids = []
    seen_master_vids = set()
    unmatched_list = []
    total_tracks = sum(len(v) for v in tracks_by_cat.values())
    current_idx = 0

    summary = {}

    for cat, tracks in tracks_by_cat.items():
        cat_p_id = playlist_ids[cat]
        cat_vids = []
        print(f"\n--- Processing category: {cat} ({len(tracks)} tracks) ---")

        for t in tracks:
            current_idx += 1
            vid = search_track(ytm, t["query"], cache)
            if vid:
                cat_vids.append(vid)
                if vid not in seen_master_vids:
                    seen_master_vids.add(vid)
                    all_matched_vids.append(vid)
                print(f"[{current_idx}/{total_tracks}] [{cat}] Matched: {t['title']}")
            else:
                unmatched_list.append(t)
                print(f"[{current_idx}/{total_tracks}] [{cat}] Not Found: {t['title']}")
            time.sleep(0.12)

        # Add to category playlist
        if cat_vids:
            print(f"Adding {len(cat_vids)} tracks to 'Local - {cat}'...")
            add_to_playlist_robust(ytm, cat_p_id, cat_vids)

        summary[cat] = {
            "total": len(tracks),
            "matched": len(cat_vids),
            "playlist_id": cat_p_id,
            "url": f"https://music.youtube.com/playlist?list={cat_p_id}"
        }

    # Save cache
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)

    # 5. Populate Master Playlist
    print("\n[4/5] Adding all unique matched tracks to Master Playlist...")
    add_to_playlist_robust(ytm, master_playlist_id, all_matched_vids)

    summary["Master"] = {
        "total_unique": len(all_matched_vids),
        "playlist_id": master_playlist_id,
        "url": f"https://music.youtube.com/playlist?list={master_playlist_id}"
    }

    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    if unmatched_list:
        with open(UNMATCHED_FILE, "w", encoding="utf-8") as f:
            for s in unmatched_list:
                f.write(f"[{s['category']}] {s['title']} (File: {s['filename']})\n")

    print("\n==================================================")
    print(" Transfer Finished Successfully!")
    print(f" Total tracks processed: {total_tracks}")
    print(f" Total matched and imported: {len(all_matched_vids)}")
    print(f" Master Playlist: https://music.youtube.com/playlist?list={master_playlist_id}")
    print("==================================================")

    # 6. Optional Shutdown PC
    if args.shutdown:
        print("\n[5/5] Task complete. Initiating PC shutdown in 60 seconds...")
        print("Run 'shutdown /a' in command prompt if you want to abort.")
        os.system('shutdown /s /t 60 /c "Antigravity Music Import Complete. Shutting down PC."')
    else:
        print("\n[5/5] Task complete. (Pass --shutdown to auto-shutdown after import.)")


if __name__ == "__main__":
    main()
