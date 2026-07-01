# JCTsh Van Sensor Suite — Phase 1 Planning Document
**Author:** Joseph C Thomas (JCT)
**Purpose:** Phase 1 discovery and feature decisions for the JCTsh Pleasure-Way van environmental sensor suite. Covers feasibility analysis, architectural decisions, sensor selection, connectivity model, data pipeline, and open questions for Phase 2.
**Version:** 1.0
**Version description:** Initial release. Phase 1 complete.
**Project:** JCTsh Van Sensor Suite
**Status:** Phase 1 Complete — Ready for Phase 2
**Related files:** `README.md`, `CLAUDE.md`, `ENVIRONMENT.md`, `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`, `JCTsh-Build-Standards.md`, `JCTsh-Component-Planning-Pattern.md`, `jctsh-network.md`, `jctsh-parts-inventory.md`

---

## What This Component Is

Two portable ESP32-based environmental sensor nodes for use in and around the Pleasure-Way Ram ProMaster 3500 camper van. One node monitors interior conditions; one monitors exterior conditions. Both nodes log timestamped readings to onboard flash storage during travel and camping, and sync automatically with JCTsh on return home via WiFi — publishing to the standard environmental data pipeline (MQTT → Node-RED → Google Sheets).

This component is part of the JCTsh environmental sensor family defined in `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`. Both nodes must conform to the standard environmental message payload and MQTT topic convention.

GPS track correlation uses GPSLogger running passively on the Pixel 10 Pro XL, posting to a Node-RED HTTP-in listener on the home Pi over cellular. No GPS hardware on either van node.

---

## Van Context

- **Vehicle:** Pleasure-Way Ram ProMaster 3500 camper van
- **Typical trips:** Weekend to multi-week; planning a 2-month Canada trip
- **Cell service:** Variable — sometimes spotty for extended periods
- **Coach power:** 12V DC available throughout the van
- **Cooking:** Always outside on a griddle — no cooking odors or grease inside the van
- **Generator:** Not used (haven't run it in years)
- **Propane:** Used inside van; standalone propane safety sensor already installed — van node propane sensing is data/monitoring only, not safety-critical
- **WiFi in van:** Pi hotspot only (coachproxyos), established for eRVin/Firefly project
- **Phone:** Google Pixel 10 Pro XL — GPSLogger runs passively all trip; GaiaGPS for hike navigation

---

## Architecture Overview

Each node operates in two modes:

**Field mode (traveling or camping):** No home WiFi. Reads sensors at configured interval (default 10 minutes), timestamps each reading using DS3231 RTC, stores to onboard flash. DS3231 maintains accurate time regardless of WiFi or cellular availability.

**Home mode (in driveway):** Connected to JCTnet1 home WiFi. Replays full onboard flash buffer to home Mosquitto broker in sequence using original timestamps. Node-RED wildcard handler routes to Google Sheets automatically. Publishes 5-minute heartbeat per JCTsh standards.

**Opportunistic sync (Pixel hotspot):** When the Pixel hotspot is active during a trip, both nodes connect and replay their full onboard flash buffers to the home Mosquitto broker over cellular. Cellular data volume is trivially small (~58KB/day for both nodes combined at 10-minute intervals). Hotspot sync is available but not required — nodes function fully without it.

**GPS correlation:** GPSLogger runs passively on the Pixel 10 Pro XL for the entire trip — driving, hiking, and camp. Posts GPS coordinates to a Node-RED HTTP-in listener on the home Pi over cellular as connectivity allows. GPSLogger queues requests when offline and delivers when service returns. Sensor readings are correlated to GPS track by matching timestamps. GaiaGPS continues to run for hike navigation independently.

**coachproxyos Pi role:** No role in the van sensor data path. The Pi remains the Firefly/eRVin RV-C interface it already is. The van sensor suite is entirely independent of it.

---

## Resolved Decisions

### Nodes

| Decision | Rationale |
|---|---|
| Two separate ESP32 nodes — indoor and outdoor | Different sensor suites, different mounting locations, different power sources; separation avoids I2C cable runs inside the van |
| No wired sensor connections between nodes and Pi | Cable runs inside the van are undesirable; WiFi-connected ESP32 nodes eliminate this entirely |
| No router — Pi hotspot only | No benefit over Pi hotspot for this use case; adds cost, complexity, power draw, and boot-order dependency |
| coachproxyos Pi not in sensor data path | No MQTT broker on Pi; no two-broker sync problem; cleaner architecture |

### Sensors — Outdoor Node

| Sensor | Decision | Rationale |
|---|---|---|
| Temperature / Humidity / Pressure | BME280 (genuine GY-BME280) | On hand (3 spares); proven in JCTsh; native ESPHome support |
| UV Index | Adafruit LTR-390 | VEML6075 discontinued; LTR-390 is direct successor — digital I2C, true UV measurement, native ESPHome `ltr390` platform |
| Air Quality | Sensirion SEN55 | PM1.0, PM2.5, PM4.0, PM10, VOC index, NOx index in one I2C module; fan duty-cycled via GPIO transistor to reduce average power draw; primary motivation is wildfire smoke, haboobs, and ozone |

### Sensors — Indoor Node

| Sensor | Decision | Rationale |
|---|---|---|
| Temperature / Humidity / Pressure | BME280 (genuine GY-BME280) | On hand (3 spares); consistent with outdoor node |
| CO2 | Sensirion SCD40 | True CO2 via photoacoustic sensing; I2C; directly relevant to van interior ventilation quality — occupancy, sleeping, propane appliance use |
| Propane / combustible gas | MQ-6 | LPG/propane-specific; analog ADC output; not safety-critical (standalone sensor already installed); data/monitoring role only; warm-up period ~1 minute; draws ~150–200mA during heating element operation |

### Clock — Both Nodes

| Decision | Rationale |
|---|---|
| DS3231 hardware RTC on both nodes | ESP32 internal oscillator drifts 1–5 minutes/day, worse under temperature variation — unacceptable for a 2-month trip with spotty cell service; DS3231 TCXO holds ±2 minutes/year; I2C; CR2032 coin cell backup; set once from NTP, accurate indefinitely |
| NTP on WiFi connect | Standard ESPHome SNTP component; syncs whenever home WiFi or Pixel hotspot is available; DS3231 updated on each NTP sync |

### Microcontroller — Both Nodes

| Decision | Rationale |
|---|---|
| ESP32 DevKitC-32 (38-pin, CP2102, USB-C) | Consistent with JCTsh ecosystem; 1 on hand (1 more needed — see Phase 2 BOM) |
| ESPHome firmware | Required per CLAUDE.md for all future ESP32 components |
| Custom C++ ESPHome component | Required for onboard flash storage and WiFi replay — same pattern as hiking monitor |

### Storage and Logging — Both Nodes

| Decision | Rationale |
|---|---|
| Onboard flash storage, 2MB partition | Default 1.5MB partition is tight for 2-month trip at 10-minute intervals; 2MB allocation gives ~15% headroom for a full 2-month trip |
| 10-minute logging interval (configurable) | Sufficient resolution for environmental variation in van context; conditions change slowly; configurable parameter for flexibility (shorter interval for testing, longer for extended trips) |
| Original timestamps preserved | Readings published to MQTT with `ts` from time of measurement, not time of upload |
| `storage_pct` field in payload | flash storage usage as a percentage; published with each reading when on WiFi; visible in Google Sheets; enables monitoring of storage state without runtime adaptive logic |

**Storage math (2-month trip, 10-minute interval):**
- 6 readings/hour × 24 hours × 60 days = 8,640 readings per node
- ~200 bytes per JSON reading = ~1.7MB per node
- Fits in 2MB flash partition with ~15% headroom

### Power — Outdoor Node

| Decision | Rationale |
|---|---|
| LiPo pouch (EEMB 1100mAh) + TP4056+boost module | On hand; same pattern as hiking monitor; flat form factor |
| 12V USB cradle in van | Keeps outdoor node charged when stored in van; node placed outside at campsite |
| Battery operation when deployed outside | Full portability — sits on picnic table, window ledge, or any convenient surface without cable tether |

### Power — Indoor Node

| Decision | Rationale |
|---|---|
| 12V USB from coach power, always on | MQ-6 requires continuous power for heating element (~150–200mA); safety-adjacent function benefits from continuous operation; 12V coach power is available throughout van |

### GPS and Track Correlation

| Decision | Rationale |
|---|---|
| No GPS hardware on either node | GPSLogger on Pixel 10 Pro XL provides continuous GPS track for the entire trip |
| GPSLogger runs passively all trip | Single continuous track covers driving, hiking, camp — one source for all correlation; GaiaGPS runs independently for navigation |
| GPSLogger posts to home Pi via cellular | Node-RED HTTP-in listener on home Pi receives GPS coordinates; GPSLogger queues when offline, delivers when service returns; no Pi hotspot involvement |
| Timestamp correlation | Each sensor reading timestamp matched to nearest GPSLogger trackpoint; DS3231 accuracy ensures timestamp error is seconds, not minutes |
| `lat` / `lon` in payload | Populated by Node-RED from nearest GPSLogger trackpoint at time of sensor reading upload, or null if no GPS data available for that timestamp |

### JCTsh Integration

| Decision | Rationale |
|---|---|
| MQTT topics: `jctsh/components/van-sensor-outdoor/data` etc. | Follows environmental sensor family convention |
| MQTT topics: `jctsh/components/van-sensor-indoor/data` etc. | Follows environmental sensor family convention |
| Node-RED wildcard handler catches data automatically | Existing `jctsh/components/+/data` subscription; no new Node-RED flow needed for data routing |
| Google Sheets archive | Permanent queryable record; pipeline inherited from hiking monitor project |
| No SmartThings integration | No real-time state to expose; van is a mobile asset |
| Dedicated Mosquitto accounts | `van-sensor-outdoor` and `van-sensor-indoor` — created per JCTsh-Build-Standards.md Section 2.7 |
| Watchdog behavior | Standard JCTsh watchdog logs device offline/online; alerts expected and normal during travel |

### Connectivity Model

| Network | Node behavior |
|---|---|
| Home WiFi (JCTnet1) | Replay full onboard flash buffer to home Mosquitto broker; resume normal logging; NTP sync via home network |
| Pixel hotspot | Replay full onboard flash buffer to home Mosquitto broker over cellular; NTP sync; buffer cleared after successful replay |
| No WiFi | Log to onboard flash; DS3231 maintains accurate timestamps |

**Pixel hotspot SSID and password must be fixed** — configure once in ESPHome; do not change.

### Deferred Features

| Feature | Status |
|---|---|
| Dedicated GPS module on outdoor node (Approach B) | Deferred — requires external active antenna routed from under-seat Pi location to dash; GPSLogger approach sufficient for Phase 1 |
| Adaptive logging interval based on storage usage | Deferred — solved at design time by 2MB flash partition and 10-minute interval; runtime adaptive logic adds complexity for no practical benefit |
| Real-time dashboard while traveling | Out of scope — data pipeline is archive-oriented; no real-time display requirement |
| Coach systems data (Firefly/eRVin RV-C) | Deferred — possible but not a priority; eRVin MQTT data could be archived if desired as a future enhancement |
| OBD2 engine data | Explicitly out of scope — standard drivetrain data not of interest; propane coach use covered by MQ-6 |

---

## Standard Environmental Payload

Conforms to `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`. Fields sent by each node:

**Outdoor node:**
```json
{
  "component": "van-sensor-outdoor",
  "ts": "2026-07-15T14:32:00Z",
  "lat": 49.2827,
  "lon": -123.1207,
  "temp_f": 74.2,
  "humidity_pct": 58.3,
  "pressure_hpa": 1012.4,
  "uv_index": 6.1,
  "pm1_0_ug_m3": 4.2,
  "pm2_5_ug_m3": 6.8,
  "pm4_0_ug_m3": 7.1,
  "pm10_ug_m3": 8.0,
  "voc_index": 112,
  "nox_index": 14,
  "storage_pct": 23.4,
  "battery_v": 3.87,
  "rssi_dbm": -58
}
```

**Indoor node:**
```json
{
  "component": "van-sensor-indoor",
  "ts": "2026-07-15T14:32:00Z",
  "lat": 49.2827,
  "lon": -123.1207,
  "temp_f": 71.6,
  "humidity_pct": 52.1,
  "pressure_hpa": 1012.3,
  "co2_ppm": 842,
  "propane_pct": 0.0,
  "storage_pct": 21.8,
  "rssi_dbm": -61
}
```

`lat` and `lon` — populated by Node-RED from nearest GPSLogger trackpoint by timestamp; null if no GPS data available for that window.

`storage_pct` — flash storage usage percentage; diagnostic field visible in Google Sheets; allows monitoring of storage state during trip sync events.

`battery_v` — outdoor node only; indoor node is always on 12V USB.

`rssi_dbm` — WiFi signal strength; diagnostic field confirming clean connection on sync.

Derived fields (`dew_point_f`, `heat_index_f`) computed by Node-RED, not sent by device.

---

## MQTT Component Names

- `van-sensor-outdoor`
- `van-sensor-indoor`

Topics per node (example for outdoor):
- `jctsh/components/van-sensor-outdoor/data`
- `jctsh/components/van-sensor-outdoor/log`
- `jctsh/components/van-sensor-outdoor/heartbeat`

---

## Preliminary BOM Notes

Full BOM confirmed in Phase 2 after inventory scan. Preliminary assessment:

**Likely on hand:** ESP32 DevKitC-32 (1 of 2 needed), BME280 ×2, LiPo pouch, TP4056+boost module, perfboard, headers, standoffs, breadboards, buttons, JST connectors, LEDs, resistors.

**Likely to order:** ESP32 DevKitC-32 ×1, DS3231 RTC ×2, LTR-390 ×1, SEN55 ×1, SCD40 ×1, MQ-6 ×1.

Inventory scan is a required Phase 2 first step — confirm on-hand quantities before ordering anything.

---

## Open Questions for Phase 2

1. **Enclosure — outdoor node:** Weather resistance required for outdoor camping use. 3D-printed with weatherproof coating, or off-the-shelf IP65 project box? SEN55 requires air intake/exhaust ports. LTR-390 requires sky-facing UV window.
2. **Enclosure — indoor node:** No weather resistance needed. Open standoff mount (default JCTsh convention) or small project box for van aesthetics?
3. **MQ-6 warm-up:** 1-minute warm-up on power-on means first propane reading after boot is unreliable. How to handle in ESPHome — discard first N readings, or publish with a `warming_up` flag?
4. **SEN55 fan duty cycle:** What GPIO transistor circuit and what duty cycle? Balance measurement accuracy against average power draw for battery operation.
5. **Outdoor node mounting at campsite:** How is it placed or attached outside? Stake, suction cup, velcro to van exterior? Needs to survive wind.
6. **Indoor node permanent location:** Where in the van interior does it live? Near propane appliances? Near sleeping area? Both? One unit or two indoor nodes?
7. **Flash partition table:** Confirm 2MB flash partition is achievable with the ESP32 DevKitC-32 flash size and ESPHome partition tooling.
8. **GPSLogger home Pi endpoint:** Node-RED HTTP-in listener design — what does the Pi do with GPS coordinates? SQLite? Flat file? How does Node-RED correlate GPS trackpoints to sensor readings at upload time?
9. **Pixel hotspot SSID/password:** Establish fixed values before ESPHome build.
10. **Inventory scan:** Load `jctsh-parts-inventory.md` and confirm on-hand quantities before finalizing BOM or ordering anything.

---

## Phase 2 Entry Criteria

Phase 1 is complete. Phase 2 (Hardware Selection) begins when:
- `jctsh-parts-inventory.md` is loaded and inventory scan is complete
- `CLAUDE.md`, `ENVIRONMENT.md`, `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`, `JCTsh-Build-Standards.md`, and `jctsh-network.md` are loaded for architecture and integration context
- Open questions 1–6 above are resolved or at least framed enough to drive hardware decisions

---

*Phase 1 completed through interactive planning session, May 2026. Two-node architecture (indoor/outdoor), ESP32/ESPHome/onboard flash pattern, DS3231 RTC, GPSLogger GPS correlation, opportunistic Pixel hotspot sync, and full data pipeline design all resolved in Phase 1.*
