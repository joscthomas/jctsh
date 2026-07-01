# photo-tv-display — Phase 2 Planning Document
**Author:** Joseph C Thomas (JCT)
**Purpose:** Phase 2 architecture and technical decisions for the JCTsh photo ambient display and phone controller component.
**Version:** 1.0
**Version description:** Initial release — Phase 2 complete.
**Project:** JCTsh Photo Platform
**Status:** Phase 2 Complete — Ready for Phase 3
**Related files:** `photo-tv-display-phase1-planning.md`, `photo-server-phase1-planning.md`, `photo-server-phase2-planning.md`

---

## Component Overview

`photo-tv-display` is the custom ambient photo slideshow and phone controller web application. It depends on `photo-server` (Immich) being operational. This component runs entirely on the `photo-server` mini PC (GMKtec M8) — no separate hardware.

---

## Hardware

No dedicated hardware. Runs as a Node.js process on the `photo-server` M8 (Ryzen PRO 6650H, 16GB RAM), confirmed sufficient to run alongside Immich and its ML workloads.

---

## Software Stack

| Layer | Technology | Notes |
|---|---|---|
| Server runtime | Node.js | Current LTS at build time; installed on `photo-server` M8 |
| WebSocket library | `ws` | Lightweight, sufficient for home LAN use; see note below on Socket.IO |
| TV view / controller view | HTML / CSS / JavaScript | Served by Node.js; no frontend framework required |
| Immich integration | Immich REST API | All calls originate from the Node.js server — neither TV view nor phone controller calls Immich directly |
| TV cast mechanism | Home Assistant REST API | `POST /api/services/media_player/play_media` |
| Reverse geocoding | Built into Immich | No additional integration required — see Metadata section |
| Deletion logging | Local file + Google Sheets (Apps Script `doPost`) | New, separate Google Sheet — not the existing JCTsh environmental data sheet |

### WebSocket Library Note

`ws` is the initial choice for simplicity — sufficient for a home LAN with a small number of devices (TV + 1–2 phones). If phone reconnection after WiFi drops proves unreliable in practice during Phase 3 testing, **Socket.IO** is the documented fallback — it handles reconnection and transport fallback automatically at the cost of a heavier dependency. This decision should be revisited only if `ws` reconnection issues are observed; do not pre-optimize.

---

## Architecture

### Data Flow

```
Immich REST API ←──────────────┐
                                │
Home Assistant REST API ←──────┤
                                │
                         Node.js server (photo-server M8, port 3000)
                                │
                         WebSocket (ws)
                                │
              ┌─────────────────┴─────────────────┐
              ▼                                     ▼
        TV view (cast via HA)              Phone controller view
        Google TV, gathering room          Joseph: Pixel 10 Pro XL
                                            Robin: Pixel 7
```

The Node.js server is the single point of contact with both Immich and Home Assistant. Neither the TV view nor the phone controller view calls either API directly.

### Why Home Assistant for Casting (Not Direct Cast Library)

Three options were evaluated:
1. Manual cast from phone each time — rejected, too much friction for daily ambient use
2. Direct Node.js casting library (e.g. `castv2-client`) — rejected, adds casting code to build and maintain with no HA dependency benefit, and duplicates capability HA likely already has via its Google Cast integration
3. **Home Assistant `media_player.play_media` via REST API — selected.** HA already has a `media_player` entity for the Google TV via its Cast integration. This is a low-effort, low-maintenance path that also directly supports the future Google Home voice trigger enhancement (the voice automation simply calls the same HA service).

### Why Not Node-RED

Node-RED's role in JCTsh is central logic for the ESP32/MQTT sensor ecosystem (per `CLAUDE.md`). `photo-tv-display` has no MQTT involvement and no relationship to that ecosystem. Routing through Node-RED would add a dependency with no benefit. The Node.js server calls the HA REST API directly.

---

## TV Slideshow Start Mechanism

### Manual Start

Phone controller "Start Slideshow" button → Node.js server → HA REST API `POST /api/services/media_player/play_media` with the slideshow URL → HA's Google Cast integration casts to the Google TV.

### Automatic Start (Idle Detection)

**Mechanism:** Home Assistant tracks the Google TV's `media_player` entity state via its existing Cast integration. An HA automation triggers after the TV has remained in an idle-equivalent state for a configurable duration, calling the same `media_player.play_media` service used for manual start.

**Important — requires empirical validation during Phase 3/build:** The exact states Google TV reports via HA's Cast integration (e.g., `idle`, `off`, `paused`, or some other value when sitting on the home screen) are not confirmed and must be observed firsthand once the HA `media_player` entity is available for testing. The automation's trigger condition cannot be finalized until this is verified against the actual TV.

**Idle duration:** Configurable from the phone controller settings panel (per Phase 1 spec).

### Future Enhancement — Google Home Voice Trigger

"Hey Google, start the photo slideshow" → HA automation (voice-triggered) → same `media_player.play_media` service call already built for manual/auto start. No new casting infrastructure needed — only a new HA automation trigger. This is the direct payoff of choosing the HA-based approach now.

---

## Immich API Integration

All Immich REST API calls originate from the Node.js server.

### Read Operations

| Purpose | Data retrieved |
|---|---|
| Fetch photo pool for current filter | Asset list matching active filter (random/owner/favorites/person/concept/location/album/date range/on-this-day) |
| Fetch photo metadata | Date taken, GPS-derived location (city/state/country — see below), recognized faces, folder/album name, owner, description |
| Fetch album list | For "add to existing album" controller action |

### Write Operations

| Purpose | Immich API action |
|---|---|
| Favorite / unfavorite | Update asset favorite status |
| Delete | Delete asset (triggers deletion log write — see below) |
| Add to existing album | Add asset to specified album |
| Create new album | Create album, then add asset |

### Metadata — Location Display

Immich performs reverse geocoding automatically during EXIF extraction at import time, resolving GPS coordinates to **city, state, and country** using its built-in GeoNames database. This data is already attached to the asset record — the Node.js server reads it directly from the standard asset metadata fetch. No separate geocoding API call, no third-party service, and no additional integration work required.

**Display format:** City and state for US locations (e.g., "Tucson, Arizona") — country omitted for US locations. For non-US locations, include country (e.g., "Paris, France").

---

## WebSocket Sync

`ws` library on the Node.js server maintains real-time state sync between the TV view and any connected phone controller(s).

**Synced state includes:**
- Current photo being displayed (so controller previous/next reflects accurately)
- Active filter mode
- Active settings (display duration, transition style, metadata fields/behavior, idle timeout)
- Favorite/delete/album action confirmations (so multiple phones see consistent state)

**Multiple controllers:** Both Joseph's and Robin's phones can connect simultaneously. Last-write-wins for settings changes — no conflict resolution UI in initial build.

---

## Deletion Logging

### Trigger

Phone controller delete action (with confirmation prompt, if enabled) → Node.js server → Immich delete API call → simultaneous write to both log destinations.

### Log Destinations

| Destination | Detail |
|---|---|
| Local log file | `/mnt/photo-library/deletion-log.csv` on the USB HDD (per `photo-server` Phase 2) |
| Google Sheets | **New, separate Google Sheet** dedicated to this component — not the existing JCTsh environmental data sheet |

### Google Sheets Integration Method

Apps Script `doPost` web app endpoint, consistent with the existing JCTsh pattern (per `JCTsh-Build-Standards.md` §5.5 GPS lookup pattern, which uses the same Apps Script `doGet`/`doPost` approach). The Node.js server POSTs the deletion record as JSON; the Apps Script appends a row to the dedicated sheet.

**Why a separate sheet:** Keeps the photo platform's data isolated from the environmental sensor data pipeline. No shared Apps Script logic, no risk of one component's changes affecting the other.

### Log Fields

`timestamp`, `filename`, `date_taken`, `album_folder`, `immich_asset_id`, `deleted_by` (Joseph or Robin)

### Google Photos Cross-Reference

No API path exists to automate deletion from Google Photos (API locked down April 2025). The log is the only mechanism enabling manual batch cleanup in the Google Photos app.

---

## Slideshow Display

### Filter / Curation Modes

(Carried forward from Phase 1 — confirmed unchanged in Phase 2)

| Mode | Implementation note |
|---|---|
| Full library random | Default query against both Joseph's and Robin's accounts |
| By owner | Filter by Immich account |
| Favorites only | Filter by favorite flag |
| By person | Filter by recognized face (Immich facial recognition) |
| By concept | Immich Smart Search (CLIP) semantic query |
| By location | Filter by reverse-geocoded city/state/country |
| By album | Filter by album ID |
| By date range | Filter by date taken |
| On this day | Filter by same calendar date across all years |

Archived photos are excluded from all modes by default (per `photo-server` quality pass).

### Transitions

Crossfade, Ken Burns, Cut, Fade to black — implemented in TV view JavaScript/CSS. Configurable from phone controller.

### Metadata Overlay

Configurable fields: date taken, location (city/state/country), people, folder/album name, owner, description. Configurable behavior: always visible, fade in/out, on demand.

---

## Network and Ports

| Service | Port | Notes |
|---|---|---|
| `photo-tv-display` Node.js server | 3000 | Reserved in `photo-server` Phase 2 |
| Access (TV view) | `http://photo-server.local:3000/tv` | Cast target URL |
| Access (controller view) | `http://photo-server.local:3000/controller` | Opened directly in phone browser, bookmarked |

Home WiFi only — no remote access for initial build, consistent with `photo-server` Phase 1/2 decisions.

---

## Integration with Existing JCTsh Infrastructure

| Integration | Detail |
|---|---|
| Home Assistant | Node.js server calls HA REST API directly for `media_player.play_media`. Requires an HA long-lived access token, stored as an environment variable on the M8 (not committed to repo). |
| Google Sheets | New dedicated sheet + Apps Script `doPost` endpoint, separate from existing JCTsh environmental data sheet |
| Node-RED | Not used |
| MQTT | Not used |
| SmartThings | Not used |

### HA Authentication

A Home Assistant long-lived access token must be generated (HA profile settings) and stored securely on the M8 as an environment variable for the Node.js server to authenticate REST API calls. Document the token generation step in Phase 3 build instructions; never commit the token to the repo.

---

## What Is Out of Scope for This Component

- Photo storage, migration, ML processing → `photo-server`
- Reverse geocoding implementation → handled entirely by Immich, no work needed here
- Google Photos sync → independent, handled by Google Photos app on each phone
- Remote access to phone controller → not planned for initial build

---

## Documentation Required (Phase 3 / Build)

| Document | Purpose |
|---|---|
| `README.md` | What `photo-tv-display` does, URLs, dependencies |
| `server.js` (or equivalent) | Node.js server source — Immich API, HA API, WebSocket handling |
| `setup.md` | Node.js installation, environment variables, HA token generation, service startup |
| `apps-script.gs` | Deletion log Apps Script source (separate sheet) |
| `tv-view.md` | TV view implementation notes — transitions, metadata overlay, casting |
| `controller-view.md` | Phone controller implementation notes — actions, filters, settings |
| `testing.md` | Validation procedure including empirical HA idle-state observation |
| `operations.md` | Day-to-day use, troubleshooting, restarting the service |

---

## Open Items Before Phase 3

- [ ] Verify HA already has a `media_player` entity for the Google TV via Cast integration (check HA UI)
- [ ] Empirically observe Google TV idle/off/paused states reported to HA before finalizing auto-start automation logic
- [ ] Generate HA long-lived access token for Node.js server authentication
- [ ] Create new dedicated Google Sheet for deletion log
- [ ] Confirm Node.js LTS version to install on `photo-server` at build time

---

## Future Enhancements

| Enhancement | Notes |
|---|---|
| Google Home voice trigger | Add HA automation triggered by voice intent, calling the same `media_player.play_media` service already implemented for manual/auto start. No new casting infrastructure required. |
| Quality threshold filter | Once `photo-server` implements automatic ML aesthetic scoring, add a filter mode here. No structural change anticipated. |
| Remote controller access | Expose Node.js server via DuckDNS (architecture supports without restructuring). |
| Socket.IO migration | If `ws` reconnection proves unreliable on real-world WiFi conditions during use. |
| Multi-controller conflict awareness | Currently last-write-wins; could add active-controller notification later. Low priority. |
