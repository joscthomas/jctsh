# photo-server — Claude Code Instructions
**Author:** Joseph C Thomas (JCT)
**Purpose:** Step-by-step build instructions for Claude Code to execute the `photo-server` component — Immich self-hosted photo platform on the GMKtec M8 mini PC.
**Version:** 1.0
**Version description:** Initial release.
**Project:** JCTsh Photo Platform
**Status:** Ready for execution
**Related files:** `photo-server-phase1-planning.md`, `photo-server-phase2-planning.md`, `JCTsh-Build-Standards.md`, `jctsh-network.md`, `README.md`

---

## Step 0 — Read Required Context

Before any work begins, read:
- `JCTsh-Build-Standards.md` (repo root) — documentation and integration standards apply even though this is not an ESP32 component
- `photo-server-phase1-planning.md` and `photo-server-phase2-planning.md` (this component's planning history)
- `jctsh-network.md` (repo root) — current device/IP table
- `CLAUDE.md` (repo root) — existing JCTsh infrastructure, especially the DNS-pinning gotcha and Tailscale pattern

This component has no relationship to the ESP32/MQTT/Node-RED ecosystem. Most of the ESP32-specific standards in `JCTsh-Build-Standards.md` do not apply. The standards that do apply: documentation completeness (§7), additive-first integration (§6.1), parts inventory check (already confirmed none apply), and git as the version record (no version suffix on files in this repo).

---

## Pre-Build Checklist (Confirm Before Proceeding)

These must be confirmed complete before Step 1. If any are not yet done, stop and report back rather than proceeding.

- [ ] Windows 11 Pro product key captured via PowerShell (or confirmed as OEM digital license) and saved securely
- [ ] Both USB HDDs confirmed empty and available:
  - Seagate Backup Plus 1TB (P/N: 1KAAP1-501) — primary Immich library
  - Seagate Momentus 640GB in Insignia enclosure (P/N: 9RN134-030) — local backup
- [ ] Ubuntu Server LTS bootable USB created on the Windows machine
- [ ] M8 connected via wired ethernet directly to a gigabit LAN port on the router

---

## Step 1 — Install Ubuntu Server LTS

1. Boot the M8 from the Ubuntu Server LTS USB installer
2. Wipe the internal 512GB NVMe SSD and install Ubuntu Server LTS (current LTS release — verify version at ubuntu.com/download/server at time of install)
3. During install:
   - Hostname: `photo-server`
   - Username: match existing JCTsh convention (confirm with Joseph if unspecified — likely `jct` or `joseph`)
   - Enable OpenSSH server during install
   - Do not configure WiFi during install if ethernet is available — use wired connection
4. Set timezone to `America/Phoenix` post-install if not set during install:
   ```bash
   sudo timedatectl set-timezone America/Phoenix
   ```
5. Update system:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

**Report back:** Confirm hostname resolves as `photo-server.local` via mDNS (Avahi) from another device on the network. If mDNS is not working, install `avahi-daemon`:
```bash
sudo apt install -y avahi-daemon
```

---

## Step 2 — Network Configuration

1. Confirm wired ethernet connection is active:
   ```bash
   ip addr show
   ```
2. Note the DHCP-assigned IP address and the interface's MAC address
3. **Report the IP and MAC to Joseph** — he will reserve this IP on the router. Do not proceed to reserve it yourself; this is a router-side action outside Claude Code's scope.
4. Once Joseph confirms the IP reservation, update `jctsh-network.md` (repo root) with a new row:
   ```
   | photo-server | <reserved IP> | photo-server.local | <MAC> | Immich photo server + photo-tv-display Node.js server; wired gigabit direct to router, DHCP-reserved |
   ```

---

## Step 3 — Install Tailscale

1. Install Tailscale:
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   ```
2. Enroll in the existing JCTsh Tailscale account:
   ```bash
   sudo tailscale up
   ```
3. Authenticate via the URL provided (open in browser, sign in with the JCTsh Tailscale account)
4. Confirm the Tailscale IP assigned:
   ```bash
   tailscale ip -4
   ```
5. Update `jctsh-network.md` Tailscale table with the new entry:
   ```
   | photo-server | <tailscale IP> | Immich + photo-tv-display — reachable remotely for admin |
   ```

---

## Step 4 — Mount the USB HDDs

Two USB HDDs are mounted: Seagate Backup Plus 1TB (primary library) and Seagate Momentus 640GB in Insignia enclosure (local backup). Both are bus-powered 2.5" drives.

### 4a — Connect and Identify Both Drives

1. Connect both USB HDDs to the M8
2. Identify the devices:
   ```bash
   lsblk
   ```
3. Note which device identifier (`/dev/sdX`) corresponds to each drive. The 1TB Backup Plus and 640GB Momentus can be distinguished by size in the `lsblk` output.

### 4b — Format Both Drives

**Confirm the correct device identifiers with Joseph before running mkfs on either drive — formatting the wrong drive is destructive and irreversible.**

Format the Seagate Backup Plus 1TB:
```bash
sudo mkfs.ext4 /dev/sdX1   # replace sdX1 with Backup Plus device partition
```

Format the Seagate Momentus 640GB:
```bash
sudo mkfs.ext4 /dev/sdY1   # replace sdY1 with Momentus device partition
```

### 4c — Get UUIDs

```bash
sudo blkid /dev/sdX1   # Backup Plus 1TB
sudo blkid /dev/sdY1   # Momentus 640GB
```

Record both UUIDs.

### 4d — Create Mount Points

```bash
sudo mkdir -p /mnt/photo-library
sudo mkdir -p /mnt/photo-library-backup
```

### 4e — Add to /etc/fstab

Add both entries using UUIDs (not device names):
```
UUID=<backup-plus-uuid>  /mnt/photo-library         ext4  defaults,nofail  0  2
UUID=<momentus-uuid>     /mnt/photo-library-backup   ext4  defaults,nofail  0  2
```

### 4f — Mount and Verify

```bash
sudo mount -a
df -h /mnt/photo-library
df -h /mnt/photo-library-backup
```

### 4g — Set Ownership

```bash
sudo chown -R $USER:$USER /mnt/photo-library
sudo chown -R $USER:$USER /mnt/photo-library-backup
```

**Report back:** Confirm both mount points are active and `nofail` is set for each.

---

## Step 5 — Install Docker and Docker Compose

1. Install Docker via the official Docker apt repository (not the Ubuntu default repository, which lags behind):
   ```bash
   sudo apt install -y ca-certificates curl
   sudo install -m 0755 -d /etc/apt/keyrings
   sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
   sudo chmod a+r /etc/apt/keyrings/docker.asc
   echo \
     "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
     $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
     sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
   sudo apt update
   sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
   ```
2. Add the current user to the `docker` group (avoids needing `sudo` for every docker command):
   ```bash
   sudo usermod -aG docker $USER
   ```
   Log out and back in (or `newgrp docker`) for this to take effect.
3. Pin DNS in the Docker daemon config — **required per the existing JCTsh lesson learned (documented in `CLAUDE.md`)** to prevent stale DHCP-assigned DNS from breaking container connectivity:
   ```bash
   sudo tee /etc/docker/daemon.json > /dev/null <<'EOF'
   {
     "dns": ["8.8.8.8", "8.8.4.4"]
   }
   EOF
   sudo systemctl restart docker
   ```
4. Verify installation:
   ```bash
   docker --version
   docker compose version
   docker run hello-world
   ```

---

## Step 6 — Install Immich

1. Create the Immich project directory:
   ```bash
   mkdir -p ~/immich-app
   cd ~/immich-app
   ```
2. Download the official Immich `docker-compose.yml` and `.env` example — **use the current official install method documented at immich.app/docs at the time of this build.** Immich releases frequently and file contents change; do not rely on a cached or remembered version.
   ```bash
   curl -o docker-compose.yml https://github.com/immich-app/immich/releases/latest/download/docker-compose.yml
   curl -o .env https://github.com/immich-app/immich/releases/latest/download/example.env
   ```
3. Edit `.env`:
   - Set `UPLOAD_LOCATION=/mnt/photo-library`
   - Set `DB_DATA_LOCATION` to a path on the internal SSD (default Docker-managed volume location is acceptable — do not redirect this to either USB HDD)
   - Set `TZ=America/Phoenix`
   - Set a strong `DB_PASSWORD` (generate randomly, do not commit to repo)
4. Start Immich:
   ```bash
   docker compose up -d
   ```
5. Verify all containers are running:
   ```bash
   docker compose ps
   ```
6. Access the web UI at `http://photo-server.local:2283` (or the reserved IP) and complete the initial admin account setup.

**Report back:** Confirm Immich web UI is reachable and the admin account is created.

---

## Step 7 — Create User Accounts

1. In the Immich web UI (as admin), create Robin's account:
   - Email and password per Joseph's instruction (collect securely, do not store in repo)
   - Standard user role (not admin)
2. Confirm both accounts can log in independently

---

## Step 8 — Enable ML Features

1. In Immich admin settings, confirm the following are enabled (they are typically on by default in current Immich releases, but verify):
   - Smart Search (CLIP)
   - Facial Recognition
   - Duplicate Detection
2. ML processing runs on CPU (Ryzen PRO 6650H) — no GPU/ROCm configuration needed for initial build
3. Note: ML model download on first run can take time and bandwidth — this is expected, not an error

---

## Step 9 — Set Up Backup (rsync cron job)

Set up a weekly rsync job to back up the Immich photo library from the Seagate Backup Plus 1TB to the Seagate Momentus 640GB:

1. Create a backup script:
   ```bash
   sudo tee /usr/local/bin/photo-library-backup.sh > /dev/null <<'EOF'
   #!/bin/bash
   rsync -av --delete /mnt/photo-library/ /mnt/photo-library-backup/
   EOF
   sudo chmod +x /usr/local/bin/photo-library-backup.sh
   ```
2. Add a weekly cron job (runs Sunday at 2:00 AM):
   ```bash
   (crontab -l 2>/dev/null; echo "0 2 * * 0 /usr/local/bin/photo-library-backup.sh >> /var/log/photo-library-backup.log 2>&1") | crontab -
   ```
3. Run the script once manually to verify it works:
   ```bash
   /usr/local/bin/photo-library-backup.sh
   ```
4. Confirm files appear at `/mnt/photo-library-backup/`

**Capacity monitoring:** The Momentus 640GB backup drive is smaller than the 1TB primary. Flag to Joseph when `/mnt/photo-library` approaches 550GB — at that point the backup drive needs to be replaced with one of the spare 1TB drives (Seagate Expansion or WD 750GB is not large enough — use the Seagate Backup Plus spare or pursue the NVMe expansion).

---

## Step 10 — Install Immich Android App (Both Phones)

This step is performed by Joseph and Robin directly on their phones, not by Claude Code. Document the configuration values needed:

| Field | Value |
|---|---|
| Server URL (home WiFi) | `http://photo-server.local:2283` or `http://<reserved IP>:2283` |
| Server URL (remote, future) | Not configured in this phase |
| Sync trigger | Home WiFi only — confirm this setting in the app, not background cellular sync |

**Report back:** Note in the build log once Joseph confirms both phones are syncing successfully.

---

## Step 11 — Photo Migration Preparation

This step involves manual actions by Joseph (Google Takeout export, quality pass) before Claude Code resumes with the import.

1. Joseph exports Google Takeout for both accounts (Google Photos only, ZIP format, max chunk size) and transfers the ZIP files to the M8 via SCP or a shared folder
2. Joseph performs the manual quality pass — moving low-quality candidates (blurry, accidental, duplicate, screenshot) into an `_archive` subfolder within the extracted Takeout structure, per the quality pass method documented in `photo-server-phase2-planning.md`

**Claude Code does not perform the quality review** — this requires human judgment about photo content and is explicitly a manual step. Wait for Joseph's confirmation that the quality pass is complete before proceeding to Step 12.

---

## Step 12 — Install immich-go and Run Migration

1. Download immich-go (current release at build time):
   ```bash
   cd ~
   curl -L -o immich-go.tar.gz https://github.com/simulot/immich-go/releases/latest/download/immich-go_Linux_x86_64.tar.gz
   tar -xzf immich-go.tar.gz
   sudo mv immich-go /usr/local/bin/
   ```
2. Generate an Immich API key for Joseph's account (Immich web UI → Account Settings → API Keys)
3. Run the import for Joseph's Takeout export:
   ```bash
   immich-go upload from-google-photos \
     --server=http://localhost:2283 \
     --api-key=<joseph-api-key> \
     /path/to/joseph-takeout-extracted
   ```
4. Generate a separate Immich API key for Robin's account and repeat for her Takeout export:
   ```bash
   immich-go upload from-google-photos \
     --server=http://localhost:2283 \
     --api-key=<robin-api-key> \
     /path/to/robin-takeout-extracted
   ```
5. Monitor import progress — this will take a significant amount of time for ~75,000 photos. Let it run to completion; do not interrupt.
6. After import, verify in the Immich web UI:
   - Photo counts roughly match expected totals (allowing for the quality pass exclusions)
   - Spot-check dates and locations on a sample of photos
   - Check album structure for major albums

**Report back:** Provide final photo/video counts per account and flag any import errors immich-go reported.

---

## Step 13 — Name Recognized Faces — N/A (decided 2026-07-09)

**Not tracked as a discrete step.** Joseph decided to name faces "catch as catch can" — ad hoc, over time, whenever he or Robin happen to be in the Immich UI — rather than as a formal one-time task to complete and check off. ML processing (`faceDetection`/`facialRecognition`) is fully complete (CARD-037) and the clusters are ready whenever naming happens; there is no pending blocker and no further action item here.

---

## Step 14 — Set Up Deletion Logging — Moved to `photo-tv-display` (decided 2026-07-09)

Joseph determined this step belongs with the `photo-tv-display` build, not `photo-server` — consistent with the original note below that the actual delete trigger lives there. Tracking moves to that component's own Claude Code Instructions document when that build starts; no action taken here.

Original content, retained for reference when that build begins:
1. Local log file: `/mnt/photo-library/deletion-log.csv` with header `timestamp,filename,date_taken,album_folder,immich_asset_id,deleted_by`
2. A new, separate Google Sheet (not the existing JCTsh environmental data sheet) for the deletion log review interface — Joseph provides the Sheet ID when that build starts
3. Apps Script `doPost` handler for the new sheet, following the JCTsh pattern in `JCTsh-Build-Standards.md` §5.5 — deployed separately from the existing JCTsh Apps Script
4. The `photo-tv-display` Node.js server calls this endpoint when deletions occur; this step only sets up the receiving side (local file + Sheet + Apps Script)

---

## Step 15 — Install Node.js (Preparation for photo-tv-display)

`photo-tv-display` runs on this same machine. Install Node.js now so it's ready when that component's build begins:

1. Install Node.js LTS via NodeSource (current LTS at build time):
   ```bash
   curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
   sudo apt install -y nodejs
   ```
2. Verify:
   ```bash
   node --version
   npm --version
   ```

No further `photo-tv-display` setup happens in this build — that is a separate Claude Code Instructions document.

---

## Step 16 — Documentation

Per `JCTsh-Build-Standards.md` §7, create the following in `components/photo-server/`:

| Document | Contents |
|---|---|
| `README.md` | What `photo-server` does, service URLs, account info (no passwords), dependencies |
| `docker-compose.yml` | Copy of the authoritative compose file actually used (with secrets/passwords redacted or templated) |
| `.env.example` | Template `.env` with placeholder values — never commit the real `.env` |
| `setup.md` | This build's actual steps as executed — capture any deviations from this instruction set |
| `migration.md` | Actual migration steps performed, including final photo counts and any errors encountered |
| `network.md` | Final IP, hostname, MAC, Tailscale IP — cross-reference with `jctsh-network.md` |
| `operations.md` | How to check Immich is running, restart it, update it, check disk space on both USB HDDs, verify backup cron job is running |
| `deletion-log-setup.md` | Apps Script source, Sheet ID (not the script's deployed URL/key — store that as a credential), local log file location |
| `backup.md` | rsync backup script location, cron schedule, how to verify backup, capacity monitoring note for Momentus 640GB drive (flag at 550GB) |

Add `.env`, any API keys, and the Apps Script deployment URL/key to the gitignored credentials file per existing JCTsh convention — do not commit secrets.

---

## Step 17 — Update Repo-Wide Files

1. Add `photo-server` to the Components table in root `README.md`:
   ```
   | [photo-server](components/photo-server/) | Self-hosted Immich photo/video library on dedicated mini PC | Production |
   ```
2. Confirm `jctsh-network.md` has been updated (Steps 2 and 3)
3. Add an entry to `jctsh-parts-inventory.md` inventory update log noting the hardware deployed:
   ```
   | <date> | photo-server | GMKtec M8 mini PC deployed (Immich server); Seagate Backup Plus 1TB USB HDD deployed (primary photo library); Seagate Momentus 640GB in Insignia enclosure deployed (local backup) |
   ```
   Also note spares not deployed:
   ```
   | <date> | photo-server | Spares on hand: Seagate Expansion 1TB (P/N 9SF2A4-500), WD 750GB (P/N WD7500H1U-00) |
   ```

---

## Step 18 — Harvest Step (Per Build Standards)

Per `JCTsh-Build-Standards.md`, propose any new patterns discovered during this build back to `JCTsh-Build-Standards.md`. Likely candidates based on this component's novelty relative to existing JCTsh components:

- A new section for non-ESP32 / Docker-based component standards (this is the first component of this type)
- Documentation of the DNS-pinning Docker daemon pattern as a now-twice-applied standard (originally HA, now also Immich)
- UUID-based USB HDD mount with `nofail` as a standard pattern for any future components with attached storage
- rsync cron backup pattern for local USB HDD backup
- Bus-powered USB HDD preference for compact installations (no external power supply)

Present these as proposed additions for Joseph's review — do not edit `JCTsh-Build-Standards.md` directly without confirmation, since it is a monorepo-wide standards file affecting all components.

---

## Known Risks and Things to Watch For

- **Formatting the wrong drive in Step 4** — verify device identifiers carefully and confirm with Joseph before running `mkfs` on either drive
- **Momentus 640GB backup capacity** — smaller than the 1TB primary; monitor and flag when `/mnt/photo-library` approaches 550GB; replacement spare is the Seagate Expansion 1TB (note: it requires external power, unlike the currently deployed bus-powered drives)
- **ML processing time** — facial recognition and smart search indexing for 75K photos will take hours; this is normal, not a hang
- **immich-go version drift** — the exact command syntax may change between releases; consult `immich-go --help` if the documented command fails
- **Immich `docker-compose.yml` drift** — the official file changes between releases; if the downloaded file differs significantly from what's described in Phase 2 planning, follow the current official documentation over this instruction set's specifics, and note the discrepancy in `setup.md`
- **DNS pinning is required, not optional** — skipping Step 5.3 risks a repeat of the June 2026 HA outage pattern if the container is recreated later with a stale DNS baked in
- **Seagate Backup Plus was formatted for Mac (HFS+)** — reformatting to ext4 in Step 4b is required and expected; no data loss concern since the drive is empty
