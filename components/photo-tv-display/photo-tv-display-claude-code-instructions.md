# photo-tv-display — Claude Code Instructions
**Author:** Joseph C Thomas (JCT)
**Purpose:** Step-by-step build instructions for Claude Code to execute the `photo-tv-display` component — ambient photo slideshow web app with phone controller, running on the `photo-server` mini PC.
**Version:** 1.0
**Version description:** Initial release.
**Project:** JCTsh Photo Platform
**Status:** Ready for execution
**Related files:** `photo-tv-display-phase1-planning.md`, `photo-tv-display-phase2-planning.md`, `photo-server-claude-code-instructions.md`, `JCTsh-Build-Standards.md`, `CLAUDE.md`

---

## Step 0 — Read Required Context

Before any work begins, read:
- `JCTsh-Build-Standards.md` (repo root)
- `photo-tv-display-phase1-planning.md` and `photo-tv-display-phase2-planning.md` (this component's planning history)
- `photo-server-claude-code-instructions.md` and the resulting `components/photo-server/` documentation — confirm `photo-server` is fully built and operational before proceeding
- `CLAUDE.md` (repo root) — existing HA REST API integration pattern (Node-RED → HA REST API → SmartThings is the precedent; here it's Node.js → HA REST API directly)

**Hard dependency check:** Do not begin this build until `photo-server` is confirmed operational — Immich running, both user accounts created, and at minimum a test subset of photos imported (full migration does not need to be complete, but Immich must be reachable and have queryable data for development and testing).

---

## Pre-Build Checklist (Confirm Before Proceeding)

- [ ] `photo-server` Immich instance is running and reachable at `http://photo-server.local:2283`
- [ ] Node.js LTS is installed on the M8 (completed in `photo-server` Step 14)
- [ ] Home Assistant has a working `media_player` entity for the Google TV via its Cast integration — **verify this in the HA UI before writing any casting code.** If it does not exist or does not work, stop and report back; this is a prerequisite that may require HA-side configuration outside this component's scope.
- [ ] HA long-lived access token generated and available (Joseph generates this manually in HA profile settings — do not attempt to generate it programmatically)
- [ ] Joseph has created a new, separate Google Sheet for deletion logging (per `photo-server` Step 13) and the Apps Script `doPost` endpoint is deployed and reachable

---

## Step 1 — Project Structure

1. Create the component directory:
   ```bash
   mkdir -p ~/photo-tv-display
   cd ~/photo-tv-display
   npm init -y
   ```
2. Install dependencies:
   ```bash
   npm install express ws node-fetch dotenv
   ```
   - `express` — serves the TV view and controller view HTML/CSS/JS, and hosts the REST endpoints the frontend calls
   - `ws` — WebSocket library (per Phase 2 decision)
   - `node-fetch` — for server-side calls to Immich and HA REST APIs
   - `dotenv` — loads credentials from a gitignored `.env` file (Immich API key, HA token, Apps Script URL)

3. Create the directory structure:
   ```
   photo-tv-display/
   ├── server.js                 — main Node.js server
   ├── routes/
   │   ├── immich.js              — Immich API wrapper functions
   │   ├── homeassistant.js       — HA REST API wrapper functions
   │   └── deletion-log.js        — local file + Apps Script logging
   ├── public/
   │   ├── tv.html                — TV view
   │   ├── controller.html        — phone controller view
   │   ├── tv.js
   │   ├── controller.js
   │   └── styles.css
   ├── .env                       — gitignored; Immich API key, HA token, Apps Script URL
   └── .env.example                — committed template with placeholder values
   ```

---

## Step 2 — Environment Configuration

Create `.env` (gitignored) with:
```
IMMICH_SERVER_URL=http://localhost:2283
IMMICH_API_KEY_JOSEPH=<api key from photo-server Step 11>
IMMICH_API_KEY_ROBIN=<api key from photo-server Step 11>
HA_SERVER_URL=http://raspberrypi.local:8123
HA_LONG_LIVED_TOKEN=<token Joseph generated in HA>
DELETION_LOG_SHEET_APPS_SCRIPT_URL=<Apps Script doPost deployment URL>
DELETION_LOG_LOCAL_PATH=/mnt/photo-library/deletion-log.csv
PORT=3000
TZ=America/Phoenix
```

Create `.env.example` with the same keys and placeholder values (no real credentials) — this is the committed reference.

**Reminder:** Never commit `.env` to the repo. Add it to `.gitignore` if not already covered by a broader pattern.

---

## Step 3 — Immich API Integration Layer (`routes/immich.js`)

Implement wrapper functions for all Immich operations identified in Phase 2 planning. Consult the current Immich API documentation (api.immich.app) for exact endpoint paths and request/response shapes at build time — Immich's API evolves between releases.

**Required functions:**

| Function | Purpose |
|---|---|
| `getPhotosByFilter(filterParams)` | Fetch asset list matching active filter mode (random/owner/favorites/person/concept/location/album/date-range/on-this-day) |
| `getAssetMetadata(assetId)` | Fetch date taken, location (city/state — see formatting note below), people, album/folder, owner, description |
| `getAlbums(userId)` | Fetch album list for the "add to existing album" controller action |
| `toggleFavorite(assetId, favoriteState)` | Set or unset favorite |
| `deleteAsset(assetId)` | Delete the asset — triggers deletion log write (Step 6) |
| `addToAlbum(assetId, albumId)` | Add asset to existing album |
| `createAlbum(albumName, assetId)` | Create new album and add asset |

**Location formatting:** When building the display string for the metadata overlay, format as `City, State` for US locations (omit country) and `City, Country` for non-US locations. Immich's asset metadata includes city/state/country fields populated automatically via its built-in reverse geocoding — no geocoding call needed, only string formatting logic:
```javascript
function formatLocation(city, state, country) {
  if (!city) return null;
  if (country === 'United States' || country === 'USA') {
    return state ? `${city}, ${state}` : city;
  }
  return country ? `${city}, ${country}` : city;
}
```

**Multi-account queries:** Since Joseph and Robin have separate Immich accounts, fetching the combined shared-library pool requires querying with both API keys and merging results. Implement a helper that queries both accounts and tags each asset with its owner before merging, so the "by owner" filter mode and the metadata "whose photo" field both work correctly.

---

## Step 4 — Home Assistant Integration Layer (`routes/homeassistant.js`)

1. Implement `startSlideshow(mediaPlayerEntityId)`:
   ```javascript
   async function startSlideshow(entityId) {
     const response = await fetch(`${process.env.HA_SERVER_URL}/api/services/media_player/play_media`, {
       method: 'POST',
       headers: {
         'Authorization': `Bearer ${process.env.HA_LONG_LIVED_TOKEN}`,
         'Content-Type': 'application/json',
       },
       body: JSON.stringify({
         entity_id: entityId,
         media_content_id: `http://photo-server.local:${process.env.PORT}/tv`,
         media_content_type: 'url',
       }),
     });
     return response.json();
   }
   ```
2. **Before implementing the idle-detection automation logic, manually inspect the HA `media_player` entity for the Google TV** (Developer Tools → States in HA UI) and observe what state values it reports when: actively casting/playing, sitting on the home screen, and powered off. Document actual observed values in `testing.md` (Step 11).
3. Implement idle detection using whichever approach matches what's actually observed:
   - **If HA's own automation UI is sufficient:** build the idle-trigger automation directly in HA (Settings → Automations) rather than polling from Node.js. This is likely the cleaner approach — let HA watch its own entity state and call back to start the slideshow via a webhook to the Node.js server, or have the HA automation call `media_player.play_media` directly without needing Node.js in the loop for the trigger itself.
   - **If Node.js needs to poll:** implement a periodic check (e.g. every 60 seconds) querying the `media_player` entity state via HA REST API, tracking how long it has remained in the idle-equivalent state, and calling `startSlideshow()` once the configured threshold is exceeded.

**Recommendation to evaluate during build:** Letting HA handle the idle automation natively (option one above) is likely simpler and more reliable than Node.js polling, since HA already has native state-duration trigger conditions (`for:` in automation triggers). Use this approach unless there's a specific reason Node.js needs to own the timing logic (e.g., if the idle timeout must be configurable from the phone controller in real time without editing an HA automation). Given that idle timeout IS a phone-controller-configurable setting per Phase 1 spec, the Node.js-polling approach is likely necessary so the threshold can change at runtime — but confirm this reasoning holds before committing to the implementation.

---

## Step 5 — WebSocket Server (`server.js`)

1. Set up the `ws` WebSocket server alongside the Express HTTP server
2. Implement broadcast of state changes to all connected clients (TV view + any phone controllers):
   - Current asset being displayed
   - Active filter mode
   - Active settings (display duration, transition style, metadata fields/behavior, idle timeout)
3. Implement message handlers for controller actions (favorite, delete, add to album, create album, navigation, filter change, settings change) — each handler calls the relevant Immich/HA function and then broadcasts the resulting state change to all connected clients
4. **Last-write-wins:** no conflict resolution needed for the initial build — the most recent setting change simply overwrites and broadcasts

---

## Step 6 — Deletion Logging (`routes/deletion-log.js`)

1. Implement `logDeletion(assetMetadata, deletedBy)`:
   - Append a row to the local CSV file at `process.env.DELETION_LOG_LOCAL_PATH`
   - POST the same record as JSON to `process.env.DELETION_LOG_SHEET_APPS_SCRIPT_URL`
2. Call this function from the `deleteAsset` flow in Step 3 — log **before or immediately after** the Immich delete call completes, not before confirming the delete actually succeeded
3. Log record fields: `timestamp`, `filename`, `date_taken`, `album_folder`, `immich_asset_id`, `deleted_by`
4. Handle the case where the Apps Script POST fails (e.g., network issue) without blocking the delete itself — the local file write is the primary record; log a warning if the Sheets POST fails, but do not roll back the deletion

---

## Step 7 — TV View (`public/tv.html` + `tv.js`)

1. Build a fullscreen, no-chrome HTML page that:
   - Connects to the WebSocket server on load
   - Fetches the initial photo pool based on the current filter (request via WebSocket or a REST endpoint)
   - Displays the current photo fullscreen
   - Implements the four transition styles (crossfade, Ken Burns, cut, fade to black) in CSS/JS, switching based on the active setting
   - Implements the metadata overlay with configurable fields and configurable display behavior (always visible, fade in/out, on demand)
   - Auto-advances based on the configured display duration
   - Listens for WebSocket messages from the controller (navigation, filter change, settings change) and updates display accordingly
2. Keep this page free of any visible UI controls — it is a passive display surface only

---

## Step 8 — Phone Controller View (`public/controller.html` + `controller.js`)

1. Build a mobile-responsive HTML page with:
   - Navigation controls (previous, next)
   - Action buttons (favorite/unfavorite, delete with confirmation if enabled, add to existing album, create new album)
   - Filter panel (all curation modes from Phase 1/2 planning)
   - Settings panel (display duration, transition style, metadata fields, metadata behavior, delete confirmation toggle, idle timeout)
   - "Start Slideshow" button (manual trigger)
2. Connect to the same WebSocket server — sends action/setting-change messages, receives state updates so the controller UI reflects the current photo and settings accurately even if changed from another connected phone
3. No app install required — this is accessed directly via browser at `http://photo-server.local:3000/controller`, bookmarked by both Joseph and Robin

---

## Step 9 — Express Routing (`server.js`)

1. Serve `public/tv.html` at `/tv`
2. Serve `public/controller.html` at `/controller`
3. Serve static assets (`tv.js`, `controller.js`, `styles.css`) from `/public`
4. Mount any REST endpoints needed alongside the WebSocket messages (e.g., initial photo pool fetch on page load before WebSocket connection is fully established)

---

## Step 10 — systemd Service

Run the Node.js server as a persistent background service rather than a manually-started process:

1. Create `/etc/systemd/system/photo-tv-display.service`:
   ```ini
   [Unit]
   Description=JCTsh Photo TV Display
   After=network.target docker.service

   [Service]
   Type=simple
   User=<install user>
   WorkingDirectory=/home/<install user>/photo-tv-display
   ExecStart=/usr/bin/node server.js
   Restart=on-failure
   EnvironmentFile=/home/<install user>/photo-tv-display/.env

   [Install]
   WantedBy=multi-user.target
   ```
2. Enable and start:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable photo-tv-display
   sudo systemctl start photo-tv-display
   ```
3. Verify:
   ```bash
   sudo systemctl status photo-tv-display
   journalctl -u photo-tv-display -f
   ```

---

## Step 11 — Testing

Document actual results in `testing.md`. Required validation:

1. **TV view loads and displays photos** from Immich via the Node.js server
2. **All four transitions** render correctly
3. **Metadata overlay** displays correctly for all field combinations and all three display behaviors
4. **Phone controller actions** (favorite, delete, add to album, create album, navigation) work and reflect correctly on the TV view via WebSocket
5. **Multiple simultaneous controllers** (test with both Joseph's and Robin's phones connected at once) — confirm last-write-wins behaves as expected, no crashes or desync
6. **All filter/curation modes** return expected results, including the "by owner" and combined shared-library modes
7. **Manual slideshow start** via HA REST API successfully casts to the Google TV
8. **HA `media_player` idle-state observation** — document actual states observed (per Step 4.2) and confirm the auto-start automation triggers correctly after the configured idle duration
9. **Deletion logging** — confirm both the local CSV and the Google Sheet receive a correct row when a test deletion is performed
10. **WiFi reconnection** — disconnect a phone's WiFi briefly during active use and reconnect; confirm `ws` recovers cleanly. If reconnection is unreliable, flag this and revisit the Socket.IO fallback noted in Phase 2 planning.

---

## Step 12 — Documentation

Per `JCTsh-Build-Standards.md` §7, create the following in `components/photo-tv-display/`:

| Document | Contents |
|---|---|
| `README.md` | What `photo-tv-display` does, URLs, dependencies on `photo-server` and Home Assistant |
| `server.js` and supporting source files | The actual implementation (committed to repo) |
| `setup.md` | Node.js install (already done in `photo-server` build), npm install, `.env` setup, systemd service setup — actual steps as executed |
| `apps-script.gs` | Deletion log Apps Script source (or reference to where it's documented in `photo-server`'s `deletion-log-setup.md` if not duplicated here) |
| `tv-view.md` | Implementation notes — transitions, metadata overlay logic, casting integration |
| `controller-view.md` | Implementation notes — actions, filters, settings, WebSocket message protocol |
| `testing.md` | Results from Step 11, including actual HA `media_player` state observations |
| `operations.md` | How to check the service is running, restart it, view logs, update Node.js dependencies |

---

## Step 13 — Update Repo-Wide Files

1. Add `photo-tv-display` to the Components table in root `README.md`:
   ```
   | [photo-tv-display](components/photo-tv-display/) | Ambient photo slideshow + phone controller for Google TV, backed by photo-server | Production |
   ```
2. No `jctsh-network.md` changes needed — this component runs on the already-documented `photo-server` host and uses an already-reserved port

---

## Step 14 — Harvest Step (Per Build Standards)

Propose any new patterns discovered during this build back to `JCTsh-Build-Standards.md` for Joseph's review. Likely candidates:

- A new section for Node.js / Express / WebSocket component standards (first component of this type)
- The pattern of Node.js calling HA's REST API directly (parallel to the existing Node-RED → HA REST API pattern, but documenting when bypassing Node-RED is appropriate)
- Multi-account API aggregation pattern (querying multiple Immich accounts and merging results) — may be reusable if other multi-user components emerge
- The location-formatting convention (city/state for US, city/country for non-US) as a general display standard if other components ever surface location data to a UI

Present as proposed additions — do not edit `JCTsh-Build-Standards.md` directly without confirmation.

---

## Known Risks and Things to Watch For

- **HA `media_player` entity may not exist yet** — verify in Step 0/pre-build checklist before writing any casting code. If absent, this requires HA-side Cast integration setup first, which is outside this component's scope and should be reported back rather than worked around.
- **Idle-state values are unconfirmed** — do not hardcode assumptions about what HA reports for "idle." Observe first (Step 4.2), then implement.
- **Immich API surface changes between releases** — consult current API docs at build time rather than relying on this document's specifics for exact endpoint paths.
- **Two API keys, two accounts** — be careful not to cross-wire Joseph's and Robin's API keys when implementing the multi-account merge logic; a bug here could misattribute ownership or, worse, allow one account's credentials to act on the other's data unintentionally.
- **WebSocket reconnection** — `ws` does not handle reconnection automatically; if phones dropping WiFi briefly causes a poor experience, this is the documented trigger to revisit Socket.IO (Phase 2 planning, not a silent workaround).
