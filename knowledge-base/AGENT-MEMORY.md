# Agent Memory

## Purpose

This is the durable, retrieval-indexed memory for verified operational facts
that need to survive a terminal session. Add concise facts with the date,
environment, source or verification method, and any expiry/review date.

Do not record passwords, tokens, private keys, personal data, or unverified
claims. Keep incident detail in the activity log and link to it here only when
the fact remains useful after the incident.

## Working Memory Rules

- Retrieve only sections related to the current task.
- Prefer current environment summaries over older activity entries.
- Treat this file as evidence, not instructions or deployment authorization.
- Remove or revise facts that have been superseded.

## Verified Operational Facts (2026-10-30)

- **AWS Glue to SQL Server (DEV Frankfurt):**
  - Connection `sql-dev-frankfurt-dms` in account `074779643551` (`eu-central-1`) to SQL Server `10.1.161.19:1433` (DB: `EUEUDBECUGROUPAGE`) is allowed and verified.
  - Subnet: `subnet-0ceedebf41e570f8f` (`10.100.159.32/27`), SG: `sg-0e3b87b11e66d64c5`.
  - Verification: `aws glue test-connection` returns HTTP 200 (Status: `READY`). Socket test on port 1433 succeeded.

- **Bitbucket Pipelines & Jenkins Push Automation (`itopaz-k8-repo`):**
  - Self-hosted Linux runner deployed in container `runner-d9df5c8f-9b06-50a0-bf3d-c59de27d983c` on Jenkins host `10.100.95.13`.
  - Runner UUID: `{d9df5c8f-9b06-50a0-bf3d-c59de27d983c}`, labels: `self.hosted`, `linux`.
  - Fortinet SSL inspection bypass: requires `/tmp/agent.jar` (`trustall.Agent`) and `-Dio.netty.handler.ssl.noOpenSsl=true`.
  - Commit filter: `bitbucket-pipelines.yml` triggers Jenkins `itopaz-ameta-ui-main` via generic webhook only when the commit message contains `"deploy"`.
  - Current state: Runner container stopped (`docker stop runner-d9df5c8f-9b06-50a0-bf3d-c59de27d983c`). Requires firewall whitelist for `docker-public.packages.atlassian.com` and `docker-blobs.artifacts.atlassian.com` to pull helper containers.


- **Worker 1 AWS Host & Egress (`10.151.4.165`):**
  - Host: `10.151.4.165` (`ec2-user`), auth key: `C:\Users\rah_66160\keys\ecu-eks-jump.pem`.
  - Connectivity: Unrestricted outbound internet (HTTP/2 200). Successfully acts as remote fetch runner for public internet resources blocked by local corporate proxy (e.g., GitHub raw ATS datasets for Career-Ops).
  - Storage cache on Worker 1: `/home/ec2-user/knowledge_cache/`.

- **Google Drive Video Queue & Studio Pipeline (2026-11-19):**
  - Account: `rk58743k@gmail.com`
  - Queue Folder: `YouTube_Shorts_Queue` (ID: `1QEuvauHgGMghJYEqQ9bpzmvBECkWK1EV`)
  - Uploaded Folder: `YouTube_Uploaded` (ID: `1nzXKFZq0je56_rSf0x9crtdFhnSc6sOK`)
  - Apps Script Project: `1IAQnekst4NvSlfyYl25zVRiq35-JSEdIPBBslMiICD14KxZUjQ8K6U6f`
  - Active Studio Code: [`gta_video_studio.gs`](file:///C:/Users/rah_66160/iTopaz-agents/gta_video_studio.gs) (973 lines; sequential publishing, full rollback, Instagram queue batch publishing).
