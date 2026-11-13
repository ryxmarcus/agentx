# Current Handoff: GTA VI Dual-Platform Auto Publisher (@ryxmarcus & @grand_theft.auto_vi)

## 1. Current Objective
Deploy and maintain an automated dual-platform publishing pipeline for GTA VI content across YouTube Shorts (**@ryxmarcus**) and Instagram Reels (**@grand_theft.auto_vi**), with high-converting audio narration and autonomous cloud staging.

## 2. Confirmed Changes & Active State (Nov 13, 2026)
- **Active Production Voiceover Deployed:**
  - **Chosen Voice:** `Brian Multilingual (Fast Hype)` (`en-US-BrianMultilingualNeural`)
  - **Pacing & Pitch Modulation:** `rate="+6%"`, `pitch="-2Hz"`.
  - **Colab Studio V3 (`Google_Veo_YouTube_Shorts_Studio_V3.ipynb`):**
    - Cell 4: Configured default voice to `en-US-BrianMultilingualNeural`, `rate="+6%"`, `pitch="-2Hz"`.
    - Cell 10: Updated `synthesize_narration` to pass dynamic rate and pitch to `edge_tts.Communicate`.
    - Cell 20: Upgraded interactive Dashboard dropdown with 5 custom-tuned presets (Brian Multilingual, Andrew Multilingual, Ryan UK, Christopher Deep, Roger Gritty) and real-time reactive voice listener.
    - Synced directly to live Google Colab tab in Chrome (`drive/1FFXfaYhaRFJ_IASic0S00sfjULLNWOWg`) and saved to Google Drive via CDP.
  - **Local Automation Engine:**
    - `youtube_automation/config.py` and `youtube_automation/tts_engine.py` updated and verified.
- **Audition Assets in User Downloads:**
  - `TEST_1_Brian_Multilingual_FastHype.mp3` (Active)
  - `TEST_2_Andrew_Multilingual_Trailer.mp3`
  - `TEST_3_Ryan_UK_CinematicDocumentary.mp3`
  - `TEST_4_Christopher_DeepStoryteller.mp3`
  - `TEST_5_Roger_LaidbackGritty.mp3`
- **Google Apps Script Cloud Publisher (Version 4.0):**
  - Project `15ceSNNCmZeXyn9tk4QsSbCVMHFjFvHGzBkTRkOJ6nOunjvz1hqWIM15E` active with triggers at 11:00 AM, 1:00 PM, 7:30 PM IST.
- **Instagram Profile Status:**
  - High-converting SEO bio live on `@grand_theft.auto_vi`. Awaiting Facebook Page link + `IG_USER_ID` and `IG_ACCESS_TOKEN` for Meta Graph API publishing.

## 3. Next Steps
1. In Google Colab, click **"1. Generate New Story"** and **"2. Generate Video"** to render a fresh video with the new Brian Multilingual hype narration.
2. Preview audio and video in the Colab dashboard, run **Quality Check**, and click **"Approve Video"** to stage it for cloud publishing.
3. Link Facebook Page to `@grand_theft.auto_vi` to unlock automated Instagram Reels uploads.
