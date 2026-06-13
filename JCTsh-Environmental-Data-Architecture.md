# JCTsh Environmental Data Architecture
**Author:** Joseph C Thomas (JCT)
**Purpose:** Defines the architecture for JCTsh environmental sensor data — the standard message payload, Google Sheets archive design, Node-RED data handler pattern, Weather Underground integration, and the planned environmental sensor family. All environmental sensor components must conform to this standard.
**Version:** 1.3
**Version description:** Added hiking observations pipeline architecture — keyword-triggered voice observation capture via Google Recorder, Apps Script processor, separate Observations sheet, and MQTT integration. Observations payload schema defined. Category taxonomy defined. Path A (manual share) and Path B (Tasker automation) implementation paths documented. No other changes from v1.2.
**Project:** JCTsh — Smart Home Automation
**Related files:** `README.md`, `CLAUDE.md`, `ENVIRONMENT.md`, `JCTsh-Build-Standards.md`, `JCTsh-Component-Planning-Pattern.md`

---

## Purpose and Scope

This document defines the data architecture for JCTsh environmental sensors — any sensor that measures physical conditions (temperature, humidity, pressure, wind, rain, UV, air quality, etc.) at a fixed or mobile location.

The weather station is the first component in this family. All subsequent environmental sensors (porch sensor, hiking monitor, Pleasure-Way node) must conform to the payload standard and data handler pattern defined here. This ensures a single Google Sheets archive captures all environmental data across all devices, and a single Node-RED data handler routes it correctly without per-device changes.

---

## Core Principles

**Lat/lon is a first-class field.** Every environmental data message carries `lat` and `lon` regardless of whether the device is fixed or mobile. Fixed sensors hardcode their coordinates in firmware. Mobile sensors with GPS hardware source them from the GPS module. Mobile devices without GPS hardware send JSON `null` for both fields — this is the correct value, not zero (0,0 is a real location in the Gulf of Guinea). Timestamp correlation with an external GPS track (e.g. GaiaGPS) is used instead. This makes every record self-contained and the null signals clearly that no GPS data is available for that reading.

**Node-RED owns external posting.** ESP32 devices publish to MQTT only. Node-RED handles all HTTP calls to Weather Underground, Google Sheets, and any other external service. This keeps ESP32 wake cycles fast, retry/error logic centralized, and battery life maximized.

**One archive, many sources.** The Google Sheets environmental archive receives data from all environmental sensors via a single Node-RED wildcard subscription. Adding a new sensor requires no changes to the archive schema or handler — the `component` field identifies the source in every row.

**Rain accumulation lives in Node-RED.** Raw tip counts from rain gauges are published by ESP32. Node-RED maintains the rolling 60-minute window and daily accumulator. This is more reliable than preserving state across deep sleep cycles in ESP32 RTC memory, and keeps Weather Underground calculations in an always-on process.

**Observations are a separate stream.** Free-text voice observations from hikes are architecturally distinct from numeric sensor readings — different payload, different schema, different Sheets tab. They are correlated to the sensor data stream and GaiaGPS track by timestamp, not by being mixed into the same rows.

---

## Standard Environmental Message Payload

All environmental sensor components publish data to `jctsh/components/<name>/data` using this JSON structure. Fields that a given sensor does not measure are omitted — do not send null or zero for absent sensors. Exception: `lat` and `lon` must always be present — send JSON `null` if no GPS hardware is available.

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
| `ts` | string | ISO 8601 UTC | ✅ Always | From DS3231 RTC or NTP-synced system clock |
| `lat` | number or null | decimal degrees | ✅ Always | Fixed constant for fixed sensors; GPS value for mobile sensors with GPS hardware; JSON `null` for mobile sensors without GPS (e.g. hiking monitor) |
| `lon` | number or null | decimal degrees | ✅ Always | Same as `lat` — never omit, never send 0 |
| `temp_f` | number | °F | if available | Primary temperature reading |
| `humidity_pct` | number | % RH | if available | Relative humidity |
| `pressure_hpa` | number | hPa | if available | Barometric pressure |
| `uv_index` | number | UVI | if available | UV index — LTR-390 sensor (UVA + UV Index); filter `lat IS NOT NULL` in Sheets when doing location-based analysis |
| `irradiance_wm2` | number | W/m² | if available | Solar irradiance (SI1145) |
| `wind_speed_mph` | number | mph | if available | Anemometer reading |
| `wind_dir_deg` | number | 0–359° | if available | Wind vane reading |
| `rain_tips` | integer | tips since last reading | if available | Raw tip count — Node-RED computes accumulations |
| `battery_v` | number | V | if battery-powered | LiPo voltage from ADC |
| `rssi_dbm` | integer | dBm | ✅ Always | WiFi signal strength — useful for deployment diagnostics |
| `pm1_ug_m3` | number | µg/m³ | if available | PM1.0 particulate matter — air quality monitor (SEN55) |
| `pm25_ug_m3` | number | µg/m³ | if available | PM2.5 particulate matter — air quality monitor (SEN55); primary AQI metric |
| `pm4_ug_m3` | number | µg/m³ | if available | PM4.0 particulate matter — air quality monitor (SEN55) |
| `pm10_ug_m3` | number | µg/m³ | if available | PM10 particulate matter — air quality monitor (SEN55) |
| `voc_index` | number | VOC index (1–500) | if available | VOC index — air quality monitor (SEN55); 100 = typical clean air |
| `nox_index` | number | NOx index (1–500) | if available | NOx index — air quality monitor (SEN55); 1 = typical clean air |

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

### Sheets Structure

The workbook contains multiple sheets:

| Sheet | Contents |
|---|---|
| `Environmental Data` | One row per sensor reading — all environmental sensor sources |
| `Hiking Observations` | One row per voice observation — see Hiking Observations Architecture section |
| `Lightning Events` | One row per lightning strike event from weather station AS3935 detector |

### Environmental Data Schema

One sheet, one row per reading, all sources. The `source` column is populated from the `component` field in the MQTT payload.

| Column | Source | Notes |
|---|---|---|
| `timestamp` | `ts` from payload | ISO 8601 UTC |
| `source` | `component` from payload | e.g. `weather-station`, `porch-sensor`, `hiking-monitor`, `air-quality-monitor` |
| `lat` | `lat` from payload | Decimal degrees, or null for devices without GPS |
| `lon` | `lon` from payload | Decimal degrees, or null for devices without GPS |
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
| `pm1_ug_m3` | `pm1_ug_m3` | µg/m³ — blank for non-AQ devices |
| `pm25_ug_m3` | `pm25_ug_m3` | µg/m³ — blank for non-AQ devices |
| `pm4_ug_m3` | `pm4_ug_m3` | µg/m³ — blank for non-AQ devices |
| `pm10_ug_m3` | `pm10_ug_m3` | µg/m³ — blank for non-AQ devices |
| `voc_index` | `voc_index` | VOC index — blank for non-AQ devices |
| `nox_index` | `nox_index` | NOx index — blank for non-AQ devices |

Columns for fields a given sensor does not provide are left blank for that row. Do not add per-device columns — all sources use the same schema.

### Analysis Capabilities

Because every row is self-contained (timestamp + source + location + readings), standard Sheets functionality covers:

- Filter by `source` to isolate one device
- Filter by date range for seasonal or storm analysis
- Chart any field over time
- Pivot to compare sources side-by-side (e.g. porch vs. weather station temperature delta)
- Import into Google Maps or GIS tools using `lat`/`lon` columns directly — filter `lat IS NOT NULL` to exclude devices without GPS
- Join hiking monitor rows to GaiaGPS track by matching `timestamp` to GPX trackpoint timestamps
- Correlate air quality monitor PM2.5 with hiking monitor UV index and pressure to characterize hike conditions fully
- Join Environmental Data rows to Hiking Observations rows by matching `timestamp` — nearest sensor reading to any observation reveals conditions at the moment of observation

---

## Node-RED Data Handler

### Subscription

The data handler subscribes to `jctsh/components/+/data` (wildcard). Any environmental sensor publishing on this pattern is automatically captured. No per-device Node-RED changes are needed when a new sensor is added.

### Handler Responsibilities

On each received data message the handler:

1. Parses the JSON payload
2. Checks `component` field — routes `hiking-observations` to Observations sheet; all others to Environmental Data sheet
3. Computes derived fields (`dew_point_f`, `heat_index_f`, `rainin`, `dailyrainin`) for environmental readings
4. Posts to Google Sheets (appends one row to the appropriate sheet)
5. Posts to Weather Underground (weather station only — filtered by `component === "weather-station"`)
6. Updates Home Assistant entities via REST API
7. Routes SmartThings-exposed values (temperature, rain active, lightning) via HA

### Rain Accumulation State

The handler maintains two in-memory accumulators per rain-gauge-equipped device:

- **Rolling 60-minute buffer** — timestamped list of tip events; sum tips within the last 60 minutes to compute `rainin`
- **Daily accumulator** — running total of tips since midnight (America/Phoenix timezone); reset at 00:00 each day

These are Node-RED flow context variables, persistent across redeploys via the Node-RED context store.

### Offline / Gap Handling

If the Node-RED handler cannot reach Google Sheets or Weather Underground (network issue, service outage), it logs the failure to `jctsh/core/log-server/log` and continues. SD card logging on the ESP32 provides a local backup for gap recovery. WU does not support backfill — gaps in WU data are permanent. Gaps in Google Sheets can be backfilled manually from SD card logs if needed.

---

## Hiking Observations Architecture

### Overview

Voice observations recorded during hikes using Google Recorder on the Pixel 10 Pro XL. Observations beginning with the keyword "observation" are automatically identified, transcribed, classified by category, and archived in the Hiking Observations sheet. Correlated to environmental sensor data and GaiaGPS track by timestamp.

No ESP32 or dedicated hardware required. Entirely a phone + Google Apps Script + Sheets pipeline.

### Observation Payload

Observations publish to `jctsh/components/hiking-observations/data` using this structure:

```json
{
  "component": "hiking-observations",
  "ts": "2026-05-27T09:14:33Z",
  "lat": null,
  "lon": null,
  "observation": "saw first saguaro bloom of the season, about halfway up the north slope",
  "categories": ["vegetation"],
  "source": "voice"
}
```

| Field | Notes |
|---|---|
| `component` | Always `hiking-observations` |
| `ts` | Timestamp of the recording — not the time of processing or publishing |
| `lat`, `lon` | Always null — timestamp correlation to GaiaGPS track used for position |
| `observation` | Full transcript text with keyword prefix stripped |
| `categories` | Array of matched categories — computed by Apps Script keyword scan, not entered manually |
| `source` | Always `voice` for Google Recorder; reserved for future observation types |

### Keyword Trigger

All observations must begin with the word **"observation"** (case-insensitive). The Apps Script processor checks this before processing. Recordings that do not begin with this keyword are ignored entirely — casual recordings, reminders, and other voice memos are never processed.

Examples of valid observation openings:
- "Observation: saw first saguaro bloom today"
- "Observation, large hawk circling above the ridge"
- "observation feels significantly more humid than last week at this point"

### Category Taxonomy

Categories are assigned automatically by keyword scan of the observation text. Multiple categories may apply. Categories are stored as a JSON array in the `categories` column.

| Category | Example keywords |
|---|---|
| `vegetation` | saguaro, bloom, cactus, tree, shrub, flower, plant, grass, palo verde, ocotillo |
| `wildlife` | bird, hawk, coyote, snake, rabbit, deer, javelina, lizard, butterfly, insect |
| `weather` | cloud, rain, wind, storm, thunder, lightning, temperature, hot, cold, warm, cool |
| `visibility` | clear, hazy, smoke, dust, fog, smoggy, murky |
| `sky` | moon, sun, stars, sunrise, sunset, rainbow, shadow |
| `air_quality` | smoky, dusty, smell, odor, particulate, ash |
| `trail` | trail, path, wash, ridge, peak, summit, canyon, rock, boulder, erosion |
| `subjective` | feels, seems, appears, noticed, unusual, different, surprising |

The taxonomy is extensible — add keywords and categories in the Apps Script processor as needed. No schema changes required to add a new category.

### Hiking Observations Sheet Schema

Separate sheet in the same Google Sheets workbook as Environmental Data.

| Column | Source | Notes |
|---|---|---|
| `timestamp` | `ts` from payload | ISO 8601 UTC — join key to Environmental Data and GaiaGPS track |
| `observation` | `observation` from payload | Full transcript text, keyword prefix stripped |
| `categories` | `categories` from payload | JSON array as string, e.g. `["vegetation","wildlife"]` |
| `source` | `source` from payload | `voice` for Google Recorder |

### Timestamp Correlation

The `timestamp` column is the join key across all three data streams:

- **Environmental Data sheet:** `=VLOOKUP(A2, 'Environmental Data'!A:B, 2, TRUE)` finds the nearest sensor reading to the observation timestamp
- **GaiaGPS track:** GPX trackpoint timestamps correlated manually or via export tool
- All three streams together give: where you were + what conditions were + what you observed

### Implementation Paths

**Path A — Manual share to Google Docs (starting point)**

1. Make observation recordings on the trail beginning with "observation"
2. After the hike, in Google Recorder, share each relevant transcript to Google Docs (one tap per recording)
3. Shared Docs land in a designated Drive folder (`JCTsh Hiking Observations`)
4. Google Apps Script runs on a schedule (every 15 minutes or triggered by new file in folder)
5. Script checks each new Doc for keyword prefix, extracts text, strips prefix, captures creation timestamp, assigns categories, appends row to Hiking Observations sheet, publishes to MQTT
6. Node-RED wildcard handler receives and logs

Path A is the correct starting point — reliable, no Tasker dependency, no undocumented API access. The manual share step is a deliberate review moment before observations enter the permanent record.

**Path B — Tasker automation on WiFi reconnect (future enhancement)**

1. Make observation recordings on the trail — no manual action needed
2. Tasker profile fires when phone reconnects to JCTnet1 WiFi after a hike
3. Tasker scans Google Recorder transcripts via Android content provider
4. Filters new recordings since last sync time beginning with "observation"
5. Publishes transcript text and recording timestamp directly to MQTT
6. Same downstream processing as Path A — Node-RED routes to Apps Script → Sheets

Path B eliminates the manual share step entirely. It depends on Tasker's ability to access Google Recorder's content provider on the Pixel 10 Pro — this requires testing before committing. Build Path A first; upgrade to Path B once Path A is proven.

### Apps Script Processor Responsibilities

The Apps Script processor (separate from the Sheets archive endpoint) handles observation processing:

1. Triggered by new file in `JCTsh Hiking Observations` Drive folder (Path A) or by MQTT message (Path B)
2. Reads transcript text
3. Checks for "observation" keyword prefix — ignores if absent
4. Strips keyword prefix from observation text
5. Captures creation timestamp from file metadata (Path A) or MQTT payload (Path B)
6. Scans text against category taxonomy — assigns all matching categories
7. Builds JSON payload
8. Appends row to Hiking Observations sheet
9. Publishes to `jctsh/components/hiking-observations/data` via MQTT (Path A only — Path B publishes before Apps Script)

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
| Hiking monitor | Mobile | Variable | None — `lat`/`lon` sent as null; timestamp correlation with GaiaGPS track used instead | Phase 1 complete — parts ordered — ready for Phase 2 |
| Hiking health monitor | Mobile (wrist) | Variable | None — companion to hiking monitor | Planned — deferred; see note below |
| Air quality monitor | Mobile (carried on hike) | Variable | None — `lat`/`lon` sent as null; timestamp correlation with GaiaGPS track | Planned — deferred; see note below |
| Hiking observations | Phone-based | Variable | None — `lat`/`lon` sent as null; timestamp correlation with GaiaGPS track | Planned — deferred; see Hiking Observations Architecture section |
| Pleasure-Way sensor node | Mobile (RV) | 2018 Ram ProMaster / Pleasure-Way Lexor FL | Dedicated GPS module (NEO-6M or similar) on ESP32 | Planned — deferred |

### Hiking Monitor — GPS Approach

The hiking monitor carries no GPS hardware. During Phase 1 planning the originally proposed approach (real-time GPS injection via Pixel 10 Pro XL hotspot) was replaced with timestamp correlation: the device logs sensor readings with NTP-synced timestamps; GaiaGPS on the Pixel 10 Pro XL logs the GPS track independently; the two datasets are correlated by matching timestamps after the hike. `lat` and `lon` are sent as JSON `null` in all hiking monitor payloads. The phone hotspot is not needed during the hike.

See `components/hiking-monitor/` for full Phase 1 planning document.

### Hiking Health Monitor — LilyGO T-WATCH-S3 Plus

Identified during hiking monitor Phase 1 planning (May 2026) as a natural companion device for health sensing. Health metrics (heart rate, SpO2, skin temperature, step counting/activity) require reliable wrist skin contact, which conflicts with the hiking monitor's clip-on environmental sensor form factor. A dedicated wrist-worn device is the correct solution.

**Planned platform:** LilyGO T-WATCH-S3 Plus (~$60)
- ESP32-S3 — same ecosystem as all JCTsh components
- MAX30102 heart rate and SpO2 sensor — integrated, wrist-mounted
- MPU9250 9-axis IMU — accelerometer, gyroscope, magnetometer
- Wi-Fi and Bluetooth 5.0
- 600mAh LiPo with charging controller
- AMOLED display
- Programmable via Arduino IDE / ESP-IDF

**Planned integration:** Publishes health readings to `jctsh/components/hiking-health/data` on home WiFi reconnect using the standard environmental payload pattern. Health-specific fields (`heart_rate_bpm`, `spo2_pct`, `steps`, `skin_temp_f`) to be added to this document's schema when the project begins. Google Sheets archive receives both environmental and health data streams, joinable by timestamp.

**Status:** Identified and deferred May 2026. Plan as a separate JCTsh component project using the standard planning pattern when ready. No parts ordered.

### Air Quality Monitor — Standalone Hiking Companion

Identified during hiking monitor Phase 1 planning (May 2026) as a natural companion device for particulate matter and VOC/NOx sensing. Air quality sensing was explicitly excluded from the hiking monitor to avoid enclosure size increase, battery life reduction, and airflow port complexity. A separate device carried on-pack or clipped to a strap is the correct solution.

**Recommended platform:** ESP32 (on hand) + Sensirion SEN55
- PM1.0, PM2.5, PM4.0, PM10, VOC index, NOx index — all in one I2C module (43×43×23mm)
- Native ESPHome `sen5x` platform support
- Same onboard flash logging and WiFi replay pattern as the hiking monitor
- Battery sized for higher draw — 2000–3000mAh LiPo or 18650 from inventory
- Duty-cycle the SEN55 fan via GPIO transistor to reduce average draw

**Status:** Identified and deferred May 2026. Build the hiking monitor first. Plan as a separate JCTsh component project when ready. No parts ordered.

### Pleasure-Way Sensor Node

A NEO-6M GPS module on the ESP32 provides coordinates directly. The vehicle's Firefly control network is a separate subsystem (see planned RV component) — the environmental sensor node is independent of Firefly.

### Porch Sensor

The front porch sensor is the next planned environmental component after the weather station. It will use the same ESPHome + MQTT + Node-RED pattern as the weather station with a reduced sensor set (BME280 only — temp, humidity, pressure). It will publish on `jctsh/components/porch-sensor/data` with hardcoded Tucson front-porch coordinates. Node-RED wildcard subscription catches it automatically with no handler changes.

---

## Document Update Policy

Update this document when:
- A new environmental sensor is added to the family (update the planned device table)
- The payload schema is extended (add new fields to the field reference)
- The Google Sheets schema is extended (add new columns)
- The Node-RED handler logic changes materially
- A new external data destination is added
- The hiking observations category taxonomy is extended

Do not update this document for component-specific implementation details — those belong in `components/<name>/README.md`.