# Hiking Monitor — Environmental Data Pipeline (Steps 9–11)

This document is the permanent reference for the JCTsh environmental data pipeline.
It covers Google Sheets setup (Step 9), Google Apps Script web app (Step 10), and
Node-RED data handler flow (Step 11). All future environmental sensors inherit this
pipeline with no changes — the wildcard subscription and `source` field handle routing
automatically.

---

## Architecture Overview

```
ESP32 (hiking-monitor)
    │  MQTT publish every 2 min
    ▼
jctsh/components/+/data  (Mosquitto broker)
    │  wildcard subscription
    ▼
Node-RED function node
    │  compute dew_point_f, heat_index_f
    │  add source field
    ▼
HTTP POST  →  Google Apps Script web app
    │  ?key=<secret>
    ▼
Google Sheets "JCTsh Environmental Data"
    └── Environmental Data sheet (one row per reading)
    └── Hiking Observations sheet (future)
```

Node-RED also publishes a log message to MQTT confirming each row appended.

---

## Step 9 — Google Sheets Setup

### Create the Workbook

**Workbook created (2026-06-04):**
- Name: JCTsh Environmental Data
- URL: `https://docs.google.com/spreadsheets/d/1aEgW3NDlu43uUM4Wtx1Hq3LjKm6hz2Lpc82LQZRO8L8/edit`
- Spreadsheet ID: `1aEgW3NDlu43uUM4Wtx1Hq3LjKm6hz2Lpc82LQZRO8L8`

### Environmental Data Sheet

The default Sheet1 becomes the Environmental Data sheet:

1. Rename Sheet1 to `Environmental Data`
2. Add these exact column headers in row 1 (A1 through Z1):

```
timestamp  source  lat  lon  temp_f  humidity_pct  pressure_hpa  dew_point_f
heat_index_f  uv_index  irradiance_wm2  wind_speed_mph  wind_dir_deg  rain_tips
rainin  dailyrainin  battery_v  rssi_dbm  pm1_ug_m3  pm25_ug_m3  pm4_ug_m3
pm10_ug_m3  voc_index  nox_index  illuminance_lx  solar_v
```

**Correction (2026-07-18):** columns Y (`illuminance_lx`) and Z (`solar_v`) were missing from this table — `environmental-data.gs`'s `doPost` has always written them (see the code, not this table, as the source of truth going forward). Added here to match.

Column mapping (A–Z):

| Col | Header | Source |
|---|---|---|
| A | `timestamp` | `ts` from payload (ISO 8601 UTC) |
| B | `source` | `component` from payload (e.g. `hiking-monitor`) |
| C | `lat` | `lat` from payload (null for hiking-monitor) |
| D | `lon` | `lon` from payload (null for hiking-monitor) |
| E | `temp_f` | `temp_f` |
| F | `humidity_pct` | `humidity_pct` |
| G | `pressure_hpa` | `pressure_hpa` |
| H | `dew_point_f` | computed by Node-RED |
| I | `heat_index_f` | computed by Node-RED |
| J | `uv_index` | `uv_index` |
| K | `irradiance_wm2` | `irradiance_wm2` (blank for hiking-monitor) |
| L | `wind_speed_mph` | `wind_speed_mph` (blank for hiking-monitor) |
| M | `wind_dir_deg` | `wind_dir_deg` (blank for hiking-monitor) |
| N | `rain_tips` | `rain_tips` (blank for hiking-monitor) |
| O | `rainin` | computed by Node-RED (blank for hiking-monitor) |
| P | `dailyrainin` | computed by Node-RED (blank for hiking-monitor) |
| Q | `battery_v` | `battery_v` |
| R | `rssi_dbm` | `rssi_dbm` |
| S | `pm1_ug_m3` | `pm1_ug_m3` (blank for hiking-monitor) |
| T | `pm25_ug_m3` | `pm25_ug_m3` (blank for hiking-monitor) |
| U | `pm4_ug_m3` | `pm4_ug_m3` (blank for hiking-monitor) |
| V | `pm10_ug_m3` | `pm10_ug_m3` (blank for hiking-monitor) |
| W | `voc_index` | `voc_index` (blank for hiking-monitor) |
| X | `nox_index` | `nox_index` (blank for hiking-monitor) |
| Y | `illuminance_lx` | `illuminance_lx` (blank for hiking-monitor) |
| Z | `solar_v` | `solar_v` (blank for hiking-monitor) |

Columns for fields a given sensor does not provide are left blank for that row.
Do not add per-device columns — all sources share the same schema.

### Hiking Observations Sheet

1. Add a new sheet named `Hiking Observations`
2. Add these column headers in row 1:

| Col | Header |
|---|---|
| A | `timestamp` |
| B | `observation` |
| C | `categories` |
| D | `source` |

Leave it empty for now — this sheet is populated by the hiking observations pipeline
(future enhancement, see `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`).

---

## Step 10 — Google Apps Script Web App

### Create the Script

1. In the Google Sheets workbook: **Extensions → Apps Script**
2. Delete any existing code in Code.gs
3. Paste the complete code below

### Apps Script Code

The complete, deployable source is in `core/data-pipeline/environmental-data.gs`.
Paste the entire contents of that file into the Apps Script editor. It contains both
`doPost(e)` (environmental sensor data) and `doGet(e)` (GPS track write and lookup, Step 19).

### Set the API Key

Before deploying, store the secret key in Script Properties:

1. In Apps Script editor: **Project Settings** (gear icon) → **Script Properties**
2. Add property: `API_KEY` = `<your secret key>` (generate a random 20+ char string)
3. Store the same key in Node-RED environment variables (see Step 11)

### Deploy as Web App

1. Click **Deploy → New deployment**
2. Click the gear icon next to "Select type" → choose **Web app**
3. Settings:
   - Description: `JCTsh Environmental Data v1`
   - Execute as: **Me**
   - Who has access: **Anyone**
4. Click **Deploy**
5. Copy the deployment URL — format:
   `https://script.google.com/macros/s/<SCRIPT_ID>/exec`

**Deployed (2026-06-04), redeployed as a new deployment (2026-07-18):**
`https://script.google.com/macros/s/AKfycbx9FIywSCFunoBKO7Q2IlX2s7mCFyn1W_se6lWaiPOXWc9aJ_fBb-4S-R2EwWpj4UAsWg/exec`

API key and URL stored in `credentials.local.md`.

**2026-07-18 redeploy note:** adding the `action=export` code (below) via the normal "Manage deployments → pencil → New version" flow silently failed three times in a row — the Active deployment kept serving old code with no error, confirmed by adding a `SCRIPT_VERSION` constant returned in every response and testing `action=version` directly. The Head/Test deployment (`Deploy → Test deployments`, `/dev` URL) correctly showed the new code the whole time, isolating the problem to the versioning step specifically, not the saved code. Creating an entirely new deployment (`Deploy → New deployment`) worked immediately. If this recurs, don't burn time re-trying "New version" — go straight to a new deployment and update the URL everywhere it's referenced (this doc, `credentials.local.md`, Node-RED's `APPS_SCRIPT_URL` environment variable, GPSLogger's custom URL setting on the phone).

6. Store the URL in Node-RED environment variables (see Step 11)

> **Anyone access is required** — Node-RED cannot use OAuth to authenticate as your
> Google account. The secret key in the URL provides the authentication instead.

### Test the Deployment

Test from PowerShell before wiring up Node-RED:

```powershell
Invoke-RestMethod -Uri "https://script.google.com/macros/s/<SCRIPT_ID>/exec?key=<YOUR_KEY>" -Method POST -ContentType "application/json" -Body '{"component":"hiking-monitor","ts":"2026-06-04T12:00:00Z","source":"hiking-monitor","lat":null,"lon":null,"temp_f":95.0,"humidity_pct":18.0,"pressure_hpa":926.0,"dew_point_f":28.5,"heat_index_f":88.2,"uv_index":0.5,"battery_v":3.85,"rssi_dbm":-37}'
```

Expected response: `{"status":"ok"}`

Confirm a new row appeared in the Environmental Data sheet before proceeding to Step 11.

### Read-only Data Export (`action=export`)

Added 2026-07-18 for Hike-izer (CARD-0073) — a generic, read-only `doGet` action that returns any sheet's rows as JSON, optionally filtered by an ISO 8601 `[start, end]` timestamp range on column A. Reuses the same deployment and `API_KEY` auth as everything else in this file; no new credentials.

```
GET <SCRIPT_URL>?key=<API_KEY>&action=export&sheet=<sheet name>&start=<ISO ts>&end=<ISO ts>
```

- `sheet` (required) — `Environmental Data`, `Hiking Observations`, or `GPS Track`. All three have a real UTC ISO timestamp in column A, so date filtering works correctly.
- `start` / `end` (optional) — ISO 8601 timestamps; omit either to leave that side unbounded.
- `Timeline` also works as a `sheet` value, but its column A (`timestamp_az`) is an Arizona-local display string, not UTC ISO — `start`/`end` filtering on it isn't reliable. Fetch it unfiltered and filter client-side instead.

Response: `{"status": "ok", "sheet": "...", "count": N, "rows": [{header: value, ...}, ...]}` — one object per row, keyed by the sheet's actual header row.

**Example — the 2026-06-15 hiking trip's environmental readings:**

```powershell
Invoke-RestMethod -Uri "https://script.google.com/macros/s/<SCRIPT_ID>/exec?key=<YOUR_KEY>&action=export&sheet=Environmental%20Data&start=2026-06-15T00:00:00Z&end=2026-06-29T23:59:59Z"
```

**Redeploy required before this works:** Apps Script only picks up code changes after a new deployment version — paste the updated `core/data-pipeline/environmental-data.gs` into the Apps Script editor, then **Deploy → Manage deployments → pencil icon → Version: New version → Save**. The deployment URL stays the same.

---

## Step 11 — Node-RED Data Handler Flow

### Node-RED Environment Variables

Set these before importing the flow. In Node-RED: **hamburger menu → Settings → Environment Variables** (or edit `settings.js`):

| Variable | Value |
|---|---|
| `APPS_SCRIPT_URL` | The deployment URL from Step 10 |
| `APPS_SCRIPT_KEY` | The API key from Step 10 |

### Flow JSON

The flow is stored in the repo at `core/data-pipeline/environmental-data.flow.json`.

Import via Node-RED UI → hamburger menu → **Import → Clipboard**, then paste the contents of that file.

### Flow Architecture (Step 20 updated)

```
MQTT In (jctsh/components/+/data)
    ↓
Prepare GPS lookup       — parse payload, build action=lookup GET URL
    ↓
GPS lookup               — GET Apps Script action=lookup&ts=<ts>
    ↓
Apply GPS coords         — set lat/lon from nearest GPS trackpoint (±5 min); null if no match
    ↓
Compute derived fields   — dew_point_f, heat_index_f; build POST body
    ↓
POST to Apps Script      — writes row to Environmental Data sheet
    ↓
Check response           — log success or alert to MQTT
    ↓
Log success/error        — MQTT Out → log dashboard
```

### After Import

1. Open the **MQTT In** node (`jctsh/components/+/data`) → select the existing JCTsh MQTT broker
2. Open the **GPS lookup** HTTP Request node → confirm URL is blank (uses `msg.url` set by function)
3. Open the **MQTT Out** node → select the same broker
4. Click **Deploy**

### Verify the Flow

Trigger a test message manually in Node-RED (inject node or MQTT Explorer) or wait for the next hiking-monitor 2-minute data publish. Confirm:

- A new row appears in the Environmental Data sheet
- `dew_point_f` and `heat_index_f` columns are populated
- `source` column shows `hiking-monitor`
- `lat`/`lon` populated for field-mode readings with GPS track; null for home-mode readings
- Log dashboard shows `Sheets row appended for hiking-monitor`

---

## Formulas Reference

### Dew Point (Magnus approximation)

```
temp_c = (temp_f - 32) × 5/9
a = 17.27,  b = 237.7
γ = (a × temp_c / (b + temp_c)) + ln(humidity_pct / 100)
dew_point_c = (b × γ) / (a − γ)
dew_point_f = dew_point_c × 9/5 + 32
```

### Heat Index

**NWS Rothfusz regression** (valid when temp_f ≥ 80°F and humidity_pct ≥ 40%):

```
HI = −42.379 + 2.04901523·T + 10.14333127·H − 0.22475541·T·H
     − 0.00683783·T² − 0.05481717·H² + 0.00122874·T²·H
     + 0.00085282·T·H² − 0.00000199·T²·H²
```

**Simple approximation** (when temp_f < 80°F or humidity_pct < 40%):

```
HI = T + H/5 − 10.3
```

Where T = temp_f, H = humidity_pct.

---

## Field Session Start / End Event Detection (Step 11b)

A separate Node-RED flow detects field session start and end events by watching for
transitions in `rssi_dbm` across all environmental sensor data streams. It works for
any sensor that uses field mode (rssi_dbm=0 when offline).

### How it works

Each data payload includes `rssi_dbm`:
- `rssi_dbm = 0` — device had no WiFi; reading was stored in field mode
- `rssi_dbm ≠ 0` — device was connected to home WiFi; live reading

The flow tracks state per component and fires on transitions:

| Transition | Event | Timestamp used |
|---|---|---|
| `rssi ≠ 0` → `rssi = 0` | **Field session started** | `ts` of first field reading |
| `rssi = 0` → `rssi ≠ 0` | **Field session ended** | `ts` of last field reading |

Events are published to `jctsh/components/<component>/log` (derived from the payload)
and appear in the log dashboard under the originating sensor. State is tracked
per-component so multiple sensors don't interfere with each other.

### Flow file

`core/node-red/hiking-hike-events.flow.json`

Import via Node-RED UI → hamburger menu → **Import → Clipboard**, paste the file contents.

### After Import

1. Open the **MQTT In** node → select the existing JCTsh MQTT broker
2. Open the **MQTT Out** node → select the same broker
3. Click **Deploy**

### Test Procedure

The flow includes four inject nodes for testing. Run them **in sequence** after importing
and deploying. Watch the debug sidebar and log dashboard.

| Step | Inject node | Expected output |
|---|---|---|
| 1 | `Test: home reading (rssi=-45)` | No event (initialises state) |
| 2 | `Test: field reading 1 — session start (rssi=0)` | `Field session started at 2026-06-07T15:00:00Z` |
| 3 | `Test: field reading 2 — mid-session (rssi=0)` | No event |
| 4 | `Test: home reading — session end (rssi=-31)` | `Field session ended at 2026-06-07T15:02:00Z` |

After the test, **reset the function node context** before going live: in Node-RED →
hamburger menu → **Context Data** → select the `hike-events-detect` node → delete
`lastRssi_hiking-monitor` and `lastTs_hiking-monitor`. This prevents the test state
from interfering with real data.

---

## Adding Future Environmental Sensors

No changes to this pipeline are needed when a new environmental sensor is added. The
`jctsh/components/+/data` wildcard catches it automatically. The `source` column in
Sheets identifies the device. Confirm the new sensor's payload conforms to the standard
in `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md` before first flash.
