# photo-server — Actual Build Steps and Deviations

Per `JCTsh-Build-Standards.md` §7 — this captures what actually happened versus `photo-server-claude-code-instructions.md`, since as-built rarely matches the plan exactly. Read the instructions doc for the intended sequence; read this for what actually occurred.

## Steps 1-10 — Base Build

Followed the instructions doc closely. Key as-built values (see `network.md` for the full reference):

- OS: **Ubuntu 26.04 LTS** (not a placeholder "current LTS" — confirmed via `lsb_release -a`)
- Drive mapping: Backup Plus 1TB → `/dev/sda` (916G), Momentus 640GB → `/dev/sdb` (586G)
- Immich version: pinned `IMMICH_VERSION=v3` in `.env`; running v3.0.1 as of 2026-07-09 (v3.0.2 available, routine update not yet applied)
- M8 has two identical-looking ethernet ports — only `eno1` carries the DHCP lease; the other silently drops network if used by mistake

## Step 11 — Quality Pass: Skipped by Decision

The planned manual pre-import quality pass (moving blurry/duplicate/screenshot candidates to an `_archive` folder) was **not done**. Decision made 2026-07-04: rely entirely on Immich's built-in CLIP-based duplicate detection plus an ongoing "mark favorites" habit instead of a one-time manual review. See `migration.md` and `backlog.md` CARD-0028 (optional automated quality scan, not started).

## Step 12 — Migration: Far From Clean

Joseph's import required **5 restarts** (1 disk-space crash, 2 crashes from `immich-go`'s default `--on-errors stop`, 2 clean partial completions) before both fixes (`--on-errors continue`, drive relocation) were in place. Robin's import ran clean in one pass. Full incident writeup, final counts, and the later CARD-0039 re-verification (which found 3,433 assets that had still gone missing despite all this) are in `migration.md`.

## Step 13 — Face Naming: Not Tracked (decided 2026-07-09)

Joseph decided to name recognized faces "catch as catch can" over time rather than as a discrete tracked task. See `photo-server-claude-code-instructions.md` Step 13 for the decision note. ML processing itself is fully complete (CARD-0037).

## Step 14 — Deletion Logging: Moved to `photo-tv-display` (decided 2026-07-09)

This step will be tracked under the `photo-tv-display` component's own build instructions when that work starts, not here. See `photo-server-claude-code-instructions.md` Step 14 for the original content, retained there for reference.

## Step 15 — Node.js: Done Late (2026-07-09)

Installed well after the original build (Node v24.18.0, npm v11.16.0 via NodeSource) — this step had been sitting undone since the initial build and was only caught and completed during a documentation catch-up pass.

## Beyond the Original Plan

Several things were built that aren't in the original instructions doc at all:

- **`photo-server-heartbeat.py`** (CARD-0029) — MQTT heartbeat to the JCTsh log dashboard, checking Docker container health *and* (after CARD-0032) actual storage read/write access inside the container, not just container status
- **Scheduled weekly reboot** (CARD-0035) with dashboard visibility (CARD-0036) — `core/maintenance/scheduled-reboot-m8.service`/`.timer` and `reboot-complete-m8.service`, requiring `mosquitto-clients` to be installed (the heartbeat script uses Python `paho-mqtt` instead, so the CLI wasn't already present)
- **CARD-0037** — found and fixed a large gap where ML processing (face detection/recognition, CLIP smart search, OCR, duplicate detection) had never run on ~11-92% of the library depending on job type, for both accounts
- **CARD-0039** — a second gap, found by re-running `immich-go` for real against the retained Takeout zips: 3,433 assets were genuinely missing from Immich entirely, not just missing ML processing

## Step 10 — Mobile Sync: Confirmed Working (2026-07-10)

Both phones are actively syncing. Most recent assets checked directly via the API: Joseph's Pixel 10 Pro XL uploaded a photo at 2026-07-09 21:24 (taken 2026-07-09 02:08); Robin's Pixel 7 uploaded photos as recently as 2026-07-10 00:31. No outstanding action here.

## CARD-0030 — Resolved (2026-07-10)

The single-drive backup design in the original instructions (Momentus 640GB mirroring the full 1TB primary) turned out to be undersized once the library grew past ~624GB. Replaced with a split-by-account architecture across two drives — see `backup.md` for the full incident and final verified state (Joseph 420G, Robin 207G, zero errors, weekly cron active).
