"""
Import Resolved Spotify Songs to YouTube Music
"""

import os
import sys
import json
import re
import time
from ytmusicapi import YTMusic
from ytmusicapi.auth.browser import initialize_headers

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SONGS_FILE = os.path.join(BASE_DIR, "resolved_songs.json")
AUTH_FILE = os.path.join(BASE_DIR, "browser.json")
HEADERS_TXT = os.path.join(BASE_DIR, "headers.txt")


def parse_headers_from_text(raw_text: str) -> dict:
    """Robustly extracts headers from cURL (bash/cmd/PowerShell) or raw headers."""
    headers = {}

    # 1. Look for cURL headers: -H 'Name: Value' or -H "Name: Value"
    curl_matches = re.findall(r"-H\s+['\"]([^:]+?):\s*(.+?)['\"](?:\s*\\)?$", raw_text, re.MULTILINE | re.IGNORECASE)
    if curl_matches:
        for k, v in curl_matches:
            headers[k.strip().lower()] = v.strip()

    # Look for cURL cookie flag: -b '...' or --cookie '...'
    cookie_match = re.search(r"(?:-b|--cookie)\s+['\"](.+?)['\"]", raw_text)
    if cookie_match and "cookie" not in headers:
        headers["cookie"] = cookie_match.group(1).strip()

    # 2. If not cURL, parse standard key: value lines
    if not headers:
        for line in raw_text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ": " in line:
                parts = line.split(": ", 1)
                k = parts[0].strip().lower().lstrip(":")
                v = parts[1].strip()
                headers[k] = v

    # Fallback: Check if user pasted raw cookie directly without "cookie:" label
    if "cookie" not in headers:
        for line in raw_text.splitlines():
            line = line.strip()
            if "SAPISID=" in line or "LOGIN_INFO=" in line or "SID=" in line:
                headers["cookie"] = line

    if "x-goog-authuser" not in headers:
        headers["x-goog-authuser"] = "0"

    return headers


def setup_auth() -> YTMusic:
    """Ensures YouTube Music authentication is configured."""
    # Check headers.txt first
    if os.path.exists(HEADERS_TXT):
        with open(HEADERS_TXT, "r", encoding="utf-8") as f:
            txt = f.read().strip()
        if txt and not txt.startswith("# Paste your full copied cURL"):
            parsed = parse_headers_from_text(txt)
            if "cookie" in parsed:
                final_headers = dict(initialize_headers())
                final_headers.update(parsed)
                final_headers["origin"] = "https://music.youtube.com"
                with open(AUTH_FILE, "w", encoding="utf-8") as f:
                    json.dump(final_headers, f, indent=4)
                print(f"[v] Extracted headers from headers.txt and saved to {AUTH_FILE}!")
                return YTMusic(AUTH_FILE)

    if os.path.exists(AUTH_FILE):
        try:
            return YTMusic(AUTH_FILE)
        except Exception:
            pass

    print("\n==================================================")
    print(" YouTube Music Authentication Required")
    print("==================================================")
    print("To avoid PowerShell line-wrapping issues:")
    print("1. In your browser DevTools Network tab, right-click 'browse' -> Copy -> 'Copy as cURL (bash)'")
    print("2. Open this file in Notepad:")
    print(f"   {HEADERS_TXT}")
    print("3. Paste the copied text and save the file (Ctrl+S).")
    print("4. Re-run this script!")
    print("==================================================\n")
    sys.exit(0)


def main():
    if not os.path.exists(SONGS_FILE):
        print(f"[!] Error: {SONGS_FILE} not found. Please run resolve_songs.py first.")
        return

    with open(SONGS_FILE, "r", encoding="utf-8") as f:
        songs = json.load(f)

    print(f"Loaded {len(songs)} tracks to transfer.")

    # Authenticate
    ytm = setup_auth()

    # Destination Choice
    print("\nHow would you like to import these tracks?")
    print("  1: Create a new Playlist (e.g. 'Merged Spotify Liked Songs') [Recommended]")
    print("  2: Add directly to YouTube Music Liked Songs")
    choice = input("Enter choice [1/2, default 1]: ").strip()

    playlist_id = None
    if choice != "2":
        playlist_name = input("Enter playlist name [default: Merged Spotify Liked Songs]: ").strip() or "Merged Spotify Liked Songs"
        playlist_id = ytm.create_playlist(playlist_name, "Imported from Spotify Liked Songs")
        print(f"[v] Created playlist: '{playlist_name}'")

    print("\n[+] Searching and transferring tracks to YouTube Music...")
    successful = 0
    failed = []

    for idx, song in enumerate(songs, 1):
        query = song.get("query", f"{song['title']} {song['artists']}")
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
                print(f"[{idx}/{len(songs)}] Added: {song['title']} - {song['artists']}")
            else:
                failed.append(song)
                print(f"[{idx}/{len(songs)}] Not found: {song['title']} - {song['artists']}")
        except Exception as e:
            failed.append(song)
            print(f"[{idx}/{len(songs)}] Error on '{song['title']}': {e}")

        time.sleep(0.25)

    print("\n==================================================")
    print(" Transfer Complete!")
    print(f" Successfully added: {successful} / {len(songs)} songs")
    print(f" Unmatched / Errors: {len(failed)}")
    print("==================================================")

    if failed:
        unmatched_path = os.path.join(BASE_DIR, "unmatched_songs.txt")
        with open(unmatched_path, "w", encoding="utf-8") as f:
            for s in failed:
                f.write(f"{s['title']} - {s['artists']}\n")
        print(f"[i] Saved unmatched songs to {unmatched_path}")


if __name__ == "__main__":
    main()
