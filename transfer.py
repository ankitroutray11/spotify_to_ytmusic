"""
Spotify to YouTube Music Liked Songs Transfer Script
Transfers and deduplicates liked songs from two Spotify accounts into YouTube Music.
"""

import os
import sys
import time
from typing import Dict, List, Set
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from ytmusicapi import YTMusic
import ytmusicapi

# Load environment variables from .env
load_dotenv()

REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
SPOTIFY_SCOPE = "user-library-read"

ACCOUNTS = [
    {
        "label": "Account 1",
        "client_id": os.getenv("SPOTIFY_ACCOUNT_1_CLIENT_ID"),
        "client_secret": os.getenv("SPOTIFY_ACCOUNT_1_CLIENT_SECRET"),
        "cache": ".spotify_cache_account1",
    },
    {
        "label": "Account 2",
        "client_id": os.getenv("SPOTIFY_ACCOUNT_2_CLIENT_ID"),
        "client_secret": os.getenv("SPOTIFY_ACCOUNT_2_CLIENT_SECRET"),
        "cache": ".spotify_cache_account2",
    },
]

YTM_AUTH_FILE = "oauth.json"


def get_spotify_client(acc: dict) -> spotipy.Spotify:
    """Authenticates a Spotify account using its credentials and dedicated cache."""
    print(f"\n==========================================")
    print(f"[+] Authenticating Spotify: {acc['label']}")
    print(f"==========================================")
    print("A browser window will open. Please log into Spotify and authorize the app.")

    auth_manager = SpotifyOAuth(
        client_id=acc["client_id"],
        client_secret=acc["client_secret"],
        redirect_uri=REDIRECT_URI,
        scope=SPOTIFY_SCOPE,
        cache_path=acc["cache"],
        open_browser=True,
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def fetch_liked_songs(sp: spotipy.Spotify, label: str) -> List[Dict[str, str]]:
    """Paginates through and retrieves all liked tracks for a given Spotify account."""
    print(f"\n[+] Fetching liked songs from {label}...")
    songs = []
    offset = 0
    limit = 50

    while True:
        try:
            results = sp.current_user_saved_tracks(limit=limit, offset=offset)
        except Exception as e:
            print(f"[!] Error fetching tracks: {e}")
            break

        items = results.get("items", [])
        if not items:
            break

        for item in items:
            track = item.get("track")
            if not track:
                continue
            name = track.get("name")
            artists = ", ".join([a["name"] for a in track.get("artists", [])])
            isrc = track.get("external_ids", {}).get("isrc", "")
            songs.append({
                "name": name,
                "artists": artists,
                "isrc": isrc,
                "query": f"{name} {artists}",
            })

        offset += len(items)
        print(f"    Fetched {offset} songs so far...", end="\r")

    print(f"\n[v] Retrieved {len(songs)} songs from {label}.")
    return songs


def setup_ytmusic() -> YTMusic:
    """Initializes or guides authentication for YouTube Music."""
    if not os.path.exists(YTM_AUTH_FILE):
        print(f"\n==========================================")
        print(f"[+] Setting up YouTube Music Authentication")
        print(f"==========================================")
        print("Starting Google device authorization flow...")
        try:
            ytmusicapi.setup_oauth(None, None, filepath=YTM_AUTH_FILE, open_browser=True)
            print(f"[v] Saved credentials to {YTM_AUTH_FILE}")
        except Exception as e:
            print(f"[!] Interactive setup error: {e}")
            print("    Please follow manual setup or copy headers into oauth.json.")
            sys.exit(1)

    return YTMusic(YTM_AUTH_FILE)


def main():
    print("==================================================")
    print(" Spotify -> YouTube Music Liked Songs Transfer")
    print("==================================================")

    # 1. Fetch from Spotify Accounts
    all_songs = []
    for acc in ACCOUNTS:
        if not acc["client_id"] or not acc["client_secret"]:
            print(f"[!] Missing credentials for {acc['label']}. Skipping...")
            continue
        sp = get_spotify_client(acc)
        songs = fetch_liked_songs(sp, acc["label"])
        all_songs.extend(songs)

    if not all_songs:
        print("[!] No songs retrieved from either Spotify account. Exiting.")
        return

    # 2. Deduplicate
    unique_songs = []
    seen: Set[str] = set()

    for s in all_songs:
        key = s["isrc"] if s["isrc"] else f"{s['name'].lower()} - {s['artists'].lower()}"
        if key not in seen:
            seen.add(key)
            unique_songs.append(s)

    print(f"\n[v] Summary:")
    print(f"    Total songs fetched: {len(all_songs)}")
    print(f"    Unique tracks to import: {len(unique_songs)} ({len(all_songs) - len(unique_songs)} duplicates removed)")

    # 3. Setup YouTube Music
    ytm = setup_ytmusic()

    # Destination Choice
    print("\nHow would you like to save these in YouTube Music?")
    print("  1: Create a new Playlist (Recommended - easy to manage & review)")
    print("  2: Add directly to Liked Songs")
    choice = input("Enter choice [1/2, default: 1]: ").strip()

    playlist_id = None
    if choice != "2":
        playlist_title = input("Enter playlist name [default: Merged Spotify Liked Songs]: ").strip() or "Merged Spotify Liked Songs"
        playlist_id = ytm.create_playlist(playlist_title, "Merged Liked Songs imported from Spotify")
        print(f"[v] Created playlist: '{playlist_title}'")

    # 4. Search and Add
    print("\n[+] Matching and adding tracks to YouTube Music...")
    successful = 0
    failed = []

    for idx, song in enumerate(unique_songs, 1):
        query = song["query"]
        try:
            results = ytm.search(query, filter="songs")
            if not results:
                results = ytm.search(query)

            if results and "videoId" in results[0]:
                video_id = results[0]["videoId"]
                if playlist_id:
                    ytm.add_playlist_items(playlist_id, [video_id])
                else:
                    ytm.rate_song(video_id, "LIKE")
                successful += 1
                print(f"[{idx}/{len(unique_songs)}] Added: {song['name']} - {song['artists']}")
            else:
                failed.append(song)
                print(f"[{idx}/{len(unique_songs)}] Not found: {song['name']} - {song['artists']}")
        except Exception as err:
            failed.append(song)
            print(f"[{idx}/{len(unique_songs)}] Error on '{song['name']}': {err}")

        time.sleep(0.3)

    print("\n==================================================")
    print(" Transfer Completed!")
    print(f" Successfully added: {successful} songs")
    print(f" Failed / Unmatched: {len(failed)} songs")
    print("==================================================")

    if failed:
        with open("unmatched_songs.txt", "w", encoding="utf-8") as f:
            for s in failed:
                f.write(f"{s['name']} - {s['artists']}\n")
        print("[i] A list of unmatched tracks was saved to unmatched_songs.txt.")


if __name__ == "__main__":
    main()
