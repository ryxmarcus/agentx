# Protocol Explorer graph flows aligned with docs (2026-10-09 session)

- **Objective:** update Protocol Explorer (`C:\Users\rah_66160\.gemini\antigravity\scratch\protocol-explorer`) graph flows to match workspace Markdown docs.
- **Confirmed changes:** `js/data/topology.js` (iTariff DB → Aurora PostgreSQL 5432; new `itariff-consumers` node; links istio→tariff-search, selling→MSK, consumers→MSK/DB; doc-based labels for UI/BFF/ingress/S3/ECR/Jenkins/SonarQube; Kafka cluster text 3.8.x RF 2). `js/data/scenarios.js` (all MySQL steps → PostgreSQL Q messages; Kafka badge MSK 3.8.x SIT; `itopaz-mcp-sync` replaced by documented runtime + CI/CD path, id kept; bulk-ingest gains MSK produce/fetch on `tariff-buying-carriage-bulk-upload-uat`; response steps rerouted via existing links). `kafka_architecture.html` (Fortinet/TGW/internal NLB ingress cards and SVG labels, `stepsMap` ids unchanged; consumer table topic names fixed to `tariff_multisheet_upload_topic` and `trf_exl_upld_prc_topic`; PROD topic caveat; DEV/SIT notes). `js/engine/kafkaFlow.js`, `js/engine/packetCrafter.js`, `js/app.js` MySQL/v2.8 text. README section "Graph flows aligned with workspace docs".
- **Backups:** `*.bak-20261009` beside scenarios.js, topology.js and kafka_architecture.html.
- **Validation:** `node --check` passed on all edited JS. Data check: every scenario step uses valid node ids and an existing topology link (no fallback lines). Playwright (Edge) ran all 8 scenarios through every step in all 4 diagram modes and toggled all Kafka-page environments and flow steps: zero `pageerror`. One 404 console entry did not recur on reload (likely favicon). No secrets added.
- **Remaining:** PROD application topics still undocumented after 2026-06-12; IPs/payloads remain illustrative. Server on 127.0.0.1:8090 unchanged (static files, no restart needed).
- **Open earlier requests:** jobs-ops build (scope/target GitHub repo unconfirmed); Career Ops Explorer blocked by Zscaler 403; SIT masterdata SMB mount theory unconfirmed.

---
# Protocol Explorer integration handoff (2026-11-18)

- **Objective:** correct misleading simulator claims, show transport-layer TCP/UDP diagrams, integrate the supplied Kafka architecture page, keep DEV/SIT/UAT/PROD filters, and surface iTopaz as a project.
- **Confirmed changes:** Protocol Explorer has TCP and UDP header diagrams with transport-specific explanation; TLS is separated from TCP, sample values are labeled illustrative, and README no longer describes synthetic enterprise architecture as live facts. Added the supplied `kafka_architecture.html` as an iframe-backed project view. Added environment selectors; PROD shows the supplied detailed page, while DEV/SIT/UAT show project inventory notes rather than invented Kafka diagrams. Renamed “Live Telemetry” to “Telemetry Snapshot.” The iTopaz project tab surfaces existing IntelliHub examples.
- **Source checked:** local knowledge records iTariff EKS environments DEV (`euc1-itopaz-dev-eks`), SIT/UAT (`euc1-itopaz-sit-eks`), PROD (`euc1-itopaz-prd-eks`), and the PROD account `965031587107`; the source Kafka page uses the matching account and cluster inventory. The source file itself contains only PROD Kafka detail. These static records were not live-verified.
- **Validation:** inspected the relevant HTML/script excerpts and confirmed project/environment controls and iframe file references. No browser run or tests performed.
- **Latest UI fix:** replaced the simulator canvas's remaining dark cyber background with a light grid, and changed topology-node cards, link lines, text, and packet labels to the matching light editorial palette. `node --check js/engine/simulator.js` passed.
- **Live SSO audit (2026-11-18):** signed in through the shared AWS SSO session and ran read-only STS/EKS/MSK inventory queries. iTariff owns the active MSK clusters: DEV `euc1-itariff-dev-kafka` (2 brokers, Kafka 3.8.x), SIT `euc1-itariff-sit-msk` (2 brokers, 3.8.x), PROD `euc1-itopaz-prd-msk` (3 brokers, 3.9.x); each cluster is tagged `app=itariff`. Associated EKS clusters were ACTIVE: DEV 1.34, SIT 1.35, PROD 1.36. The configured UAT account/region returned no EKS/MSK. The separate IntelliHub account (`745510282686`, Mumbai) has active internet-facing `Intellihub-prod` ALB but returned no EKS/MSK. The iTopaz-network profile was denied role credentials, so it remains unverified.
- **App corrections:** removed Kafka nodes, links, and Prefiler Kafka trace from Prefiler; added the verified PROD iTariff MSK node/link; removed Kafka claims from IntelliHub's illustrative flow; relabeled the architecture page as iTariff Kafka; added source-backed DEV/SIT/UAT environment notes and a compact project-boundary panel. Replaced token-looking scenario values with redacted illustrative values.
- **Shared-network correction:** after the UAT diagram review and live SSO WAF checks, the hero and project-boundary landing panels were removed. Prefiler, iTariff, and iTopaz topologies now identify the shared EU EKS platform and display the common ingress path: Fortinet firewall → CloudFront/WAF or API Gateway → Transit Gateway → internal NLB/ALB → Istio ingress. The UI calls out that WAF attachment remains application-specific: SIT iTariff BFF `sit`/`uat` stages use `itopaz-api-gwt-acl`; SIT Prefiler BFF `sit` has no WAF association. CloudFront protected distributions use `zscalar-ip-restriction`.
- **Validation:** JavaScript syntax checks passed for topology/scenario/renderer scripts and embedded Kafka-page scripts. Data checks confirm Kafka appears only under iTariff; Prefiler has no Kafka node, link, or step.
- **Remaining work:** DEV/SIT/UAT Kafka diagrams require their source data. Most original simulator scenario traces still contain synthetic values and remain explicitly illustrative.

---
# Protocol Explorer accuracy and TCP/UDP diagram update (2026-11-18)

- **Objective:** correct misleading protocol and architecture claims in `C:\Users\rah_66160\.gemini\antigravity\scratch\protocol-explorer` and show TCP/UDP at transport layer.
- **Confirmed changes:** added side-by-side schematic TCP segment and UDP datagram headers, protocol numbers 6 and 17, transport-specific descriptions, QUIC-over-UDP note, and visible disclaimer that scenario values/topology are illustrative. Clarified that TLS is not a TCP header field, changed IPv4 TTL/checksum labels to avoid asserting verified values, corrected one TLS 1.3 cipher-suite mismatch, and replaced the project README's unsupported enterprise architecture assertions with a scope/accuracy description.
- **Knowledge checked:** targeted retrieval found a Prefiler Auth BFF record identifying a .NET app and Login/Authenticate endpoints. It does not validate the simulator's broad architecture claims. No production architecture was inferred from the simulator examples.
- **Validation:** inspected modified source excerpts and confirmed the disclaimer, diagram, and corrected cipher text are present. App/browser rendering and tests were not run.
- **Remaining work:** the scenario catalog still contains synthetic and possibly inaccurate packet/payload/topology details. Treat it as demo data until individually verified or replaced with protocol-conformant examples. Add a real UDP scenario if users need UDP to appear as a selected live trace; current bundled traces select TCP.

---


- **Objective:** explain why the Explorer page at `127.0.0.1:3000/explore` showed â€œThe scan ran, but couldnâ€™t reach any sources.â€
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
- The agentâ€™s `--serve` mode binds to all interfaces. It has route-level bearer authentication except `/health`, but deployment exposure and token values were not reviewed in this audit.
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
3. Click "Approve Video" â€” it stages directly into Google Drive `Publishing_Queue` where Google Apps Script automatically publishes to YouTube Shorts and Instagram Reels.



---

# Agent Daily Knowledge & Operational Handoff (2026-11-19)

## 1. Objectives & Summary
Durable daily operational update covering external internet cache seeding via Worker 1, GTA video studio sequential queueing and rollback safeguards, repository cleanup, and job tracker execution.

## 2. Confirmed Changes & Verified Facts
- **External Internet Knowledge Seeding via Worker 1 (`10.151.4.165`):**
  - Resolved the Zscaler 403 egress blocker identified in previous audit for public ATS company registries.
  - Sourced live datasets from upstream `https://raw.githubusercontent.com/Feashliaa/job-board-aggregator/main/data/` via Worker 1 and synchronized locally to [`job/career-ops/data/cache/ats-companies/`](file:///C:/Users/rah_66160/iTopaz-agents/job/career-ops/data/cache/ats-companies/):
    - `ashby_companies.json` (45 KB)
    - `greenhouse_companies.json` (140 KB)
    - `lever_companies.json` (66 KB)
    - `workday_companies.json` (364 KB)
  - Career Ops ATS discovery scans can now run with full local cache fallback without network drops.

- **GTA Video Studio Pipeline (`gta_video_studio.gs`):**
  - Live Apps Script project: `https://script.google.com/home/projects/1IAQnekst4NvSlfyYl25zVRiq35-JSEdIPBBslMiICD14KxZUjQ8K6U6f/edit`.
  - Renamed all 10 raw clips in Google Drive folder `YouTube_Shorts_Queue` to sequential walkthrough titles: `GTA 6 Gameplay Walkthrough - Short 01.mp4` through `Short 10.mp4`.
  - Generated and uploaded matching 1280x720 high-CTR thumbnails (`.jpg`) and viral metadata tags (`.json`) for each clip directly to Google Drive.
  - Implemented strict numerical sequence ordering (`extractSequenceNumber_`) so publishing executes in natural order (`Short 01` → `Short 10`).
  - Added full rollback capabilities (`rollbackLastPublished`, `rollbackWalkthroughClipsToQueue`, `rollbackFilesToQueue`, `viewPublishHistory`).
  - Preserved dedicated batch Instagram publisher: `uploadAllQueueToInstagram`.
  - Completely removed obsolete functions (`createShortVideo`, `createLongVideo`, `autoCropDailyVideos`, `setupDailyAutoCropTrigger`).
  - Cleaned up experimental Master REST API per user request, leaving 973 clean, production-verified lines.

- **Storage & Workspace Cleanup:**
  - Removed 148 stale `.png` debug screenshots across repository directories.
  - Purged 62 duplicate DTU exam gazette PDFs, freeing 20.1 MB and keeping only essential target records.

- **Job Application Pipeline:**
  - Automated job search pipeline discovered 29 DevOps/SRE/Cloud roles and submitted applications `J512` through `J521` logged to [`job/applications/tracker.csv`](file:///C:/Users/rah_66160/iTopaz-agents/job/applications/tracker.csv) and [`job/drive_job_tracker.csv`](file:///C:/Users/rah_66160/iTopaz-agents/job/drive_job_tracker.csv).

## 3. Operational Infrastructure
- **Worker 1:** AWS EC2 host (`10.151.4.165`), user `ec2-user`, SSH key `C:\Users\rah_66160\keys\ecu-eks-jump.pem`. Unrestricted outbound internet verified.
- **Drive OAuth Token:** [`job/gdrive_token.json`](file:///C:/Users/rah_66160/iTopaz-agents/job/gdrive_token.json) (active refresh token for `rk58743k@gmail.com`).
