# Canonize (YTM)

## Context
In the old days, MP3 players had to have a folder with downloaded files from the internet. But now that I am using YouTube Music, I wanted to have the same files that I had in my library but the canonical official version in my YouTube Music playlist.

## What the project does
Canonize (YTM) is an automation pipeline designed to modernize your local music library. It performs the following steps:
1.  **Scans** a local directory (`input_music_to_id`) for MP3 files.
2.  **Identifies** tracks using existing metadata (ID3 tags) and audio fingerprinting (AcoustID) to fill in gaps.
3.  **Normalizes** data to fix typos and group similar artist names.
4.  **Searches** YouTube Music for the official versions of these songs.
5.  **Adds** the found songs to a dedicated YouTube Music playlist.

## Why the project is useful
Manually searching for hundreds or thousands of local songs on a streaming service is time-consuming. This tool automates the migration process, helping you preserve your curated collection while moving to a modern streaming platform. It handles messy file names and missing tags to find the best match available online.

## How users can get started

### Prerequisites
You will need Python installed on your machine. You also need to install the required dependencies:

```bash
pip install pandas ytmusicapi mutagen rapidfuzz pyacoustid
```

*Note: For the audio fingerprinting to work, you may need `fpcalc` (Chromaprint) installed on your system path.*

### Setup
1.  **Authentication**: This project uses `ytmusicapi`. You must generate a `browser.json` file to authenticate with your account.
    *   Run `ytmusicapi oauth` in your terminal and follow the instructions.
    *   Place the generated `browser.json` file in the root directory of this project.
    *   If you have any issues with the authentication process, please visit: https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html
2.  **AcoustID API Key**:
    *   To identify songs via audio fingerprinting, an AcoustID API Key is required.
    *   You can generate one at: https://acoustid.org/new-application
    *   The script will ask for this key during execution, or you can set it as an environment variable named `ACOUSTID_KEY`.
3.  **Music Folder**:
    *   Run `music_pipeline.py` once to generate the folder structure, or manually create a folder named `input_music_to_id`.
    *   Place your MP3 files inside `input_music_to_id`.

### Usage
The process is divided into two scripts:

1.  **Process Local Files**:
    Run the pipeline to identify and curate your local music.
    ```bash
    python music_pipeline.py
    ```
    Follow the on-screen prompts. This will generate a `final_curated.csv` file in the `output_files` directory.

2.  **Upload to YouTube Music**:
    Once the CSV is generated, run the `ytmusic_playlist_commit.py` script to create the playlist.
    ```bash
    python ytmusic_playlist_commit.py
    ```

## Where users can get help
If you have trouble setting up or running the script, please open an issue in this repository describing the problem.

## Who maintains and contributes to the project
This project is maintained by **Vyst**.

## Acknowledgments
Special thanks to **sigma67** for his [ytmusicapi](https://github.com/sigma67/ytmusicapi).

---

## Disclaimer
This is my first uploaded repo so pardon me if I do not comply with good practices or manners among the GitHub community.

**PLEASE LET ME KNOW** so I can improve my integration as a member of the coding community, as I do not take anything personal.

Feedback is welcome!