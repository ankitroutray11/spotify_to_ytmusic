import os
import re
import mutagen

MUSIC_DIR = os.getenv("LOCAL_MUSIC_DIR", os.path.join(os.path.expanduser("~"), "Music"))
AUDIO_EXTS = {".mp3", ".m4a", ".flac", ".ogg", ".wma", ".aac", ".wav"}

def clean_filename(fname: str) -> str:
    name, _ = os.path.splitext(fname)
    # Remove common junk like [www.site.com], (Official Video), 128kbps, etc.
    name = re.sub(r"\[.*?\]|\(.*?\)", "", name)
    name = re.sub(r"^\d+[\s\.\-_]+", "", name)  # track numbers at start
    name = re.sub(r"[-_]+", " ", name)
    return " ".join(name.split()).strip()

def scan():
    tracks = []
    for root, _, files in os.walk(MUSIC_DIR):
        category = os.path.relpath(root, MUSIC_DIR).split(os.sep)[0]
        if category == ".":
            category = "General"
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
                tracks.append({
                    "path": fp,
                    "filename": f,
                    "category": category,
                    "title": title,
                    "artist": artist,
                    "query": query
                })
    return tracks

if __name__ == "__main__":
    tracks = scan()
    print(f"Total audio tracks found: {len(tracks)}")
    categories = {}
    for t in tracks:
        categories[t["category"]] = categories.get(t["category"], 0) + 1
    for cat, cnt in sorted(categories.items()):
        print(f"  {cat}: {cnt} tracks")
    print("\nSample 5 tracks:")
    for t in tracks[:5]:
        print(f"  - [{t['category']}] {t['title']} (Artist: {t['artist']}) -> Query: '{t['query']}'")
