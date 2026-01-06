import os
import sys
import re
import csv
import ast
import shutil
import pandas as pd
from mutagen.easyid3 import EasyID3
from rapidfuzz import fuzz
import acoustid

# ---------------- CONFIG ----------------
MUSIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "input_music_to_id")
OUTPUT_FILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_files")
ACOUSTID_KEY = os.getenv("ACOUSTID_KEY")
SIMILARITY_THRESHOLD = 85
JUNK_PATTERNS = re.compile(r"(track\s*\d+|unknown|whatsapp|audio\d+)", re.I)

FILE_STAGE1 = os.path.join(OUTPUT_FILES_DIR, "stage1_raw.csv")
FILE_STAGE2 = os.path.join(OUTPUT_FILES_DIR, "stage2_normalized.csv")
FILE_STAGE3 = os.path.join(OUTPUT_FILES_DIR, "stage3_clusters.csv")
FILE_STAGE4 = os.path.join(OUTPUT_FILES_DIR, "stage4_other.csv")
FILE_STAGE5 = os.path.join(OUTPUT_FILES_DIR, "stage5_acoustid.csv")
FILE_STAGE6 = os.path.join(OUTPUT_FILES_DIR, "final_curated.csv")

# Create the output directory if it doesn't exist
os.makedirs(OUTPUT_FILES_DIR, exist_ok=True)

# Check for AcoustID Key if Stage 5 is not yet complete
if not ACOUSTID_KEY and not os.path.exists(FILE_STAGE5):
    print("AcoustID API Key is required for Stage 5.")
    ACOUSTID_KEY = input("Please enter your AcoustID API Key: ").strip()

if not os.path.exists(MUSIC_DIR):
    os.makedirs(MUSIC_DIR)
    print(f"A folder named '{os.path.basename(MUSIC_DIR)}' was created in the repository, please place the music files in there to identify them and restart the process")
    sys.exit()

# ---------------- PRE-CLEANUP ----------------
# Move non-mp3 files to a designated folder
NOT_MP3_DIR = os.path.join(MUSIC_DIR, "not_mp3_files")

for root, dirs, files in os.walk(MUSIC_DIR):
    # Skip the not_mp3_files directory to avoid recursion
    if "not_mp3_files" in dirs:
        dirs.remove("not_mp3_files")

    for f in files:
        if not f.lower().endswith(".mp3"):
            if not os.path.exists(NOT_MP3_DIR):
                os.makedirs(NOT_MP3_DIR)
            
            src_path = os.path.join(root, f)
            dst_path = os.path.join(NOT_MP3_DIR, f)
            
            # Handle duplicate filenames by appending a counter
            base, ext = os.path.splitext(f)
            counter = 1
            while os.path.exists(dst_path):
                dst_path = os.path.join(NOT_MP3_DIR, f"{base}_{counter}{ext}")
                counter += 1
            
            try:
                shutil.move(src_path, dst_path)
                print(f"Moved non-mp3 file: {os.path.basename(dst_path)}")
            except Exception as e:
                print(f"Error moving {f}: {e}")

if not any(f.lower().endswith(".mp3") for _, _, files in os.walk(MUSIC_DIR) for f in files):
    print("no music to id inside the {os.path.basename(MUSIC_DIR)} folder, please add some mp3 files and restart the process")
    sys.exit()

# ---------------- UTIL ----------------
def pause(stage):
    input(f"\n=== {stage} complete. Review CSV. Press ENTER to continue ===\n")

def normalize(text):
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()

# ---------------- STAGE 0+1 ----------------
#(Raw Metadata): The script scans the music folder, locates all .mp3 files, 
#and extracts their current ID3 tags (Artist, Title, Album) exactly as they are. 
#This information is then saved into a "stage1_raw.csv" inside the output_files folder. 
if os.path.exists(FILE_STAGE1):
    print(f"Resuming Stage 1 from {os.path.basename(FILE_STAGE1)}")
    df = pd.read_csv(FILE_STAGE1).fillna("")
else:
    rows = []
    for root, _, files in os.walk(MUSIC_DIR):
        for f in files:
            if f.lower().endswith(".mp3"):
                path = os.path.join(root, f)
                try:
                    tags = EasyID3(path)
                    artist = tags.get("artist", [""])[0]
                    title = tags.get("title", [""])[0]
                    album = tags.get("album", [""])[0]
                except Exception as e:
                    print(f"Error reading tags for {path}: {e}")
                    artist = title = album = ""
                rows.append({
                    "path": path,
                    "artist": artist,
                    "title": title,
                    "album": album
                })

    df = pd.DataFrame(rows)
    df.to_csv(FILE_STAGE1, index=False)
    pause("Stage 1 — Raw metadata")

# ---------------- STAGE 2 ----------------
# (Normalization): The script takes the raw data and cleans the text. 
# It converts everything to lowercase and removes punctuation. 
# This step is crucial for the computer to recognize that 
# "The Beatles" and "the beatles." are the same entity.
if os.path.exists(FILE_STAGE2):
    print(f"Resuming Stage 2 from {os.path.basename(FILE_STAGE2)}")
    df = pd.read_csv(FILE_STAGE2).fillna("")
else:
    df["artist_norm"] = df["artist"].apply(normalize)
    df["title_norm"] = df["title"].apply(normalize)
    df.to_csv(FILE_STAGE2, index=False)
    pause("Stage 2 — Normalization")

# ---------------- STAGE 3 ----------------
# (Fuzzy Grouping / Clustering): Using fuzzy logic (rapidfuzz), 
# the script identifies artist names or song titles that are highly similar 
# (e.g., an 85% match or higher) and groups them under a single canonical name. 
# This effectively corrects minor typos.
if os.path.exists(FILE_STAGE3):
    print(f"Resuming Stage 3 from {os.path.basename(FILE_STAGE3)}")
    df = pd.read_csv(FILE_STAGE3).fillna("")
else:
    def cluster(series):
        canon = []
        mapping = {}
        for item in series:
            found = False
            for c in canon:
                if fuzz.ratio(item, c) >= SIMILARITY_THRESHOLD:
                    mapping[item] = c
                    found = True
                    break
            if not found:
                canon.append(item)
                mapping[item] = item
        return mapping

    artist_map = cluster(df["artist_norm"].unique())
    title_map = cluster(df["title_norm"].unique())

    df["artist_canon"] = df["artist_norm"].map(artist_map)
    df["title_canon"] = df["title_norm"].map(title_map)

    df.to_csv(FILE_STAGE3, index=False)
    pause("Stage 3 — Fuzzy clusters")

# ---------------- STAGE 4 ----------------
# ("Other" Classification): The script identifies files that are likely 
# not valid commercial songs based on specific patterns 
# (such as "WhatsApp Audio," "Track 01," or very short titles). 
# These are flagged as is_other so they can be filtered out or reviewed manually later.
if os.path.exists(FILE_STAGE4):
    print(f"Resuming Stage 4 from {os.path.basename(FILE_STAGE4)}")
    df = pd.read_csv(FILE_STAGE4).fillna("")
else:
    df["is_other"] = (
        df["title_canon"].str.match(JUNK_PATTERNS) |
        (df["title_canon"].str.len() < 3)
    )

    df.to_csv(FILE_STAGE4, index=False)
    pause("Stage 4 — OTHER classification")

# ---------------- STAGE 5 ----------------
#(Acoustic Identification - AcoustID): For songs missing an Artist ID 
# (fields that remain empty after normalization), 
# the script generates an audio "fingerprint." 
# It then queries the AcoustID database to identify the song by 
# "listening" to the audio rather than relying on metadata tags.
if os.path.exists(FILE_STAGE5):
    print(f"Resuming Stage 5 from {os.path.basename(FILE_STAGE5)}")
    df = pd.read_csv(FILE_STAGE5).fillna("")
else:
    def acoustid_lookup(path):
        try:
            duration, fp = acoustid.fingerprint_file(path)
            results = acoustid.lookup(ACOUSTID_KEY, fp, duration)
            return results
        except Exception as e:
            print(f"AcoustID lookup failed for {path}: {e}")
            return None

    df["acoustid_result"] = None

    for i, row in df[df["artist_canon"] == ""].iterrows():
        df.at[i, "acoustid_result"] = str(acoustid_lookup(row["path"]))

    df.to_csv(FILE_STAGE5, index=False)
    pause("Stage 5 — Acoustic identification")

# ---------------- STAGE 6 ----------------
if os.path.exists(FILE_STAGE6):
    print(f"Resuming Stage 6 from {os.path.basename(FILE_STAGE6)}")
    df = pd.read_csv(FILE_STAGE6).fillna("")
else:
    def extract_acoustid_meta(result_str):
        try:
            if pd.isna(result_str) or str(result_str) == "None":
                return "", ""
            
            # Parse the stringified dictionary from Stage 5
            data = ast.literal_eval(result_str)
            
            if not data or "results" not in data or not data["results"]:
                return "", ""
                
            # Get the best match
            best = data["results"][0]
            if "recordings" not in best or not best["recordings"]:
                return "", ""
                
            recording = best["recordings"][0]
            title = recording.get("title", "")
            
            artists = recording.get("artists", [])
            artist = artists[0].get("name", "") if artists else ""
            
            return artist, title
        except Exception as e:
            return "", ""

    # Extract info
    extracted = df["acoustid_result"].apply(extract_acoustid_meta)
    df["acoustid_artist"] = extracted.apply(lambda x: x[0])
    df["acoustid_title"] = extracted.apply(lambda x: x[1])

    # Create final curated columns
    df["final_artist"] = df["artist_canon"]
    df["final_title"] = df["title_canon"]

    # Fill gaps with AcoustID data
    mask = (df["final_artist"] == "") & (df["acoustid_artist"] != "")
    df.loc[mask, "final_artist"] = df.loc[mask, "acoustid_artist"]
    df.loc[mask, "final_title"] = df.loc[mask, "acoustid_title"]

    # Label unrecognized
    df.loc[df["final_artist"] == "", "final_artist"] = "NOT_RECOGNIZED"
    df.loc[df["final_title"] == "", "final_title"] = "NOT_RECOGNIZED"

    # Save final curated list
    final_cols = ["path", "final_artist", "final_title", "is_other"]
    df[final_cols].to_csv(FILE_STAGE6, index=False)
    pause("Stage 6 — Final Curation")

print("\nPipeline complete. Results written to final_curated.csv")
