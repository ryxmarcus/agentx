# Current Handoff: GTA VI Dual-Platform Auto Publisher (@ryxmarcus & @grand_theft.auto_vi)

## 1. Current Objective
Deploy and maintain an automated dual-platform publishing pipeline for GTA VI content across YouTube Shorts (**@ryxmarcus**) and Instagram Reels (**@grand_theft.auto_vi**), with high-converting audio narration and autonomous cloud staging.

## 2. Confirmed Changes & Active State (Nov 13, 2026)
- **Permanent Production Voiceover Finalized:**
  - **Chosen Voice:** `TEST_3_Ryan_UK_CinematicDocumentary` (`en-GB-RyanNeural`)
  - **Pacing & Pitch Modulation:** `rate="+5%"`, `pitch="-3Hz"`.
  - **Style Profile:** Prestigious, authoritative BBC/Rockstar Games documentary trailer tone.
  - **Rendered Videos:**
    - [`C:\Users\Rahul pc\Downloads\GTA6_Ryan_RockstarTrailer_Reel.mp4`](file:///C:/Users/Rahul%20pc/Downloads/GTA6_Ryan_RockstarTrailer_Reel.mp4) (0:35 duration, 1080x1920)
    - [`C:\Users\Rahul pc\Downloads\GTA6_Brian_FastHype_Reel.mp4`](file:///C:/Users/Rahul%20pc/Downloads/GTA6_Brian_FastHype_Reel.mp4) (0:34 duration, 1080x1920)
  - **Colab Studio V3 (`Google_Veo_YouTube_Shorts_Studio_V3.ipynb`):**
    - Configured default voice to `en-GB-RyanNeural` (+5% speed, -3Hz pitch).
    - Set default dashboard dropdown to `en-GB-RyanNeural`.
    - Live-synced to Google Colab and saved to Google Drive.
  - **Local Automation Engine:**
    - `youtube_automation/config.py` and `youtube_automation/tts_engine.py` updated to `en-GB-RyanNeural`.
- **Google Apps Script Cloud Publisher (Version 4.0):**
  - Project `15ceSNNCmZeXyn9tk4QsSbCVMHFjFvHGzBkTRkOJ6nOunjvz1hqWIM15E` active with triggers at 11:00 AM, 1:00 PM, 7:30 PM IST.
- **Instagram Reels Activation:**
  - High-converting SEO bio live on `@grand_theft.auto_vi`. Awaiting Facebook Page link + `IG_USER_ID` and `IG_ACCESS_TOKEN` for Meta Graph API publishing.

## 3. Next Steps
1. User watches [`C:\Users\Rahul pc\Downloads\GTA6_Ryan_RockstarTrailer_Reel.mp4`](file:///C:/Users/Rahul%20pc/Downloads/GTA6_Ryan_RockstarTrailer_Reel.mp4).
2. All future videos generated in Colab and local engine will use `en-GB-RyanNeural` by default.
3. Link Facebook Page to `@grand_theft.auto_vi` to enable autonomous Instagram Reels uploads.
