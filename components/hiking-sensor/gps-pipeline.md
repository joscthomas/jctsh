# Hiking Monitor — GPS Track Pipeline (Steps 19–20)

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
| URL | `https://script.google.com/macros/s/<SCRIPT_ID>/exec?key=<API_KEY>&action=gps&lat=%LAT&lon=%LON&ts=%TIME&acc=%ACC&alt=%ALT` |
| Method | GET |
| Body | (leave empty — all params are in the URL) |
| Headers | (leave empty) |
| Basic auth | disabled |
| Discard offline locations | **off** — queues failed GETs and retries when connectivity returns |

Replace `<SCRIPT_ID>` and `<API_KEY>` with values from `credentials.local.md`.

**Constructed URL example:**
```
https://script.google.com/macros/s/<SCRIPT_ID>/exec?key=<API_KEY>&action=gps&lat=32.2226&lon=-110.9747&ts=1749340800&acc=4.2&alt=728.3
```

**GPSLogger placeholders:**

| Placeholder | Value |
|---|---|
| `%LAT` | Latitude (decimal degrees) |
| `%LON` | Longitude (decimal degrees) |
| `%TIME` | Unix epoch timestamp in **seconds** (integer) |
| `%ACC` | GPS accuracy in meters |
| `%ALT` | Altitude in meters above sea level |

> `%TIME` is a Unix epoch integer (e.g. `1749340800`). The Apps Script converts it to ISO8601
> UTC before writing to the sheet.

### Test Before Walking

With GPSLogger running, tap the play button and step outside briefly. Check the "GPS Track" sheet
(see Section 3) — a row should appear within 30–60 seconds. If not, check the GPSLogger log
(swipe the bottom bar up) for HTTP errors.

---

## Section 2 — Google Apps Script GPS Endpoint

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

## Section 3 — GPS Track Sheet Setup

### Add the Sheet

1. Open the [JCTsh Environmental Data spreadsheet](https://docs.google.com/spreadsheets/d/1aEgW3NDlu43uUM4Wtx1Hq3LjKm6hz2Lpc82LQZRO8L8/edit)
2. Click **+** (add sheet) at the bottom
3. Rename it to exactly: `GPS Track`

### Column Headers

Add these headers in row 1 (A1 through E1):

| Col | Header | Content |
|---|---|---|
| A | `timestamp` | ISO8601 UTC (e.g. `2026-06-12T19:00:00.000Z`) |
| B | `lat` | Decimal degrees (e.g. `32.2226`) |
| C | `lon` | Decimal degrees (e.g. `-110.9747`) |
| D | `accuracy_m` | GPS accuracy in meters (e.g. `4.2`) |
| E | `altitude_m` | Altitude in meters above sea level (e.g. `728.3`) |

No formulas, no auto-formatting — plain data only. The Apps Script appends rows starting at row 2.

### Size Expectations

At 30-second intervals, a 10-hour hike produces ~1,200 rows (~75 KB). No pruning needed.

---

## Section 4 — Timestamp Lookup for Step 20

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
