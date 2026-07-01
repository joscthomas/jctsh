# photo-server — Phase 2 Planning Document
**Author:** Joseph C Thomas (JCT)
**Purpose:** Phase 2 hardware selection, architecture, and build preparation for the JCTsh self-hosted photo library server component.
**Version:** 1.0
**Version description:** Initial release — Phase 2 complete.
**Project:** JCTsh Photo Platform
**Status:** Phase 2 Complete — Ready for Phase 3
**Related files:** `photo-server-phase1-planning.md`, `photo-tv-display-phase1-planning.md`, `jctsh-network.md`, `README.md`

---

## Hardware

### Mini PC — Already Purchased and On Hand

**GMKtec NucBox M8**
- Purchased: confirmed on hand
- CPU: AMD Ryzen 5 PRO 6650H (6C/12T, up to 4.5GHz, Zen 3+, 6nm)
- RAM: 16GB LPDDR5 6400MHz (soldered, non-upgradable)
- Internal SSD: 512GB PCIe 4.0 NVMe (pre-installed)
- Second M.2 slot: empty, PCIe 4.0 NVMe only (SATA not supported) — future expansion option
- GPU: AMD Radeon 660M (integrated, RDNA 2)
- Networking: Dual 2.5GbE LAN + WiFi 6E
- Cooling: Dual-fan active with copper heat pipes
- OS pre-installed: Windows 11 Pro (capture license key before wiping — see Pre-Build Actions)

### USB Spinning HDD — On Hand

Dedicated USB spinning hard drive for Immich photo/video library.
- **Capacity: to confirm** (estimated 500GB or 1TB — check when home)
- Currently empty; dedicated entirely to Immich
- 500GB is workable for the current ~300GB library; 1TB is strongly preferred for growth headroom

### Future Storage Expansion Option (Not Required for Initial Build)

A second M.2 2280 NVMe SSD can be added to the empty internal slot at any time:
- Form factor: M.2 2280 (22mm × 80mm)
- Interface: PCIe NVMe only — SATA is not supported in this slot
- Recommended capacity: 1TB or 2TB (~$60–100, reputable brands: Samsung 970/980, WD Black SN850, Crucial P3/P5, SK Hynix)
- When added: active Immich photo library migrates from USB HDD to internal NVMe; USB HDD becomes local backup/overflow
- Migration path: file copy to new mount point + Docker Compose volume path update; no Immich reinstallation
- Heatsink: a low-profile M.2 stick-on heatsink ($5–10) is recommended due to sustained write load during initial migration
- Installation: remove four bottom screws, seat the drive, replace cover

### Network Connection

Wired ethernet (2.5GbE) is required — WiFi is not acceptable for a machine running sustained photo migration and always-on Immich serving.

The TP-Link AXE5400 router has 4 gigabit LAN ports. The Raspberry Pi and SmartThings hub are moved to the existing 10/100 switch (both are low-bandwidth devices — the Pi's ethernet is 100Mbps anyway, so the 10/100 switch is no limitation). This frees a gigabit LAN port on the router for the M8 direct connection — no new switch required.

**Final wired ethernet layout:**
| Device | Connection |
|---|---|
| GMKtec M8 (photo-server) | Direct to router gigabit LAN port |
| Raspberry Pi 3B+ | 10/100 switch → router |
| SmartThings Hub | 10/100 switch → router |

### Parts Inventory

No on-hand parts from `jctsh-parts-inventory.md` apply to this component. `photo-server` is a mini PC / Docker / Ubuntu build with no ESP32, perfboard, or sensor involvement.

---

## Pre-Build Actions

These steps must be completed before installing Ubuntu.

### 1. Capture Windows 11 Pro License Key

Run the following in PowerShell on the M8 while Windows is still installed:

```powershell
(Get-WmiObject -query 'select * from SoftwareLicensingService').OA3xOriginalProductKey
```

Save the output to a password manager or secure offline location.

**If the command returns nothing or a generic key:** The license is an OEM digital license tied to the UEFI chip. It will reactivate automatically if Windows is ever reinstalled on this hardware. Note that a valid OEM license exists and the hardware is the activation proof. Either way, document the outcome before proceeding.

### 2. Confirm USB HDD Capacity

Check the USB HDD capacity before beginning. Either 500GB or 1TB works; 1TB is strongly preferred. If 500GB is the only available drive, proceed — the current library (~300GB) fits with modest headroom.

---

## Operating System

**Ubuntu Server LTS** — replaces Windows 11 Pro.

- Use the current LTS release at build time (verify at ubuntu.com/download/server)
- Server edition (no desktop GUI) — all administration via SSH and browser-based UIs
- Timezone: `America/Phoenix` (MST, UTC-7, no DST) — consistent with the rest of JCTsh infrastructure
- Hostname: `photo-server`

**Installation media:** Create a bootable USB drive on the Windows machine using Balena Etcher or Rufus before wiping Windows.

---

## Network Configuration

### Wired Ethernet

The M8 connects via wired ethernet to the home router (or switch if needed). WiFi is available as a fallback only.

### IP and Hostname

| Field | Value |
|---|---|
| Hostname | `photo-server` |
| mDNS | `photo-server.local` |
| IP assignment | Dynamic on first boot; reserve in router DHCP after confirming assignment |
| MAC address | Record from router DHCP table after first boot |

After reserving the IP, record the entry in `jctsh-network.md`:

```
| photo-server | [assigned IP] | photo-server.local | [MAC] | Immich photo server + photo-tv-display Node.js server |
```

### Tailscale

Install Tailscale on the M8 and enroll it in the existing JCTsh Tailscale account. This provides secure remote admin access (SSH, Immich web UI) from anywhere without port forwarding.

Add the Tailscale IP to `jctsh-network.md` after enrollment.

### WiFi — Not Used for Production

The M8's WiFi 6E radio is available but not used for JCTsh service traffic. Wired ethernet is the production interface. WiFi may be used during initial Ubuntu setup before ethernet is configured, if needed.

**Note:** JCTsh devices use JCTnet1 (2.4GHz). The M8's WiFi 6E radio supports 2.4GHz, 5GHz, and 6GHz — connect to JCTnet1 if WiFi is needed during setup.

---

## Software Stack

| Layer | Technology | Notes |
|---|---|---|
| OS | Ubuntu Server LTS | Current LTS at build time |
| Container runtime | Docker + Docker Compose | Install via official Docker apt repository |
| Photo platform | Immich | Current stable release at build time; installed via official Docker Compose method |
| Migration tool | immich-go CLI | Current stable release at build time |
| Photo source for migration | Google Takeout export | Downloaded on Windows machine, transferred to photo-server |
| Mobile sync | Immich Android app | Joseph: Pixel 10 Pro XL; Robin: Pixel 7 |
| Remote access | Tailscale | Enrolled in existing JCTsh Tailscale account |
| TV app server | Node.js | Installed on same machine; serves `photo-tv-display` web app and handles Immich API calls |

### Immich Installation Method

Use the official Immich Docker Compose installation — do not use third-party installers or package managers. The official method is documented at immich.app/docs and is the only supported path. Verify the current recommended `docker-compose.yml` and `.env` at build time — Immich releases frequently and the compose file changes.

### DNS Configuration

Pin DNS to `8.8.8.8` / `8.8.4.4` in the Docker daemon configuration — consistent with the existing JCTsh Pi pattern (documented in `CLAUDE.md`) that prevents stale DHCP-assigned DNS servers from breaking container connectivity.

Add to `/etc/docker/daemon.json`:
```json
{
  "dns": ["8.8.8.8", "8.8.4.4"]
}
```

---

## Storage Architecture

### Mount Points

| Mount point | Device | Contents |
|---|---|---|
| `/` (root filesystem) | Internal 512GB NVMe SSD | Ubuntu OS, Docker engine, Immich database, Immich ML models, Docker volumes |
| `/mnt/photo-library` | USB spinning HDD | Immich photo and video library (uploaded files) |

### USB HDD Mount

The USB HDD is mounted at `/mnt/photo-library` via `/etc/fstab` using the device UUID (not device name — device names like `/dev/sdb` can change between reboots; UUID is stable).

Mount options: `defaults,nofail` — `nofail` ensures the system boots normally even if the USB HDD is disconnected.

### Docker Compose Volume Mapping

The Immich `UPLOAD_LOCATION` environment variable in the Immich `.env` file is set to `/mnt/photo-library`. This directs all uploaded and migrated photo files to the USB HDD while Immich's database and ML model cache remain in Docker-managed volumes on the internal SSD.

### Future NVMe Expansion Migration Path

When a second internal NVMe SSD is added:
1. Mount new NVMe at `/mnt/photo-library-new`
2. Stop Immich: `docker compose down`
3. Copy library: `rsync -av /mnt/photo-library/ /mnt/photo-library-new/`
4. Verify copy integrity
5. Update `/etc/fstab` to mount new NVMe at `/mnt/photo-library`
6. Unmount and update mount: `sudo umount /mnt/photo-library && sudo mount -a`
7. Start Immich: `docker compose up -d`
8. USB HDD repurposed as backup/overflow

No changes to Docker Compose or Immich configuration are required — the mount point path stays the same.

---

## Immich Configuration

### Users

Two Immich accounts are created during setup:

| Account | Role |
|---|---|
| Joseph (admin) | Admin account — manages server, users, and shared library |
| Robin | Standard user — full photo access, shared library participant |

The admin account also functions as Joseph's photo account — no separate admin-only account is needed.

### Shared Library

Both Joseph's and Robin's uploaded photos are visible in a shared library. Ownership is tracked at the account level and available as metadata. The `photo-tv-display` Node.js server queries both accounts and presents photos in an integrated pool.

### ML Features

Enable all Immich ML features:
- **Smart Search (CLIP):** semantic image search — "hiking", "sunset", "birthday"
- **Facial Recognition:** automatic face detection and grouping; users name faces once
- **Duplicate Detection:** flags likely duplicates for review

ML processing runs on the M8's Ryzen PRO 6650H CPU. GPU acceleration (AMD Radeon 660M via ROCm) is not required for initial build — CPU inference is adequate and simpler to configure.

### Memory / "On This Day"

Immich's built-in memory feature generates "On this day" collections automatically. Enable in Immich settings.

---

## Photo Migration

### Source

Google Takeout export of both Joseph's and Robin's Google Photos libraries.

**Export steps (per account):**
1. Go to takeout.google.com
2. Deselect all, then select Google Photos only
3. Export format: ZIP, maximum file size (50GB chunks if library exceeds single file)
4. Download all ZIP files to Windows machine
5. Transfer to `photo-server` via local network (SCP or shared folder)

### Migration Tool

**immich-go CLI** — purpose-built for Google Takeout imports. Handles:
- Reconciliation of Google's JSON sidecar files (dates, GPS metadata) with photo files
- Album reconstruction from Takeout album folders
- Duplicate detection during import
- Progress reporting and resumable imports

Download current release from github.com/simulot/immich-go at build time.

### Migration Sequence

1. Complete Ubuntu and Immich installation and verify Immich is running
2. Complete quality pass on Takeout export before importing (see Quality Pass below)
3. Import Joseph's Takeout export into Joseph's Immich account via immich-go
4. Import Robin's Takeout export into Robin's Immich account via immich-go
5. Verify photo counts, dates, and album structure in Immich web UI
6. Enable facial recognition and allow ML processing to complete (may take several hours for 75K photos)
7. Name detected faces in Immich

### Quality Pass (Pre-Import)

Before running immich-go, review the Takeout export for low-quality content:

**Archive candidates (set aside, do not delete):**
- Blurry or out-of-focus photos
- Accidental photos (pocket shots, black frames)
- Duplicate shots (near-identical burst photos — keep the best one)
- Screenshots
- Very low-resolution images not worth displaying on TV

**Method:** Create an `_archive` subfolder in the Takeout export. Move low-quality files there before import. immich-go imports the remaining files. The archived files are retained as a local backup outside Immich.

**Goal:** Slideshow pool contains only photos worth displaying. Archiving is reversible — files in `_archive` can be imported later if needed.

### What Transfers from Google Photos

| Data | Transfers? | Notes |
|---|---|---|
| Original photo files | ✅ Yes | Full resolution originals |
| EXIF data (camera, aperture, ISO, etc.) | ✅ Yes | Embedded in photo files |
| GPS coordinates | ✅ Yes | Embedded in EXIF for most Pixel photos |
| Date taken | ✅ Yes (via immich-go) | Reconciled from JSON sidecar by immich-go |
| Album structure | ✅ Partial | Reconstructed by immich-go; complex hierarchies may need manual cleanup |
| Descriptions / notes | ⚠️ Inconsistent | May appear in JSON sidecar; not reliably transferred — manual re-entry required for critical notes |
| Face tags (Google's) | ❌ No | Immich re-detects faces from scratch using its own ML |
| Google Photos edits/filters | ❌ No | Export is the original unedited file |

---

## Photo Quality Strategy

### Initial Quality Pass
Performed on Takeout export before import (see Migration section above).

### Ongoing Quality Proxy
Photos marked as **favorites** in Immich (via `photo-tv-display` phone controller or Immich app) accumulate into a curated high-quality pool over time. `photo-tv-display` can filter to favorites-only slideshow mode.

### Future Enhancement Hook — Automatic Quality Scoring
Third-party ML aesthetic scorer (e.g., CLIP-based aesthetic predictor) running on M8 hardware. Scores photos on import, writes results back as Immich tags. `photo-tv-display` filters by quality threshold. Architecture supports this addition without structural change to `photo-server`. Deferred to future build.

---

## Deletion Logging

When `photo-tv-display` deletes a photo from Immich, the Node.js server writes a deletion log entry simultaneously to two destinations:

| Destination | Path / Location | Purpose |
|---|---|---|
| Local log file | `/mnt/photo-library/deletion-log.csv` | Primary record; on USB HDD alongside the library |
| Google Sheets | Shared JCTsh Google Sheet (tab: `Photo Deletions`) | Review and manual Google Photos cleanup interface |

**Log fields:** `timestamp`, `filename`, `date_taken`, `album_folder`, `immich_asset_id`, `deleted_by` (Joseph or Robin)

**Google Sheets integration:** Append-only via Google Apps Script `doPost` endpoint or Google Sheets API from the Node.js server. Consistent with existing JCTsh pattern of using Sheets for data archiving.

**Google Photos deletion:** No API path exists (Google locked down the Photos Library API, April 2025). Manual deletion from Google Photos app using the log as a reference.

---

## Mobile Sync

### Immich Android App

Install on both phones:
- Joseph: Pixel 10 Pro XL
- Robin: Pixel 7

**Configuration per phone:**
- Server URL: `http://photo-server.local:2283` (on home WiFi) or Tailscale IP for remote setup
- Sync trigger: home WiFi only (initial build)
- Auto-backup: enabled for Camera Roll

### Dual Backup

Google Photos continues syncing independently on both phones. Immich and Google Photos are entirely independent — no programmatic link between them.

### Remote Sync (Future Enhancement)

Expose Immich via DuckDNS (already in use for JCTsh at `jctsh.duckdns.org`). A separate subdomain or path routes to Immich on the M8. Immich Android app connects remotely. Photos arrive in Immich in near real-time rather than waiting for home WiFi. Deferred — architecture supports it without structural change.

---

## Port Assignments

| Service | Port | Notes |
|---|---|---|
| Immich web UI | 2283 | Immich default; access via `http://photo-server.local:2283` |
| `photo-tv-display` Node.js server | 3000 | Confirmed in Phase 2 of `photo-tv-display` component |
| SSH | 22 | Standard; key-based auth only |

No ports are forwarded to the internet for the initial build.

---

## Integration with Existing JCTsh Infrastructure

`photo-server` is a standalone service on the home LAN. It has no MQTT, Node-RED, ESPHome, or Home Assistant involvement in the initial build.

### Touchpoints with Existing JCTsh

| Integration | Action required |
|---|---|
| `jctsh-network.md` | Add `photo-server` entry (IP, hostname, MAC, Tailscale IP) after first boot |
| `README.md` | Add `photo-server` to the Components table |
| Tailscale | Enroll M8 in existing JCTsh Tailscale account |
| Google Sheets | Add `Photo Deletions` tab to existing JCTsh Google Sheet (or create new sheet) |
| DuckDNS | Future: add Immich routing for remote mobile sync |

### What Is Not Involved

- Mosquitto MQTT broker — not used
- Node-RED — not used (Node.js on M8 handles all `photo-tv-display` logic)
- Home Assistant — not used in initial build (future: Google Home voice trigger via HA)
- SmartThings — not used
- Raspberry Pi 3B+ — not involved; `photo-server` runs entirely on the M8

---

## Documentation Required (Phase 3 / Build)

Following JCTsh Build Standards §7, the completed component requires:

| Document | Purpose |
|---|---|
| `README.md` | What `photo-server` does, how to access it, service URLs, user accounts |
| `docker-compose.yml` | Immich Docker Compose configuration (authoritative copy in repo) |
| `.env` | Immich environment variables template (secrets gitignored; template committed) |
| `setup.md` | Ubuntu installation, Docker setup, USB HDD mount, Immich installation procedure |
| `migration.md` | Google Takeout export, quality pass, immich-go import procedure |
| `network.md` | IP reservation, mDNS hostname, Tailscale enrollment |
| `operations.md` | Day-to-day administration, backup, Immich update procedure |
| `deletion-log-setup.md` | Local log file setup and Google Sheets integration for deletion logging |

---

## Open Items Before Phase 3

- [ ] Confirm USB HDD capacity (500GB or 1TB)
- [ ] Capture Windows 11 Pro license key via PowerShell before wiping
- [ ] Create Ubuntu bootable USB on Windows machine before wiping
- [ ] Confirm ethernet port availability at router (or procure unmanaged switch if needed)
- [ ] Download Balena Etcher or Rufus on Windows machine for USB boot drive creation
- [ ] Determine Google Sheets destination for deletion log (existing JCTsh sheet new tab, or new sheet)

---

## Future Enhancements

| Enhancement | Notes |
|---|---|
| Second internal NVMe SSD | PCIe M.2 2280, 1–2TB; migration path defined above; heatsink recommended |
| Remote mobile sync | DuckDNS path already exists; Immich Android app remote config; deferred |
| Automatic quality scoring | ML aesthetic scorer on M8 CPU; scores written as Immich tags; hook preserved |
| Google Home voice trigger | Implemented in `photo-tv-display`, not `photo-server`; noted for cross-reference |
| HA integration | Future: Immich as HA media source; Google Home voice control via HA |
| TLS for Immich | HTTPS via reverse proxy (Caddy or nginx) + Let's Encrypt; required before any internet exposure |
