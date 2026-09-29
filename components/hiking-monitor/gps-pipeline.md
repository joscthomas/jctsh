# Hiking Monitor — GPS Track Pipeline (Steps 19–20)

> **Current state (2026-09-29 13:10 MST, CARD-0349/CARD-0365).** GPS points go to **`data-pipeline-api`**
> (`https://hikes.jctnet.com/data/gps`), stored in the `gps_track` table — not the Google Apps Script
> and Google Sheet this document was written for. **Section 1 below is current** (GPSLogger
> configuration). **Sections 2–4 and the architecture diagram describe the retired Apps Script/Sheet
> implementation** and are kept as history; for how the gateway works see
> `core/data-pipeline/README.md`.

This document covers GPSLogger Android configuration (Step 19), the Google Apps Script GPS endpoint
(Step 19), the "GPS Track" sheet setup (Step 19), and the timestamp lookup endpoint used to
populate `lat`/`lon` in the environmental data pipeline (Step 20).

---

## Architecture Overview

```
Pixel 10 Pro XL (GPSLogger app)
    │  GET every 30 seconds while hiking
    ▼
Google Apps Script  action=gps
    │  append one row
    ▼
"GPS Track" sheet in "JCTsh Environmental Data"

          ↕  (Step 20 — on replay/upload)

Node-RED wildcard data handler
    │  GET action=lookup&ts=<sensor_ts>
    ▼
Google Apps Script  action=lookup
    │  nearest trackpoint within ±5 min
    ▼
lat/lon fields populated in Environmental Data sheet
```

No port forwarding. No public Pi access. GPSLogger posts directly to Google over cellular.

---

## Section 1 — GPSLogger Android Configuration

**App:** GPSLogger for Android (open source)
- Play Store: search "GPSLogger for Android" by BasicAirData
- F-Droid: `com.mendhak.gpslogger`

### Installation and Setup

1. Install GPSLogger on Pixel 10 Pro XL
2. Open GPSLogger → General Options:
   - **Start on bootup:** off
   - **Start logging when app starts:** on
   - **Notification:** on (keeps service alive in background)
3. Performance Options:
   - **Logging interval:** 30 seconds
   - **Distance filter:** 0 (log all points)
   - **Accuracy filter:** 40 meters (skip points with accuracy worse than 40m)
4. Logging Details → uncheck all local file formats (GPX, KML, CSV) — Google Sheets is the only needed output

### Custom URL Logger

In GPSLogger → Logging Details → Log to custom URL:

| Setting | Value |
|---|---|
| URL | `https://hikes.jctnet.com/data/gps?lat=%LAT&lon=%LON&ts=%TIME&acc=%ACC&alt=%ALT&direction=%DIR` — **no `key=` in it** (CARD-0365) |
| Method | GET |
| Body | (leave empty — all params are in the URL) |
| Headers | `Authorization: Bearer <DATA_PIPELINE_KEY>` — the key goes here, not in the URL, so it stays out of every access log (CARD-0365) |
| Basic auth | disabled |
| Discard offline locations | **off** — queues failed GETs and retries when connectivity returns |

Take `<DATA_PIPELINE_KEY>` from `credentials.local.md` (the data-pipeline-api section). A request with no valid key is rejected with `401` and, with "Discard offline locations" off, queues on the phone and retries.

**Constructed URL example:**
```
https://hikes.jctnet.com/data/gps?lat=32.2226&lon=-110.9747&ts=1749340800&acc=4.2&alt=728.3&direction=274.5
```

**GPSLogger placeholders:**

| Placeholder | Value |
|---|---|
| `%LAT` | Latitude (decimal degrees) |
| `%LON` | Longitude (decimal degrees) |
| `%TIME` | Unix epoch timestamp in **seconds** (integer) |
| `%ACC` | GPS accuracy in meters |
| `%ALT` | Altitude in meters above sea level |
| `%DIR` | GPS bearing/direction of travel, degrees clockwise from North (CARD-0085, added 2026-08-05) — optional; older requests without it still work, `doGet` writes an empty value rather than failing. **Corrected 2026-09-28 (CARD-0349) — this table previously said `%DIRECTION`, the wrong macro, found live:** the real GPSLogger app substitutes `%DIR`; a URL using `%DIRECTION` gets only its leading `%DIR` replaced, leaving a literal `ECTION` suffix on the value (e.g. `0.0ECTION`). Never caused a visible failure here because `doGet`'s `parseFloat()` parses only the leading numeric prefix of a string and silently ignores the rest — direction values have likely been truncated (usually to `0.0`) since this field was added, not genuinely missing. Confirmed against `data-pipeline-api`'s own logs (CARD-0349 Phase 1's stricter Python parser rejected the same malformed value outright, which is what surfaced this). |

> `ts` reaches the gateway as an ISO 8601 UTC string in practice (observed in production,
> 2026-09-29: `ts=2026-09-29T19%3A55%3A15.211Z`); the gateway also accepts epoch seconds or
> milliseconds, and stores a `timestamptz`.

### Test Before Walking

With GPSLogger running, tap the play button and step outside briefly. A new row should appear in
`gps_track` within 30–60 seconds — check with
`curl -s -H "Authorization: Bearer $KEY" "https://hikes.jctnet.com/data/export?table=gps_track&start=<recent ISO time>"`,
or ask Claude to look. If not, check the GPSLogger log (swipe the bottom bar up) for HTTP errors:
`401` means the Headers field is wrong or missing; and on the gateway host,
`docker logs data-pipeline-api | grep legacy` showing a `/gps` line means the key is still in the URL.

---

## Section 2 — Google Apps Script GPS Endpoint (RETIRED)

> **Retired by CARD-0349** — replaced by `data-pipeline-api`'s `GET /gps`. Kept as history.

The existing Apps Script (`Code.gs` in the "JCTsh Environmental Data" workbook) has only `doPost(e)`.
Add the `doGet(e)` function below it. The `doPost` function is unchanged.

### Script Source

The complete, deployable source is in `core/data-pipeline/environmental-data.gs`.
Paste the entire contents of that file into the Apps Script editor — it contains both
`doPost(e)` (environmental sensor data, Step 10) and `doGet(e)` (`action=gps` and
`action=lookup`, Step 19).

### Redeploy After Editing

After pasting the code:

1. **Extensions → Apps Script** (if not already open)
2. Click **Deploy → Manage deployments**
3. Click the **pencil icon** on the existing `JCTsh Environmental Data v1` deployment
4. Change **Version** to **New version**
5. Click **Save**

The deployment URL does not change. All existing Node-RED flows continue to work.

### Test the GPS Endpoint

From PowerShell (replace `<SCRIPT_ID>` and `<KEY>` from `credentials.local.md`):

```powershell
Invoke-RestMethod -Uri "https://script.google.com/macros/s/<SCRIPT_ID>/exec?key=<KEY>&action=gps&lat=32.2226&lon=-110.9747&ts=1749340800&acc=4.2&alt=728.3"
```

Expected response: `{"status":"ok"}`

Confirm a new row appeared in the "GPS Track" sheet before configuring GPSLogger.

---

## Section 3 — GPS Track Sheet Setup (RETIRED)

> **Retired by CARD-0349** — the data lives in the `gps_track` table (`core/data-pipeline/init/schema.sql`). Kept as history.

### Add the Sheet

1. Open the [JCTsh Environmental Data spreadsheet](https://docs.google.com/spreadsheets/d/1zBzeLocOp4VNW99Neh6JKOW8WHQ1evW2-5HYKJP70_g/edit)
2. Click **+** (add sheet) at the bottom
3. Rename it to exactly: `GPS Track`

### Column Headers

Add these headers in row 1 (A1 through F1):

| Col | Header | Content |
|---|---|---|
| A | `timestamp` | ISO8601 UTC (e.g. `2026-06-12T19:00:00.000Z`) |
| B | `lat` | Decimal degrees (e.g. `32.2226`) |
| C | `lon` | Decimal degrees (e.g. `-110.9747`) |
| D | `accuracy_m` | GPS accuracy in meters (e.g. `4.2`) |
| E | `altitude_m` | Altitude in meters above sea level (e.g. `728.3`) |
| F | `direction` | GPS bearing in degrees, clockwise from North (CARD-0085, added 2026-08-05) — blank for rows logged before this column existed |

No formulas, no auto-formatting — plain data only. The Apps Script appends rows starting at row 2.

### Size Expectations

At 30-second intervals, a 10-hour hike produces ~1,200 rows (~75 KB). No pruning needed.

---

## Section 4 — Timestamp Lookup for Step 20 (RETIRED)

> **Retired by CARD-0349** — now `GET /lookup-gps` on the gateway (`core/data-pipeline/README.md`). Kept as history.

Step 20 adds `lat`/`lon` to the environmental data pipeline by looking up the nearest GPS
trackpoint for each sensor reading's timestamp.

**How the lookup works:**

- Node-RED calls: `GET <SCRIPT_URL>?key=<KEY>&action=lookup&ts=2026-06-15T14:32:00Z`
- The Apps Script scans all rows in "GPS Track" and finds the row whose `timestamp` is
  nearest to the requested `ts`
- If the nearest row is within ±5 minutes: returns `{"lat": 32.2226, "lon": -110.9747}`
- If no row within ±5 minutes (home mode readings, test readings): returns `{"lat": null, "lon": null}`

**Why ±5 minutes:** Sensor readings are every 2 minutes; GPS trackpoints are every 30 seconds.
In the worst case, sensor timestamps and GPS timestamps are perfectly interleaved at 2-minute
offsets — the nearest GPS point is always within 1 minute when hiking. The 5-minute window
also tolerates brief GPS signal loss (tunnels, heavy tree cover).

**Field-mode readings only get coordinates:** Readings taken at home (rssi_dbm ≠ 0) have a
current timestamp during upload, not a hike timestamp — the lookup will correctly return null
for them since no GPS track exists for home readings.

The `action=lookup` code is already included in Section 2's `doGet(e)` function above.
Step 20 wires it into Node-RED.

---

## Step 19 Completion Record

*(Filled in after Joseph confirms GPSLogger posting successfully)*

| Item | Value |
|---|---|
| GPSLogger app version | F-Droid install (Play Store listing removed) |
| Test walk duration | ~5 minutes (mailbox and back) |
| Trackpoints logged | 23 |
| Deployment redeployed (new version) | 2026-06-12 |
| Any settings differing from above | "Retry on failure" is labeled "Discard offline locations" (set to off); "Keep screen on" not present; "Start on bootup" off; "Start logging when app starts" on |
