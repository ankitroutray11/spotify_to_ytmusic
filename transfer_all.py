import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from ytmusicapi import YTMusic

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SONGS_FILE = os.path.join(BASE_DIR, "resolved_songs.json")
AUTH_FILE = os.path.join(BASE_DIR, "browser.json")
UNMATCHED_FILE = os.path.join(BASE_DIR, "unmatched_songs.txt")

def search_track(ytm, song):
    query = song.get("query", f"{song['title']} {song['artists']}")
    try:
        results = ytm.search(query, filter="songs")
        if not results:
            results = ytm.search(query)
        if results and "videoId" in results[0]:
            return song, results[0]["videoId"], results[0].get("title", "")
    except Exception as e:
        print(f"Search error for {query}: {e}")
    return song, None, None

def main():
    print("=== YouTube Music Importer ===")
    ytm = YTMusic(AUTH_FILE)

    account_info = ytm.get_account_info() if hasattr(ytm, "get_account_info") else {}
    print(f"Logged in as: {account_info.get('accountName', 'YouTube Music User')}")

    with open(SONGS_FILE, "r", encoding="utf-8") as f:
        songs = json.load(f)

    print(f"Total songs to import: {len(songs)}")

    # 1. Create Playlist
    playlist_title = "Merged Spotify Liked Songs"
    playlist_id = ytm.create_playlist(
        playlist_title,
        "Imported from two Spotify accounts via Antigravity"
    )
    print(f"[v] Created playlist '{playlist_title}' (ID: {playlist_id})")

    # 2. Search all tracks in parallel
    print("[+] Searching for matching tracks on YouTube Music...")
    matched_video_ids = []
    unmatched_songs = []

    # Sequential or small pool to avoid rate limiting
    for idx, s in enumerate(songs, 1):
        query = s.get("query", f"{s['title']} {s['artists']}")
        _, vid, matched_title = search_track(ytm, s)
        if vid:
            matched_video_ids.append(vid)
            print(f"[{idx}/{len(songs)}] Matched: {s['title']} -> {matched_title}")
        else:
            unmatched_songs.append(s)
            print(f"[{idx}/{len(songs)}] Not found: {s['title']} - {s['artists']}")
        time.sleep(0.15)

    print(f"\n[v] Search complete: {len(matched_video_ids)} matched, {len(unmatched_songs)} unmatched.")

    # 3. Add to playlist in chunks of 50
    print("[+] Adding matched tracks to playlist in batches...")
    chunk_size = 50
    for i in range(0, len(matched_video_ids), chunk_size):
        chunk = matched_video_ids[i:i + chunk_size]
        try:
            ytm.add_playlist_items(playlist_id, chunk)
            print(f"    Added {min(i + chunk_size, len(matched_video_ids))} / {len(matched_video_ids)} songs...")
        except Exception as e:
            print(f"    Error adding chunk {i}: {e}")
            # Try adding individually
            for vid in chunk:
                try:
                    ytm.add_playlist_items(playlist_id, [vid])
                except Exception:
                    pass
        time.sleep(1)

    if unmatched_songs:
        with open(UNMATCHED_FILE, "w", encoding="utf-8") as f:
            for s in unmatched_songs:
                f.write(f"{s['title']} - {s['artists']}\n")
        print(f"[i] Unmatched songs saved to {UNMATCHED_FILE}")

    print("\n==========================================")
    print(f" Transfer Complete!")
    print(f" Playlist URL: https://music.youtube.com/playlist?list={playlist_id}")
    print(f" Total added: {len(matched_video_ids)} / {len(songs)}")
    print("==========================================")

if __name__ == "__main__":
    main()
