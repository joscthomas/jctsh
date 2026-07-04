# photo-server — Phase 1 Planning Document
**Author:** Joseph C Thomas (JCT)
**Purpose:** Phase 1 Discovery summary and feasibility findings for the JCTsh self-hosted photo library server component.
**Version:** 1.0
**Version description:** Initial release — Phase 1 Discovery complete.
**Project:** JCTsh Photo Platform
**Status:** Phase 1 Complete — Ready for Phase 2
**Related files:** `photo-tv-display-phase1-planning.md`

---

## Component Overview

`photo-server` is a self-hosted photo and video library running **Immich** on a dedicated mini PC. It replaces Google Photos as the primary browsing and curation platform while Google Photos continues as an independent backup. Both Joseph and Robin have separate Immich accounts feeding a shared library. The server also acts as the backend for the `photo-tv-display` component.

---

## Hardware

### Mini PC
**GMKtec NucBox M8**
- CPU: AMD Ryzen 5 PRO 6650H (6 cores / 12 threads, up to 4.5 GHz, Zen 3+, 6nm)
- RAM: 16GB LPDDR5 6400MHz (soldered, non-upgradable)
- Internal SSD: 512GB PCIe NVMe (pre-installed)
- Storage slots: Dual M.2 2280 PCIe 4.0 NVMe (second slot empty — expansion option, see below)
- GPU: AMD Radeon 660M (integrated, RDNA 2) — adequate for Immich ML workloads
- Networking: Dual 2.5GbE LAN + WiFi 6E
- OS: Windows 11 Pro pre-installed (Ubuntu will be installed for JCTsh use)
- Cooling: Dual-fan active cooling with copper heat pipes

This hardware is confirmed — **already purchased and on hand.**

**Purchased:** GMKtec Mini PC M8 Desktop Computer AMD Ryzen PRO 6650H (6C/12T 4.50Ghz) Dual NIC LAN 2.5GbE, 16GB LPDDR5 RAM + 512GB Hard Drive PCle SSD, Oculink, USB4, HDMI, USB-C

**Pre-build required action — capture Windows license before wiping:**
Before installing Ubuntu, capture the Windows 11 Pro product key. Run the following in PowerShell:
```powershell
(Get-WmiObject -query 'select * from SoftwareLicensingService').OA3xOriginalProductKey
```
Save the output to a password manager or secure location. If the command returns nothing or a generic key, the license is an OEM digital license tied to the UEFI chip — it will reactivate automatically if Windows is ever reinstalled on this hardware. In that case, note that a valid OEM license exists and the hardware is the activation proof. Either way, document the outcome before proceeding with Ubuntu installation.

### Storage Architecture
Storage is split between the internal SSD and two bus-powered USB spinning HDDs — no external power supplies required:

| Role | Device | Rationale |
|---|---|---|
| OS, Docker, Immich database, ML models | Internal 512GB NVMe SSD | Fast random I/O required for database and ML |
| Immich photo/video library (primary) | Seagate Backup Plus 1TB USB HDD | Bus-powered, compact 2.5" form factor, newer drive |
| Local backup of photo library | Seagate Momentus 640GB in Insignia enclosure | Bus-powered, compact 2.5" form factor |

**Primary USB HDD — confirmed on hand:**
- **Seagate Backup Plus Portable Drive, 1TB spinning HDD**
- P/N: 1KAAP1-501, S/N: NA7R2L3V
- Model: SRD00F1
- Bus-powered via USB — no external power supply required
- 2.5" compact form factor
- Currently empty; dedicated entirely to Immich photo/video library

**Backup USB HDD — confirmed on hand:**
- **Seagate Momentus 640GB spinning HDD in Insignia NS-PCHD235 2.5" USB 3.0 enclosure**
- Drive S/N: 5WX1MLNF, P/N: 9RN134-030, WWN: 5000C5002EA01011, 5400 RPM
- Bus-powered via USB — no external power supply required
- 2.5" compact form factor
- Repurposed as local backup of the Immich photo library

**Spare drives (not deployed):**
- Seagate Expansion 1TB (P/N: 9SF2A4-500, S/N: 2GHK8E60) — requires external power; spare
- Western Digital 750GB (P/N: WD7500H1U-00, S/N: WCAU41533297) — spare

**Backup capacity note:** The Momentus backup drive (640GB) is smaller than the primary (1TB). The current library (~300GB) fits comfortably. Monitor disk usage — flag when `/mnt/photo-library` approaches 550GB as the backup drive capacity limit is approaching.

**Future storage expansion option:** The empty second M.2 2280 slot supports an additional NVMe SSD (PCIe only — SATA not supported). A 1TB or 2TB NVMe (~$60–100, reputable brands: Samsung, WD Black, Crucial, SK Hynix) can be added at any time by removing the four bottom screws and seating the drive. When added:
- The active Immich photo library migrates from Seagate Backup Plus to the internal NVMe
- USB HDDs become backup/overflow drives
- Migration requires only a file copy and Docker Compose volume path update — no Immich reinstallation
- A low-profile M.2 heatsink ($5–10) is recommended when adding the SSD due to sustained write loads during migration

---

## Software Stack

| Layer | Technology |
|---|---|
| OS | Ubuntu Server LTS (replaces Windows 11 for JCTsh use) |
| Container runtime | Docker + Docker Compose |
| Photo platform | Immich (self-hosted) |
| Migration tool | immich-go CLI |
| Photo source | Google Takeout export |
| Mobile sync | Immich Android app (Joseph — Pixel 10 Pro XL; Robin — Pixel 7) |

### Why Immich
- Full-featured REST API enabling the `photo-tv-display` custom app
- Active development and strong community support
- Built-in ML features (facial recognition, semantic search) that run locally
- Native multi-user support with shared library capability
- immich-go CLI handles Google Takeout import quirks (sidecar JSON reconciliation, album reconstruction)

---

## Library

- **Source:** Google Photos (Joseph and Robin combined)
- **Size:** ~75,000 photos + modest video collection, approximately 300GB total
- **Migration method:** Google Takeout export → immich-go CLI import
- **EXIF data:** Original EXIF transfers with photo files; dates and location metadata reconciled from Google's JSON sidecar files by immich-go; Google Photos face tags do not transfer (Immich re-detects faces from scratch)
- **Notes/descriptions:** Google Photos comments transfer inconsistently via Takeout; any critical notes require manual re-entry in Immich. Photo description is included as a display field in `photo-tv-display` going forward.
- **Album structure:** Partially reconstructed by immich-go; complex hierarchies may require manual cleanup post-import

---

## Users and Accounts

Both Joseph and Robin have separate Immich accounts. Photos sync from each phone under the respective owner's account and appear in a shared library visible to both.

| User | Device | Immich account |
|---|---|---|
| Joseph | Pixel 10 Pro XL | Separate Immich account |
| Robin | Pixel 7 | Separate Immich account |

Ownership is tracked at the Immich account level and is available as metadata for display in `photo-tv-display`.

---

## Photo Sync

**Method:** Immich Android app on both Pixel phones, syncing to `photo-server` on home WiFi connection.

**Sync trigger:** Home WiFi only (no remote sync in initial build). Photos taken away from home queue locally and sync automatically when the phone rejoins the home WiFi network.

**Dual backup:** Google Photos continues to sync independently on both phones via its own app. Immich and Google Photos operate independently — there is no programmatic link between them.

**Remote sync (future enhancement):** Remote sync via DuckDNS (already in use for JCTsh data pipeline) deferred to a future enhancement. Architecture supports it without structural change.

---

## ML Features

Immich ML features are enabled:

| Feature | Description |
|---|---|
| Facial recognition | Automatically groups photos by detected face; user names faces once and tagging is automatic thereafter |
| Semantic search | Natural-language search ("beach sunset", "hiking", "birthday cake") using image recognition — no manual tagging required |
| Memory albums | "On this day" collections auto-generated from same-date photos across all years |
| Duplicate detection | Flags likely duplicates for review and cleanup |

The Ryzen PRO 6650H with 16GB RAM is confirmed sufficient for concurrent ML workloads alongside photo serving.

---

## Photo Quality Strategy

A hybrid approach is used:

**One-time quality pass during migration:**
- Low-quality photos (blurry, accidental, duplicates, screenshots) are **archived** in Immich (not deleted)
- Archived photos are excluded from all slideshow modes in `photo-tv-display` by default
- Archiving is reversible — no photos are permanently deleted during the quality pass

**Ongoing quality proxy:**
- Photos marked as **favorites** in Immich (via `photo-tv-display` phone controller or Immich app) form a curated high-quality pool over time
- `photo-tv-display` can filter to favorites-only slideshow mode

**Future enhancement hook:** Ongoing automatic quality scoring via third-party ML aesthetic scorer (e.g., CLIP-based aesthetic predictor) running on M8 hardware. Scores written back as Immich tags. `photo-tv-display` filters by quality threshold. Architecture supports this addition without structural change to `photo-server`.

---

## Deletion Logging

When a photo is deleted from Immich via `photo-tv-display`, the deletion is logged in two places for manual Google Photos cleanup:

| Log destination | Purpose |
|---|---|
| Local log file on mini PC | Primary record; persistent even without network |
| Google Sheets (via Apps Script doPost) | Review and action interface; accessible from any device |

**Log fields per deletion:** original filename, date taken, folder/album name, Immich asset ID, deletion timestamp, deleting user (Joseph or Robin).

**Google Photos deletion:** No API path exists (Google locked down the Photos Library API). Manual deletion from Google Photos app using the log as a reference. Log enables batch cleanup on any schedule.

---

## Integration with photo-tv-display

`photo-server` is the backend for `photo-tv-display`. The Node.js server in `photo-tv-display` communicates with Immich exclusively via the Immich REST API:

- Fetch photo assets (with filter support: favorites, albums, people, date range, semantic search, owner)
- Fetch photo metadata (date, GPS/location, recognized faces, folder/album, owner, description)
- Write actions: favorite/unfavorite, delete, add to existing album, create new album and add
- Reverse geocoding: GPS coordinates → human-readable place name (handled by Immich built-in — confirmed in Phase 2)

The `photo-server` component has no direct knowledge of `photo-tv-display` — the API is the contract between them.

---

## Network and Access

- `photo-server` runs on the home LAN
- Accessible to `photo-tv-display` Node.js server via local network
- Accessible to Immich Android app on home WiFi
- Remote access via Tailscale (existing JCTsh infrastructure) for admin tasks
- No direct port forwarding required for initial build

---

## What Is Out of Scope for This Component

The following are handled by `photo-tv-display` or deferred:

- TV slideshow display and phone controller UI → `photo-tv-display`
- Google Home voice trigger for slideshow → future enhancement in `photo-tv-display`
- Remote photo sync from phones away from home → future enhancement
- Ongoing automatic quality scoring → future enhancement hook defined above
- Google Photos deletion automation → not possible (API restriction); manual process with log support

---

## Key Findings and Constraints

- **Google Photos API restriction:** Google locked down the Photos Library API (April 2025). No third-party app can delete from or automate Google Photos. All Google Photos interaction is manual.
- **EXIF and metadata transfer:** Original EXIF transfers intact. Google sidecar JSON metadata (dates, locations) reconciled by immich-go. Face tags, comments/notes transfer inconsistently — notes require manual re-entry for any critical annotations.
- **Album reconstruction:** immich-go handles album reconstruction from Takeout but complex hierarchies may need manual cleanup.
- **Storage split is required:** Immich database and ML models must reside on fast SSD storage. Spinning USB HDD is appropriate for the photo library but not for database or ML cache.
- **RAM is soldered:** 16GB is fixed. Confirmed sufficient for Immich ML workloads.
- **M.2 slots are PCIe only:** SATA drives are not compatible with the M8's M.2 slots.
- **Bus-powered drives selected:** Both USB HDDs are 2.5" bus-powered — no external power supplies required, keeping the installation clean and compact.

---

## Open Items Before Phase 2

All open items resolved:
- [x] USB HDD confirmed: Seagate Backup Plus 1TB (primary); Seagate Momentus 640GB in Insignia enclosure (backup)
- [x] Both HDDs confirmed spinning drives and bus-powered — storage architecture holds as planned

---

## Phase 2 Prerequisites

Before beginning Phase 2 hardware selection, load:
- `README.md` (repo root)
- `CLAUDE.md` (repo root)
- `ENVIRONMENT.md` (repo root)
- `JCTsh-Build-Standards.md` (repo root)
- `jctsh-network.md` (repo root)
- `JCTsh-Parts-Inventory.md` (repo root)

Phase 2 will confirm: OS installation approach, Docker Compose configuration, Immich version, immich-go version, network hostname and IP assignment, and any on-hand parts applicable to this build.

---

## Future Enhancements

**Remote sync from phones away from home:** Expose Immich via DuckDNS (already in use for JCTsh data pipeline). Immich Android app connects remotely. Photos arrive in Immich in near real-time rather than waiting for home WiFi.

**Ongoing automatic quality scoring:** Third-party ML aesthetic scorer runs on M8 hardware, scores all new photos on import, writes scores back as Immich tags. `photo-tv-display` filters by quality threshold. Hook is preserved in the architecture.

**Google Home voice trigger for slideshow:** Implemented in `photo-tv-display`, not `photo-server`. Noted here for cross-reference.
