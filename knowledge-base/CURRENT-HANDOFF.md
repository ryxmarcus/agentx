# Current Handoff: GTA VI Dual-Platform Auto Publisher (@ryxmarcus & @grand_theft.auto_vi)

## 1. Current Objective
Deploy and maintain an automated dual-platform publishing pipeline for GTA VI content across YouTube Shorts (**@ryxmarcus**) and Instagram Reels (**@grand_theft.auto_vi**), with high-converting audio narration and autonomous cloud staging.

## 2. Confirmed Changes & Active State (Nov 13, 2026)
- **Google Vids Voiceover Integration & Studio V3.1 Pipeline Upgraded:**
  - **Pipeline Notebook:** [`C:\Users\Rahul pc\Downloads\Google_Veo_YouTube_Shorts_Studio_V3_1_GoogleVids.ipynb`](file:///C:/Users/Rahul%20pc/Downloads/Google_Veo_YouTube_Shorts_Studio_V3_1_GoogleVids.ipynb) (and synced to `Google_Veo_YouTube_Shorts_Studio_V3.ipynb`).
  - **Google Vids Built-in Preset:** `Google Vids: Ryan (British Documentary)` (`en-GB-RyanNeural`, `rate="+5%"`, `pitch="-3Hz"`).
  - **Custom Google Vids Audio Import:** Automatically checks for `google_vids_voiceover.mp3` in `STUDIO_DIRS["voiceovers"]` and uses local Whisper (`base.en`) to extract word-level subtitle alignment timestamps.
  - **Audio Mastering Chain (Cell 10):** Mastered for phone speakers with 48 kHz stereo AAC (192 kbps), 90 Hz HPF, -3.5 dB @ 240 Hz (de-mud), +2.5 dB @ 3.2 kHz (vocal presence), 2.2:1 gentle compression, and -16 LUFS target loudness (-1.5 dBTP limiter).
  - **Publishing Staging Fix (Cell 18):** Decoupled hard Google Cloud Storage dependency. The approval gate now ALWAYS copies `.mp4`, `.json`, and `_thumb.jpg` directly into Google Drive's `Publishing_Queue` folder for our Google Apps Script Version 4.0 scheduler (runs at 11:00 AM, 1:00 PM, 7:30 PM IST), with GCS upload acting as an optional fallback.
  - **Dashboard Upgraded (Cell 20):** Dropdown includes Google Vids presets and custom audio import mode.
- **Local Engine & Rendered Assets:**
  - `youtube_automation/config.py` and `youtube_automation/video_engine.py` updated to 48 kHz stereo mastering.
  - Rendered files in Downloads:
    - [`C:\Users\Rahul pc\Downloads\GTA6_Ryan_RockstarTrailer_Reel.mp4`](file:///C:/Users/Rahul%20pc/Downloads/GTA6_Ryan_RockstarTrailer_Reel.mp4) (0:35, 10.87 MB)
    - [`C:\Users\Rahul pc\Downloads\GTA6_Brian_FastHype_Reel.mp4`](file:///C:/Users/Rahul%20pc/Downloads/GTA6_Brian_FastHype_Reel.mp4) (0:34, 10.73 MB)

## 3. Next Steps
1. In Colab, open or upload `Google_Veo_YouTube_Shorts_Studio_V3_1_GoogleVids.ipynb` to [`https://colab.research.google.com/drive/1LbPgg-yZM9C3rTLQCilvZVYGjcol_YMz`](https://colab.research.google.com/drive/1LbPgg-yZM9C3rTLQCilvZVYGjcol_YMz).
2. Choose between:
   - **Mode A (Built-in Google Vids Voice):** Keep dropdown on `Google Vids: Ryan (British Documentary)` to generate with 48 kHz studio mastering.
   - **Mode B (External Google Vids File):** Drop your Google Vids audio track as `google_vids_voiceover.mp3` into `YouTube_Shorts_Studio/Voiceovers/` and select `Import Custom Google Vids Audio File`.
3. Click "Approve Video" — it stages directly into Google Drive `Publishing_Queue` where Google Apps Script automatically publishes to YouTube Shorts and Instagram Reels.
