import os
import pandas as pd
from ytmusicapi import YTMusic

PLAYLIST_NAME = "PCMusic2"

OUTPUT_FILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_files")
CSV_INPUT = os.path.join(OUTPUT_FILES_DIR, "final_curated.csv")
CSV_OUTPUT = os.path.join(OUTPUT_FILES_DIR, "stage8_ytmusic_results.csv")

BROWSER_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser.json")
yt = YTMusic(BROWSER_JSON)


# -------- helpers --------
def get_or_create_playlist(name):
    playlists = yt.get_library_playlists(limit=100)
    for p in playlists:
        if p["title"] == name:
            return p["playlistId"]
    return yt.create_playlist(
        title=name,
        description="Imported from PC local music pipeline"
    )

def best_match(results):
    for r in results:
        if r.get("resultType") == "song":
            return r
    return None

# -------- main --------
df = pd.read_csv(CSV_INPUT)
df["ytmusic_status"] = "SKIPPED"

playlist_id = get_or_create_playlist(PLAYLIST_NAME)

for i, row in df.iterrows():
    # Skip files marked as 'other' or not recognized
    if row.get("is_other") == True:
        continue
    
    artist = row.get("final_artist", "")
    title = row.get("final_title", "")
    
    if artist == "NOT_RECOGNIZED" or title == "NOT_RECOGNIZED":
        continue

    query = f"{artist} {title}"
    try:
        results = yt.search(query, filter="songs", limit=5)
        match = best_match(results)

        if not match:
            df.at[i, "ytmusic_status"] = "NOT_FOUND"
            continue

        yt.add_playlist_items(
            playlistId=playlist_id,
            videoIds=[match["videoId"]]
        )
        df.at[i, "ytmusic_status"] = "ADDED"

    except Exception as e:
        df.at[i, "ytmusic_status"] = f"ERROR"

df.to_csv(CSV_OUTPUT, index=False)
print("Done. Results written to", CSV_OUTPUT)
