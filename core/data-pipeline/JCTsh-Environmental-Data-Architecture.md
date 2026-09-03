# JCTsh Environmental Data Architecture
**Author:** Joseph C Thomas (JCT)
**Purpose:** Defines the architecture for JCTsh environmental sensor data — the standard message payload, Google Sheets archive design, Node-RED data handler pattern, Weather Underground integration, and the planned environmental sensor family. All environmental sensor components must conform to this standard.
**Version:** 1.5
**Version description:** Added the `Hike Start Forecast` sheet and its Apps Script capture logic (CARD-0083) — a live weather-forecast snapshot captured on the first Hiking Observation of each day. New sheet in the Sheets Structure table and a new "Hike Start Forecast Architecture" section. No changes to the standard environmental payload schema from v1.4.
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
| `illuminance_lx` | number | lux | if available | Ambient light level — BH1750 sensor |
| `solar_v` | number | V | if solar-powered | Solar panel voltage from ADC voltage divider — combined with `battery_v`, distinguishes charging (solar_v > battery_v + ~0.3V) from draining |

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
| `Hike Start Forecast` | One row per day a hike started — a live weather-forecast snapshot captured at that moment; see Hike Start Forecast Architecture section |

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
| `illuminance_lx` | `illuminance_lx` | lux — blank for sensors without BH1750 |
| `solar_v` | `solar_v` | V — blank for non-solar devices |

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
| `source` | Always `voice` (Tasker's on-device "Get Voice" transcription); reserved for future observation types |

### Keyword Trigger

No keyword prefix required. The Tasker widget tap is the intent signal — whatever is spoken after tapping the widget is recorded as an observation. The Apps Script stores the full transcript as-is.

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

### Implementation (as actually built, CARD-0156 — corrected 2026-09-02, CARD-0225)

The two-path Google Recorder/Drive-folder design below was the original plan; it was never built. What actually shipped is simpler and has no MQTT step at all:

1. Tap the "Log Observation" widget on the Pixel — Tasker's **Get Voice** action transcribes on-device, no manual share step, no Drive folder, no keyword prefix required (the widget tap itself is the intent signal).
2. The transcript is written to a small on-device queue file (resilient to connectivity gaps, CARD-0156) and flushed via a direct **HTTP POST** to the Apps Script endpoint (`doPost`, `component: "hiking-observations"`) — as soon as the phone is online, no polling, no scheduled trigger.
3. `doPost` itself does the keyword-taxonomy category scan, builds the row, and appends directly to the Hiking Observations sheet — there is no separate "Apps Script processor" triggered by a Drive file or an MQTT message; it's one function, one write.
4. Google Apps Script has no MQTT client capability at all (`UrlFetchApp` only, no raw sockets) — this pipeline is direct HTTP end to end, matching GPS Track's own shape. See `CLAUDE.md`'s "MQTT vs. Direct HTTP" section for why that's the correct shape, not a gap.

Full build detail — every real-device quirk, the offline-queue design, the two auto-flush triggers — is `components/hiking-monitor/observations-pipeline.md`, the authoritative current-state reference. (The original "Path A: manual Drive-folder share" / "Path B: Tasker → MQTT" two-phase plan this section used to describe was superseded before either was built — CARD-0156 built the direct-HTTP design above instead.)

---

## Hike Start Forecast Architecture

### Overview

A live snapshot of what the weather forecast *was* at the moment a hike began — captured once, server-side, then frozen. Distinct from a forecast re-checked whenever a Hike-izer summary happens to be generated later, and distinct from actual historical/observed conditions (a separate, still-undecided item — see CARD-0074). Added for CARD-0083.

### Trigger

Captured by the same Apps Script `doPost` handler that already processes every Hiking Observation (see Hiking Observations Architecture above) — no new mobile automation, no new Tasker/Node-RED work. On each incoming observation, the handler computes the Arizona-local calendar date and checks whether a forecast has already been captured for that date. If not, and if the observation resolved a GPS position via the existing `_gpsLookup` correlation, it fetches and stores a forecast. If GPS hasn't resolved yet for this particular observation, capture is skipped for it (not defaulted to a home-area location) — a later observation the same day with a resolved position will retry.

This makes the *first* Hiking Observation of a hike the de facto trigger in practice, though the actual condition checked is "not yet captured today with a resolved GPS position," not literally "observation #1."

### Provider

[Open-Meteo](https://open-meteo.com) (`api.open-meteo.com`) — free, no API key or account required. Its hourly forecast endpoint returns temperature, relative humidity, precipitation probability, wind speed, and UV index in a single call, covering the full content scope Hike-izer needs without a second provider or any credential management.

Open-Meteo has no named "nearest station" concept, unlike NWS/METAR-based sources which snap to an airport or gridpoint office — it's a gridded numerical model interpolated to the exact coordinate requested. The response's own `latitude`/`longitude` fields report the actual grid point used (can differ slightly from the input due to grid resolution); these are what's stored, not the input coordinates, so the record shows precisely what point the forecast was for.

### Hike Start Forecast Sheet Schema

Separate sheet in the same Google Sheets workbook as Environmental Data. Self-provisioning — the Apps Script creates the sheet with this header row on first use if it doesn't already exist, so no manual Sheets setup step is required.

| Column | Source | Notes |
|---|---|---|
| `timestamp` | Triggering observation's `ts` | ISO 8601 UTC — join key for `action=export` date-range filtering, same as the other sheets |
| `date_az` | Derived from `timestamp` | Column header name is legacy (pre-CARD-0097) — value is the hike's own local `YYYY-MM-DD` (via Open-Meteo `timezone=auto`), not necessarily Arizona's. The dedup key ("already captured today, at this location?"). Header text itself wasn't renamed since the sheet already existed when CARD-0097 shipped; matching is positional, not by header name. |
| `lat` | Open-Meteo response | The actual grid point used, not the input coordinate |
| `lon` | Open-Meteo response | Same as `lat` |
| `temp_f` | Open-Meteo `hourly.temperature_2m` | °F, nearest hour to the triggering observation |
| `precip_pct` | Open-Meteo `hourly.precipitation_probability` | % chance |
| `wind_mph` | Open-Meteo `hourly.wind_speed_10m` | mph |
| `humidity_pct` | Open-Meteo `hourly.relative_humidity_2m` | % RH |
| `uv_index` | Open-Meteo `hourly.uv_index` | UVI |
| `provider` | Constant | `open-meteo` — future-proofing if the provider ever changes |

### Consumption

`components/hike-izer/fetch_hike_data.py` reads this sheet the same way it reads Environmental Data, Hiking Observations, and GPS Track — via the generic `action=export` endpoint, filtered to the requested day's window — and includes it in its output JSON as `hike_start_forecast`. See `.claude/skills/hike-izer/SKILL.md` for how the narrative-writing step reports it (or reports its absence, never fabricating a value).

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