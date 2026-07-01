# photo-tv-display — Phase 1 Planning Document
**Author:** Joseph C Thomas (JCT)
**Purpose:** Phase 1 Discovery summary and feasibility findings for the JCTsh photo ambient display and phone controller component.
**Version:** 1.0
**Version description:** Initial release — Phase 1 Discovery complete.
**Project:** JCTsh Photo Platform
**Status:** Phase 1 Complete — Ready for Phase 2
**Related files:** `photo-server-phase1-planning.md`

---

## Component Overview

`photo-tv-display` is a custom ambient photo slideshow system consisting of two views of the same web application:

- **TV view:** Fullscreen photo slideshow displayed on the gathering room Google TV, launched via Chromecast
- **Phone controller view:** Touch-based remote control opened in the browser on Joseph's Pixel 10 Pro XL or Robin's Pixel 7 — no app install required, browser bookmark only

A Node.js server running on the `photo-server` mini PC acts as the backend: it serves the web app, maintains websocket sync between TV and phone(s), and makes all Immich API calls on behalf of the controller.

This component depends on `photo-server` being operational. Build `photo-server` first.

---

## Architecture

### Components

| Component | Technology | Runs on |
|---|---|---|
| Web app (TV view) | HTML / CSS / JavaScript | Google TV browser (cast) |
| Web app (phone controller view) | HTML / CSS / JavaScript | Pixel browser (home WiFi) |
| Backend server | Node.js | `photo-server` mini PC |
| Photo/metadata source | Immich REST API | `photo-server` mini PC |
| TV/phone sync | WebSocket | Node.js server |

### Data Flow

```
Immich REST API
      ↓
Node.js server (photo-server mini PC)
      ↓ WebSocket
TV view (Google TV)     Phone controller view (Pixel)
```

The Node.js server is the single point of contact with Immich. Neither the TV view nor the phone controller view calls Immich directly — all photo fetching, metadata retrieval, and write actions (favorite, delete, album) flow through the Node.js server.

### Why This Architecture

- Google Photos API is locked down (April 2025) — Immich with its full REST API is the only viable self-hosted path
- A sideloaded Android TV app was evaluated and rejected: requires Kotlin/Android Studio development from scratch, complex deployment, and higher risk of TV-specific compatibility issues
- Web app + phone controller provides full interactive capability with standard web technologies, browser-based development and testing on Windows PC before any TV involvement, and no app install for either Joseph or Robin

### Access

- TV view and phone controller are accessible on home WiFi only (initial build)
- No external access required for `photo-tv-display`
- Node.js server runs as a background service on the mini PC, always available when the mini PC is on

---

## Users

Both Joseph and Robin have full, equal access to all controller functions. There are no role restrictions between users.

| User | Device | Access level |
|---|---|---|
| Joseph | Pixel 10 Pro XL | Full controller — all actions and settings |
| Robin | Pixel 7 | Full controller — all actions and settings |

Multiple phones can be active as controllers simultaneously. Last-write-wins for settings changes.

---

## Slideshow — Display

### TV View
- Fullscreen photo display, no chrome or UI elements visible during ambient mode
- Photos sourced from Immich via Node.js server according to active filter state
- Configurable photo display duration (set from phone controller)
- Configurable transition style (set from phone controller)

### Transition Styles (configurable)
| Style | Description |
|---|---|
| Crossfade | Photos dissolve into each other smoothly |
| Ken Burns | Slow pan/zoom across photo while displayed, then crossfade to next |
| Cut | Instant switch, no transition |
| Fade to black | Fades out, fades in next photo |

### Metadata Overlay
A subtle overlay displayed on the TV view. All fields and behavior are configurable from the phone controller.

**Configurable metadata fields (each independently toggleable):**
- Date taken
- Location (reverse-geocoded place name from GPS coordinates)
- People (recognized faces from Immich facial recognition)
- Folder / album name
- Whose photo it is (Joseph or Robin)
- Photo description / notes (entered in Immich)

**Configurable display behavior:**
- Always visible — overlay present at all times
- Fade in/out — appears briefly when a new photo loads, then fades away
- On demand — only visible when explicitly requested from phone controller

---

## Slideshow — How It Starts

**Automatic:** Slideshow starts automatically after the Google TV has been idle for a configurable period (screensaver-style). Idle timeout duration is configurable from the phone controller settings.

**Manual:** Either phone controller can start the slideshow at any time regardless of idle state.

**Future enhancement:** Google Home voice trigger ("Hey Google, start the photo slideshow") via Home Assistant integration. Deferred to future build — architecture supports it without structural change.

---

## Phone Controller — Navigation

| Action | Description |
|---|---|
| Previous photo | Go back to the prior photo in the current session sequence |
| Next photo | Advance to the next photo |
| Start slideshow | Launch the slideshow manually on the TV |

---

## Phone Controller — Photo Actions

All actions apply to the photo currently displayed on the TV.

| Action | Description |
|---|---|
| Favorite / unfavorite | Toggle favorite status in Immich |
| Delete | Remove photo from Immich (see Deletion section below) |
| Add to existing album | Pick from a list of existing Immich albums |
| Create new album and add | Name a new album on the fly; photo is added immediately |

---

## Phone Controller — Filter / Curation Modes

The filter panel on the phone controller determines what photos the slideshow draws from. Filters can be changed at any time and take effect on the next photo advance.

| Filter mode | Description |
|---|---|
| Full library random | All photos from both Joseph and Robin, random order |
| By owner | Joseph's photos only, Robin's photos only, or both |
| Favorites only | Only photos marked as favorites in Immich |
| By person | One or more named faces (Immich facial recognition) |
| By concept | Semantic search term (e.g., "hiking", "birthday", "sunset") — Immich smart search drives the pool |
| By location | Photos taken at a specific place |
| By album | Photos from a specific Immich album |
| By date range | Photos within a specified date range |
| On this day | Photos taken on today's date across all years |

Archived photos (low-quality pass from migration) are excluded from all filter modes by default.

---

## Phone Controller — Settings

All settings are runtime-configurable — no redeployment required to change them.

| Setting | Options |
|---|---|
| Photo display duration | Configurable (seconds per photo) |
| Transition style | Crossfade, Ken Burns, Cut, Fade to black |
| Metadata fields displayed | Date, location, people, folder/album, owner, description — each independently toggleable |
| Metadata display behavior | Always visible, fade in/out, on demand |
| Delete confirmation prompt | On (default) or off |
| Slideshow idle auto-start timeout | Configurable duration; disable option |

---

## Deletion

When a photo is deleted from the phone controller:

1. Node.js server receives the delete request
2. If confirmation is enabled (default), phone controller shows a confirmation prompt
3. On confirmation: Node.js server calls Immich REST API to delete the photo
4. Simultaneously, a deletion log entry is written to two destinations:

| Log destination | Purpose |
|---|---|
| Local log file on mini PC | Primary record; persistent regardless of network state |
| Google Sheets row (via Apps Script or Sheets API) | Review and action interface; accessible from any device for manual Google Photos cleanup |

**Deletion log fields:** original filename, date taken, folder/album name, Immich asset ID, deletion timestamp, deleting user (Joseph or Robin).

**Google Photos:** No API path exists to automate deletion from Google Photos (Google locked down the Photos Library API, April 2025). The deletion log enables manual batch cleanup from the Google Photos app on any schedule.

---

## Photo Quality Integration

`photo-tv-display` respects Immich's archive status — archived photos never appear in any slideshow mode. No additional quality logic is required in this component.

The favorites system serves as the ongoing quality proxy: photos favorited via the phone controller accumulate into a curated high-quality pool available via the Favorites filter mode.

Future enhancement hook: when the automatic quality scoring system is implemented in `photo-server`, `photo-tv-display` will gain a quality threshold filter mode. No structural changes to `photo-tv-display` are anticipated.

---

## Non-Technical Requirements (Robin-Facing Summary)

The following plain-language summary is suitable for sharing with Robin:

---

**JCTsh Photo Platform — What It Does**

**The big picture**

We're setting up our own photo library on a small computer at home. All our Google Photos will be copied there, and new photos from our phones will continue going to both Google Photos and our home system automatically. Both of us have our own accounts on the home system, but our photos are displayed together as one shared library.

**The TV experience**

The gathering room TV will display a slideshow of our photos as an ambient display — similar to the screensaver mode Google TV already has, but one we control completely. Photos will rotate through with smooth transitions, and each photo can show a subtle caption at the bottom with things like the date it was taken, where it was taken, who's in it, what folder it's from, and whose photo it is.

**How the slideshow starts**

The slideshow starts automatically after the TV has been idle for a set amount of time — just like a screensaver. You can also start it manually at any time from your phone controller without waiting for the idle timer. In the future we'll be able to start it with a voice command through Google Home.

**Photo quality**

Before the library goes live, photos will be reviewed for quality. Blurry shots, accidental photos, duplicates, and screenshots will be set aside so the slideshow shows our best photos. As we use the system and see photos we love, we can mark them as favorites — over time that becomes our curated collection of the best shots.

**Using your phone as the remote**

When the slideshow is running, you can pick up your Pixel and open a webpage on our home network — no app to install, just a browser bookmark. From your phone you can:
- Go to the previous photo
- Skip to the next photo
- Mark a photo as a favorite
- Delete a photo from our home library
- Add a photo to an existing album or create a new album on the spot
- Change slideshow settings
- Start the slideshow manually

Both our phones work as full controllers with equal access — either of us can do anything from our own phone.

**Choosing what plays**

From the phone controller you can choose what the slideshow draws from:
- All photos randomly (both of ours together)
- Just your photos or just Joseph's photos
- Favorites only
- Photos of specific people (the system learns to recognize faces automatically)
- Photos from a specific place
- Photos from a specific album or date range
- "On this day" — photos taken on today's date in any prior year
- A themed slideshow by concept — for example, search "hiking" or "birthday" and the slideshow pulls matching photos automatically

**What you can customize**

From the phone controller you can change:
- How long each photo stays on screen before advancing
- How photos transition (smooth fade, slow pan/zoom, instant cut, fade to black)
- What information shows in the caption (date, location, people, folder name, whose photo it is, photo description)
- Whether the caption always shows, fades in briefly when a photo changes, or only appears when you ask for it
- Whether you want a confirmation prompt before deleting a photo
- How long the TV needs to be idle before the slideshow starts automatically

**A note on deleting photos**

Deleting a photo removes it from our home library only. Google Photos stays untouched — it's our safety net. If you want to also remove a deleted photo from Google Photos, we keep a log of everything deleted (date, filename, where it was from) so you can find it easily and remove it manually from the Google Photos app.

**What stays the same**

Google Photos keeps working exactly as it does today. New photos from your Pixel back up to Google Photos automatically. Nothing about how you use your phone changes.

---

## Key Constraints and Findings

- **Google Photos API restriction:** No automated deletion from or control of Google Photos is possible. All Google Photos interaction is manual.
- **No native Android TV app:** Sideloaded APK approach evaluated and rejected in favor of web app + phone controller due to Kotlin/Android Studio complexity and deployment risk for a developer starting from zero.
- **Web app is home WiFi only:** No remote access required or planned for initial build.
- **Node.js is the sole Immich API caller:** TV view and phone controller never call Immich directly — all API interaction is server-side.
- **WebSocket sync:** TV and phone stay in sync via WebSocket. Multiple phones can be active simultaneously.
- **Reverse geocoding:** GPS coordinates → human-readable place name. Implementation approach (Immich built-in vs Node.js layer) to be determined in Phase 3.

---

## What Is Out of Scope for This Component

- Photo storage, migration, ML processing → `photo-server`
- Google Photos sync → handled independently by Google Photos app on each phone
- Google Home voice trigger → future enhancement (see below)
- Remote access to phone controller away from home WiFi → not planned
- Automatic quality scoring → future enhancement hook in `photo-server`

---

## Phase 2 Prerequisites

Before beginning Phase 2, `photo-server` Phase 1 planning must be complete and Phase 2 hardware selection for `photo-server` should be underway or complete. Load the standard Phase 2 file set:

- `README.md` (repo root)
- `CLAUDE.md` (repo root)
- `ENVIRONMENT.md` (repo root)
- `JCTsh-Build-Standards.md` (repo root)
- `jctsh-network.md` (repo root)
- `JCTsh-Parts-Inventory.md` (repo root)
- All existing component READMEs
- `photo-server-phase1-planning.md` (as reference for backend API contract)

Phase 2 will confirm: Node.js version, Chromecast launch mechanism, WebSocket library, Google Sheets API integration approach for deletion log, and network hostname/port assignments.

---

## Future Enhancements

**Google Home voice trigger:** "Hey Google, start the photo slideshow" triggers the slideshow via Home Assistant routine → Node.js server API call. Requires Home Assistant integration with the Node.js server. Deferred — architecture supports it without structural change.

**Automatic quality threshold filter:** Once `photo-server` implements ongoing ML aesthetic scoring and writes scores as Immich tags, `photo-tv-display` gains a quality threshold filter mode. No structural changes anticipated.

**Remote phone controller access:** Expose Node.js server via DuckDNS (already in use for JCTsh data pipeline) so the phone controller works away from home WiFi. Deferred — architecture supports it without structural change.

**Simultaneous multi-phone controller coordination:** Currently last-write-wins for settings. Future enhancement could add awareness of multiple active controllers (e.g., conflict notification). Low priority.
