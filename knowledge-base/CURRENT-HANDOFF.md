# Career Ops Explorer source-access incident

- **Objective:** explain why the Explorer page at `127.0.0.1:3000/explore` showed “The scan ran, but couldn’t reach any sources.”
- **Confirmed local evidence:** all four required public ATS directory requests returned `HTTP/1.1 403 Forbidden` with `Server: Zscaler/6.2`: `greenhouse_companies.json`, `lever_companies.json`, `ashby_companies.json`, and `workday_companies.json` under `https://raw.githubusercontent.com/Feashliaa/job-board-aggregator/main/data/`.
- **Not the cause:** DNS resolves `raw.githubusercontent.com` to GitHub addresses; `scan-ats-full.mjs` and `portals.yml` exist; no source cache exists at `job/career-ops/data/cache/ats-companies`, so there is no stale fallback dataset.
- **Impact:** each selected source reports an empty dataset; Explorer receives `companiesScanned: 0` and correctly renders the degraded card. No ATS board scan is attempted, so changing scan concurrency/timeouts will not help.
- **Required next step:** request Zscaler/network allow-list access for `raw.githubusercontent.com` (at minimum the dataset path above) or provide an approved internal mirror. Once access is approved, retry Discover; the scanner will seed its 24-hour local source cache automatically.
- **No code change applied:** this is an external egress policy block, not a scanner defect. Do not apply a proxy bypass, disable TLS verification, or fabricate cache data.
- **Evidence:** `.tmp/career-ops-source-check.txt`, `.tmp/career-ops-403-detail.txt`, `.tmp/career-ops-prereqs.txt` (local temporary diagnostics; no credentials recorded).

---

# Agent CLI audit and optimisation (2026-11-17)

## Objective
Fresh review and performance optimisation of the canonical iTOPAZ CLI in this workspace. Canonical entrypoint: `agentx.py`; `agent/itopaz_agent.py` is a compatibility shim.

## Confirmed changes
- **Startup performance:** `core/project_manager.py` previously ran 36 Git subprocesses while importing. Git state is now lazy, cached for `ITOPAZ_GIT_CACHE_TTL` seconds (default 30), uses two calls per repository, and project-list refreshes run in parallel.
- **Measured locally:** `--doctor` improved from 4.77s to 0.45s; `--search "EBX auto heal"` from 4.55s to 0.44s; `--list-projects` completed in 1.56s.
- **Entrypoints:** repaired `agent/bin/itopaz-agent`, which incorrectly targeted non-existent `agent/agentx.py`; it now executes `${AGENT_ROOT}/agentx.py`. The compatibility shim remains functional.
- **Safety:** command history is now disabled while `.agent-operation-lock.json` is locked, matching the default no-write policy.
- **Configuration/docs:** the local node registry points to `agentx.py`; root and nested READMEs now use the canonical CLI name and correctly document root-level `config.json`.
- **Legacy code:** archived (not deleted) the untracked, unused `agent/core/` snapshot at `scratch/legacy-agent-core-20261117/`.

## Validation
- Recursive Python compile: passed (`rc=0`).
- Unit tests: 25 passed in 13.327s.
- `python agentx.py --doctor`: passed; local node detected, operation lock enabled, all three knowledge sources present, workers 1 and 2 enabled with deployed agents and configured keys present.
- `python agent/itopaz_agent.py --nodes`: passed.
- Static shell-launcher contract and stale reference scan: passed; no references remain to `agent/agentx.py`, `python itopaz_agent.py`, or runtime `agent/config.json`.

## Current source-control state
Changes remain uncommitted in the local `main` working tree for `https://github.com/ryxmarcus/agentx.git`. No remote/server configuration was changed by this audit.

## Remaining follow-ups
- `scripts/` and the repository root contain substantial unrelated browser-automation artifacts, screenshots, PDFs, and job-application files. They were deliberately not moved or deleted; organise/archive them only with explicit approval.
- The agent’s `--serve` mode binds to all interfaces. It has route-level bearer authentication except `/health`, but deployment exposure and token values were not reviewed in this audit.
- The operation lock is an application guard, not an operating-system or SSH authorization boundary.

---

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
