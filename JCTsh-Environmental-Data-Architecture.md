# JCTsh Environmental Data Architecture
**Author:** Joseph C Thomas (JCT)
**Purpose:** Defines the architecture for JCTsh environmental sensor data — the standard message payload, Google Sheets archive design, Node-RED data handler pattern, Weather Underground integration, and the planned environmental sensor family. All environmental sensor components must conform to this standard.
**Version:** 1.0
**Version description:** Initial release. Established during weather station planning (May 2026). Covers payload schema, multi-source archive design, lat/lon as a first-class field, Node-RED wildcard handler pattern, WU integration, and the planned device family (weather station, porch sensor, hiking monitor, Pleasure-Way).
**Project:** JCTsh — Smart Home Automation
**Related files:** `README.md`, `CLAUDE.md`, `ENVIRONMENT.md`, `JCTsh-Build-Standards.md`, `JCTsh-Component-Planning-Pattern.md`

---

## Purpose and Scope

This document defines the data architecture for JCTsh environmental sensors — any sensor that measures physical conditions (temperature, humidity, pressure, wind, rain, UV, air quality, etc.) at a fixed or mobile location.

The weather station is the first component in this family. All subsequent environmental sensors (porch sensor, hiking monitor, Pleasure-Way node) must conform to the payload standard and data handler pattern defined here. This ensures a single Google Sheets archive captures all environmental data across all devices, and a single Node-RED data handler routes it correctly without per-device changes.

---

## Core Principles

**Lat/lon is a first-class field.** Every environmental data message carries `lat` and `lon` regardless of whether the device is fixed or mobile. Fixed sensors hardcode their coordinates in firmware. Mobile sensors source them from GPS hardware or a companion phone. This makes every record self-contained and spatiotemporally queryable without joining to a device registry.

**Node-RED owns external posting.** ESP32 devices publish to MQTT only. Node-RED handles all HTTP calls to Weather Underground, Google Sheets, and any other external service. This keeps ESP32 wake cycles fast, retry/error logic centralized, and battery life maximized.

**One archive, many sources.** The Google Sheets environmental archive receives data from all environmental sensors via a single Node-RED wildcard subscription. Adding a new sensor requires no changes to the archive schema or handler — the `component` field identifies the source in every row.

**Rain accumulation lives in Node-RED.** Raw tip counts from rain gauges are published by ESP32. Node-RED maintains the rolling 60-minute window and daily accumulator. This is more reliable than preserving state across deep sleep cycles in ESP32 RTC memory, and keeps Weather Underground calculations in an always-on process.

---

## Standard Environmental Message Payload

All environmental sensor components publish data to `jctsh/components/<name>/data` using this JSON structure. Fields that a given sensor does not measure are omitted — do not send null or zero for absent sensors.

```json
{
  "component": "weather-station",
  "ts": "2026-05-21T14:32:00Z",
  "lat": 32.2226,
  "lon": -110.9747,
  "temp_f": 98.4,
  "humidity_pct": 12.3,
  "pressure_hpa": 1005.2,
  "uv_index": 9.2,
  "irradiance_wm2": 887.0,
  "wind_speed_mph": 8.1,
  "wind_dir_deg": 225,
  "rain_tips": 3,
  "battery_v": 3.94,
  "rssi_dbm": -67
}
```

### Field Reference

| Field | Type | Unit | Required | Notes |
|---|---|---|---|---|
| `component` | string | — | ✅ Always | Matches the MQTT component name — used as `source` in Sheets |
| `ts` | string | ISO 8601 UTC | ✅ Always | From DS3231 RTC; NTP-synced on WiFi connect |
| `lat` | number | decimal degrees | ✅ Always | Fixed constant for fixed sensors; GPS for mobile |
| `lon` | number | decimal degrees | ✅ Always | Fixed constant for fixed sensors; GPS for mobile |
| `temp_f` | number | °F | if available | Primary temperature reading |
| `humidity_pct` | number | % RH | if available | Relative humidity |
| `pressure_hpa` | number | hPa | if available | Barometric pressure |
| `uv_index` | number | UVI | if available | Calculated from UVA + UVB (VEML6075) |
| `irradiance_wm2` | number | W/m² | if available | Solar irradiance (SI1145) |
| `wind_speed_mph` | number | mph | if available | Anemometer reading |
| `wind_dir_deg` | number | 0–359° | if available | Wind vane reading |
| `rain_tips` | integer | tips since last reading | if available | Raw tip count — Node-RED computes accumulations |
| `battery_v` | number | V | if battery-powered | LiPo voltage from ADC |
| `rssi_dbm` | integer | dBm | ✅ Always | WiFi signal strength — useful for deployment diagnostics |

### Derived Fields (computed by Node-RED, not sent by ESP32)

| Field | Computed from | Used for |
|---|---|---|
| `dew_point_f` | `temp_f` + `humidity_pct` | Sheets archive, HA entity |
| `heat_index_f` | `temp_f` + `humidity_pct` | Sheets archive, HA entity |
| `rainin` | rolling 60-min `rain_tips` sum | Weather Underground |
| `dailyrainin` | midnight-to-now `rain_tips` sum | Weather Underground |

---

## Google Sheets Archive

### Purpose

The Google Sheets environmental archive is the permanent, queryable record of all JCTsh environmental sensor data. It is the authoritative data store — Weather Underground is a display window, not an archive.

### Access

Node-RED posts to the archive via a Google Apps Script web app deployed as a REST endpoint. The endpoint accepts a JSON POST, appends one row, and returns a success status. Authentication is a secret key in the URL — no OAuth required.

The Apps Script web app URL and secret key are stored in Node-RED environment variables (not in source control).

### Schema

One sheet, one row per reading, all sources. The `source` column is populated from the `component` field in the MQTT payload.

| Column | Source | Notes |
|---|---|---|
| `timestamp` | `ts` from payload | ISO 8601 UTC |
| `source` | `component` from payload | e.g. `weather-station`, `porch-sensor` |
| `lat` | `lat` from payload | Decimal degrees |
| `lon` | `lon` from payload | Decimal degrees |
| `temp_f` | `temp_f` | °F |
| `humidity_pct` | `humidity_pct` | % RH |
| `pressure_hpa` | `pressure_hpa` | hPa |
| `dew_point_f` | computed by Node-RED | °F |
| `heat_index_f` | computed by Node-RED | °F |
| `uv_index` | `uv_index` | UVI |
| `irradiance_wm2` | `irradiance_wm2` | W/m² |
| `wind_speed_mph` | `wind_speed_mph` | mph |
| `wind_dir_deg` | `wind_dir_deg` | 0–359° |
| `rain_tips` | `rain_tips` | raw tip count |
| `rainin` | computed by Node-RED | inches, rolling 60 min |
| `dailyrainin` | computed by Node-RED | inches, midnight to now |
| `battery_v` | `battery_v` | V |
| `rssi_dbm` | `rssi_dbm` | dBm |

Columns for fields a given sensor does not provide are left blank for that row. Do not add per-device columns — all sources use the same schema.

### Analysis Capabilities

Because every row is self-contained (timestamp + source + location + readings), standard Sheets functionality covers:

- Filter by `source` to isolate one device
- Filter by date range for seasonal or storm analysis
- Chart any field over time
- Pivot to compare sources side-by-side (e.g. porch vs. weather station temperature delta)
- Import into Google Maps or GIS tools using `lat`/`lon` columns directly

---

## Node-RED Data Handler

### Subscription

The data handler subscribes to `jctsh/components/+/data` (wildcard). Any environmental sensor publishing on this pattern is automatically captured. No per-device Node-RED changes are needed when a new sensor is added.

### Handler Responsibilities

On each received data message the handler:

1. Parses the JSON payload
2. Computes derived fields (`dew_point_f`, `heat_index_f`, `rainin`, `dailyrainin`)
3. Posts to Google Sheets (appends one row)
4. Posts to Weather Underground (weather station only — filtered by `component === "weather-station"`)
5. Updates Home Assistant entities via REST API
6. Routes SmartThings-exposed values (temperature, rain active, lightning) via HA

### Rain Accumulation State

The handler maintains two in-memory accumulators per rain-gauge-equipped device:

- **Rolling 60-minute buffer** — timestamped list of tip events; sum tips within the last 60 minutes to compute `rainin`
- **Daily accumulator** — running total of tips since midnight (America/Phoenix timezone); reset at 00:00 each day

These are Node-RED flow context variables, persistent across redeploys via the Node-RED context store.

### Offline / Gap Handling

If the Node-RED handler cannot reach Google Sheets or Weather Underground (network issue, service outage), it logs the failure to `jctsh/core/log-server/log` and continues. SD card logging on the ESP32 provides a local backup for gap recovery. WU does not support backfill — gaps in WU data are permanent. Gaps in Google Sheets can be backfilled manually from SD card logs if needed.

---

## Weather Underground Integration

### Account

A free PWS (Personal Weather Station) account at wunderground.com. Upload is free for PWS owners. The Station ID and Station Key are stored in Node-RED environment variables (not in source control).

### Upload Format

Node-RED posts to the WU PWS upload URL:

```
https://weatherstation.wunderground.com/weatherstation/updateweatherstation.php
  ?ID=<STATION_ID>
  &PASSWORD=<STATION_KEY>
  &dateutc=<UTC_DATETIME>
  &tempf=<temp_f>
  &humidity=<humidity_pct>
  &baromin=<pressure_inhg>
  &windspeedmph=<wind_speed_mph>
  &winddir=<wind_dir_deg>
  &rainin=<rainin>
  &dailyrainin=<dailyrainin>
  &UV=<uv_index>
  &solarradiation=<irradiance_wm2>
  &action=updateraw
```

Note: WU expects pressure in inHg (`baromin`), not hPa. Node-RED converts: `inHg = hPa / 33.8639`.

### Upload Interval

Matches the ESP32 wake cycle — one upload per data message received (approximately every 5 minutes). WU accepts updates as fast as every 2.5 seconds; 5 minutes is well within acceptable frequency.

---

## MQTT Lightning Topic

The AS3935 lightning detector publishes strike events on a separate topic to allow independent handling (SmartThings alert, Sheets log entry) without mixing strike events into the regular data stream.

```
topic:   jctsh/components/weather-station/lightning
payload: { "component": "weather-station", "distance_km": 12, "energy": 847 }
```

Node-RED subscribes separately to this topic and:
- Fires a momentary ON to the `switch.weather_station_lightning` virtual switch in HA → SmartThings
- Appends a row to a separate `Lightning Events` sheet in the same Google Sheets workbook

---

## Planned Environmental Sensor Family

| Device | Type | Location | GPS source | Status |
|---|---|---|---|---|
| Weather station | Fixed | Backyard, Tucson | Hardcoded constants | In planning |
| Porch sensor | Fixed | Front porch, Tucson | Hardcoded constants | Planned — next after weather station |
| Hiking monitor | Mobile | Variable | Pixel 10 Pro XL via hotspot + MQTT location injection | Planned — deferred |
| Pleasure-Way sensor node | Mobile (RV) | 2018 Ram ProMaster / Pleasure-Way Lexor FL | Dedicated GPS module (NEO-6M or similar) on ESP32 | Planned — deferred |

### Mobile Sensor GPS Pattern

**Hiking monitor:** The ESP32 connects via Pixel 10 Pro XL hotspot. A companion Android app (or Tasker + MQTT plugin) publishes the phone's GPS coordinates to a companion location topic or injects them directly into the sensor payload before forwarding. The exact mechanism is deferred to the hiking monitor planning session.

**Pleasure-Way:** A NEO-6M GPS module on the ESP32 provides coordinates directly. The vehicle's Firefly control network is a separate subsystem (see planned RV component) — the environmental sensor node is independent of Firefly.

### Porch Sensor

The front porch sensor is the next planned environmental component. It will use the same ESPHome + MQTT + Node-RED pattern as the weather station with a reduced sensor set (BME280 only — temp, humidity, pressure). It will publish on `jctsh/components/porch-sensor/data` with hardcoded Tucson front-porch coordinates. Node-RED wildcard subscription catches it automatically with no handler changes.

---

## Document Update Policy

Update this document when:
- A new environmental sensor is added to the family (update the planned device table)
- The payload schema is extended (add new fields to the field reference)
- The Google Sheets schema is extended (add new columns)
- The Node-RED handler logic changes materially
- A new external data destination is added

Do not update this document for component-specific implementation details — those belong in `components/<name>/README.md`.
