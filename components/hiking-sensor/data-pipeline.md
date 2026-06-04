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
2. Add these exact column headers in row 1 (A1 through X1):

```
timestamp  source  lat  lon  temp_f  humidity_pct  pressure_hpa  dew_point_f
heat_index_f  uv_index  irradiance_wm2  wind_speed_mph  wind_dir_deg  rain_tips
rainin  dailyrainin  battery_v  rssi_dbm  pm1_ug_m3  pm25_ug_m3  pm4_ug_m3
pm10_ug_m3  voc_index  nox_index
```

Column mapping (A–X):

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
(future enhancement, see `JCTsh-Environmental-Data-Architecture.md`).

---

## Step 10 — Google Apps Script Web App

### Create the Script

1. In the Google Sheets workbook: **Extensions → Apps Script**
2. Delete any existing code in Code.gs
3. Paste the complete code below

### Apps Script Code

```javascript
function doPost(e) {
  try {
    // Authenticate via secret key in URL query parameter
    var expectedKey = PropertiesService.getScriptProperties().getProperty('API_KEY');
    if (!expectedKey || e.parameter.key !== expectedKey) {
      return ContentService
        .createTextOutput(JSON.stringify({status: 'error', message: 'unauthorized'}))
        .setMimeType(ContentService.MimeType.JSON);
    }

    var payload = JSON.parse(e.postData.contents);
    var ss = SpreadsheetApp.getActiveSpreadsheet();

    if (payload.component === 'hiking-observations') {
      // Route to Hiking Observations sheet
      var obsSheet = ss.getSheetByName('Hiking Observations');
      obsSheet.appendRow([
        payload.ts,
        payload.observation,
        JSON.stringify(payload.categories || []),
        payload.source || 'voice'
      ]);
    } else {
      // Route to Environmental Data sheet
      var envSheet = ss.getSheetByName('Environmental Data');
      var v = function(field) {
        var val = payload[field];
        return (val !== undefined && val !== null) ? val : '';
      };
      envSheet.appendRow([
        v('ts'),           // A  timestamp
        v('source'),       // B  source
        v('lat'),          // C  lat
        v('lon'),          // D  lon
        v('temp_f'),       // E  temp_f
        v('humidity_pct'), // F  humidity_pct
        v('pressure_hpa'), // G  pressure_hpa
        v('dew_point_f'),  // H  dew_point_f
        v('heat_index_f'), // I  heat_index_f
        v('uv_index'),     // J  uv_index
        v('irradiance_wm2'),  // K
        v('wind_speed_mph'),  // L
        v('wind_dir_deg'),    // M
        v('rain_tips'),       // N
        v('rainin'),          // O
        v('dailyrainin'),     // P
        v('battery_v'),       // Q
        v('rssi_dbm'),        // R
        v('pm1_ug_m3'),       // S
        v('pm25_ug_m3'),      // T
        v('pm4_ug_m3'),       // U
        v('pm10_ug_m3'),      // V
        v('voc_index'),       // W
        v('nox_index')        // X
      ]);
    }

    return ContentService
      .createTextOutput(JSON.stringify({status: 'ok'}))
      .setMimeType(ContentService.MimeType.JSON);

  } catch(err) {
    return ContentService
      .createTextOutput(JSON.stringify({status: 'error', message: err.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
```

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

---

## Step 11 — Node-RED Data Handler Flow

### Node-RED Environment Variables

Set these before importing the flow. In Node-RED: **hamburger menu → Settings → Environment Variables** (or edit `settings.js`):

| Variable | Value |
|---|---|
| `APPS_SCRIPT_URL` | The deployment URL from Step 10 |
| `APPS_SCRIPT_KEY` | The API key from Step 10 |

### Flow JSON

Import this flow via Node-RED UI → hamburger menu → **Import → Clipboard**:

```json
[
  {
    "id": "env-data-mqtt-in",
    "type": "mqtt in",
    "name": "jctsh/components/+/data",
    "topic": "jctsh/components/+/data",
    "qos": "0",
    "datatype": "auto",
    "broker": "",
    "wires": [["env-data-process"]]
  },
  {
    "id": "env-data-process",
    "type": "function",
    "name": "Compute derived fields + build POST",
    "func": "// Parse payload\nvar d = msg.payload;\nif (typeof d === 'string') {\n    try { d = JSON.parse(d); } catch(e) { node.warn('Bad JSON: ' + msg.payload); return null; }\n}\n\n// Add source field\nd.source = d.component;\n\n// Compute dew point and heat index if temp + humidity available\nif (d.temp_f != null && d.humidity_pct != null) {\n    var temp_c = (d.temp_f - 32) * 5 / 9;\n    var a = 17.27, b = 237.7;\n    var gamma = (a * temp_c / (b + temp_c)) + Math.log(d.humidity_pct / 100);\n    var dew_c = (b * gamma) / (a - gamma);\n    d.dew_point_f = Math.round((dew_c * 9/5 + 32) * 10) / 10;\n\n    var T = d.temp_f, H = d.humidity_pct;\n    if (T >= 80 && H >= 40) {\n        d.heat_index_f = Math.round((\n            -42.379 + 2.04901523*T + 10.14333127*H\n            - 0.22475541*T*H - 0.00683783*T*T - 0.05481717*H*H\n            + 0.00122874*T*T*H + 0.00085282*T*H*H\n            - 0.00000199*T*T*H*H\n        ) * 10) / 10;\n    } else {\n        d.heat_index_f = Math.round((T + H/5 - 10.3) * 10) / 10;\n    }\n}\n\n// Build HTTP POST\nmsg.url = env.get('APPS_SCRIPT_URL') + '?key=' + env.get('APPS_SCRIPT_KEY');\nmsg.method = 'POST';\nmsg.headers = {'Content-Type': 'application/json'};\nmsg.payload = d;\nmsg._component = d.component;\nreturn msg;",
    "wires": [["env-data-http-post"]]
  },
  {
    "id": "env-data-http-post",
    "type": "http request",
    "name": "POST to Apps Script",
    "method": "use",
    "ret": "txt",
    "paytoqs": "ignore",
    "url": "",
    "wires": [["env-data-check-response"]]
  },
  {
    "id": "env-data-check-response",
    "type": "function",
    "name": "Check response",
    "func": "var component = msg._component || 'unknown';\ntry {\n    var resp = JSON.parse(msg.payload);\n    if (resp.status === 'ok') {\n        msg.payload = JSON.stringify({\n            component: 'node-red',\n            category: 'System',\n            message: 'Sheets row appended for ' + component\n        });\n        return [msg, null];\n    } else {\n        msg.payload = JSON.stringify({\n            component: 'node-red',\n            category: 'Alert',\n            message: 'Sheets append failed for ' + component + ': ' + (resp.message || msg.payload)\n        });\n        return [null, msg];\n    }\n} catch(e) {\n    msg.payload = JSON.stringify({\n        component: 'node-red',\n        category: 'Alert',\n        message: 'Sheets response parse error for ' + component + ': ' + msg.payload\n    });\n    return [null, msg];\n}",
    "wires": [["env-data-log-success"], ["env-data-log-error"]]
  },
  {
    "id": "env-data-log-success",
    "type": "mqtt out",
    "name": "Log success",
    "topic": "jctsh/core/log-server/log",
    "qos": "0",
    "retain": "false",
    "broker": "",
    "wires": []
  },
  {
    "id": "env-data-log-error",
    "type": "mqtt out",
    "name": "Log error",
    "topic": "jctsh/core/log-server/log",
    "qos": "0",
    "retain": "false",
    "broker": "",
    "wires": []
  }
]
```

### After Import

1. Open the **MQTT In** node (`jctsh/components/+/data`) → select the existing JCTsh MQTT broker
2. Open both **MQTT Out** nodes → select the same broker
3. Click **Deploy**

### Verify the Flow

Trigger a test message manually in Node-RED (inject node or MQTT Explorer) or wait for the next hiking-monitor 2-minute data publish. Confirm:

- A new row appears in the Environmental Data sheet
- `dew_point_f` and `heat_index_f` columns are populated
- `source` column shows `hiking-monitor`
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

## Adding Future Environmental Sensors

No changes to this pipeline are needed when a new environmental sensor is added. The
`jctsh/components/+/data` wildcard catches it automatically. The `source` column in
Sheets identifies the device. Confirm the new sensor's payload conforms to the standard
in `JCTsh-Environmental-Data-Architecture.md` before first flash.
