# JCTsh Weather Station — Component Planning Document
**Author:** Joseph C Thomas (JCT)
**Purpose:** Planning document for the JCTsh DIY weather station — captures Phase 1 (Discovery), Phase 2 (Hardware), and Phase 3 (Architecture) decisions. Defines the phased build strategy and sets up the agenda for Phase 4 (Claude Code instructions).
**Version:** 1.2
**Version description:** Phase 3 complete. Added Phase 3 Architecture and Integration Design section with all checklist items resolved. Corrected Phase 1 technology notes: ESPHome replaces Arduino C++ per Build Standards; data pipeline (WU, Google Sheets) moves to Node-RED rather than ESP32 direct HTTP. Updated BOM to reflect on-hand inventory (BME280 ×6, ESP32 ×4, perfboard, headers, standoffs, LEDs, resistors already on hand — removed from purchase list). Corrected MQTT topic type to `components` per garage-radar precedent. Added environmental data architecture reference. Cleared Phase 3 checklist. Removed resolved open questions.
**Project:** JCTsh Weather Station
**Status:** Phase 3 complete — ready for Phase 4 when directed
**Related files:** `JCTsh-Component-Planning-Pattern.md`, `CLAUDE.md`, `ENVIRONMENT.md`, `JCTsh-Parts-Inventory.md`, `JCTsh-Build-Standards.md`, `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`

---

## Context Note

All required context files per `JCTsh-Component-Planning-Pattern.md` have been loaded and reviewed:

- `README.md` (repo root) ✅
- `CLAUDE.md` (repo root) ✅
- `ENVIRONMENT.md` (repo root) ✅
- `JCTsh-Parts-Inventory.md` (repo root) ✅
- `JCTsh-Build-Standards.md` (repo root) ✅
- `components/salt-sensor/README.md` ✅ — SmartThings reference pattern
- `components/garage-radar/README.md` ✅ — ESPHome and MQTT topic reference pattern

Phase 4 (Claude Code instructions) requires this document plus all the above context files to be loaded into the Claude Code session.

---

## Phase 1 — Discovery Summary

### Goal

Build a fully DIY outdoor weather station that:
- Measures temperature, humidity, barometric pressure, wind speed, wind direction, rain, UV index, and solar irradiance
- Runs completely off-grid on solar + LiPo battery power
- Publishes data to Weather Underground (public sharing + community data)
- Logs all data to Google Sheets (personal historical archive)
- Integrates with the existing JCTsh ecosystem (MQTT, Node-RED, Home Assistant, SmartThings)

### Technology Confirmed

- **Microcontroller:** ESP32 — chosen for built-in WiFi, sufficient GPIO, 3.3V I2C compatibility, deep sleep capability, and ESPHome platform support
- **Firmware platform:** ESPHome (required per JCTsh Build Standards Section 2.1 — Arduino C++ is not used for new builds)
- **Data pipeline:** Node-RED handles all external posting (Weather Underground, Google Sheets) via HTTP from always-on Pi — ESP32 publishes to MQTT only. This keeps the ESP32 wake cycle fast and retry/error logic in Node-RED where it belongs.
- **Power:** Solar panel → MPPT charger → LiPo battery → boost converter → ESP32. Deep sleep between readings to minimize power draw.
- **Integration path:** ESP32 → MQTT → Node-RED → Home Assistant → SmartThings (same path as all JCTsh components)
- **Environmental data store:** Google Sheets via Google Apps Script web app endpoint (Node-RED posts on behalf of all environmental sensors — see `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`)

### Key Feasibility Findings

- All sensor interfaces (BME280, VEML6075, SI1145, wind vane, anemometer, rain gauge, AS3935) are well-proven with ESP32 and have ESPHome components or can be wired as GPIO pulse counters and ADC inputs
- ESPHome handles deep sleep, MQTT, WiFi, OTA, and credentials natively — no custom WiFi or MQTT code required
- The SparkFun Weather Meter Kit uses reed switches — no active electronics, very reliable, but the wind vane outputs analog voltage up to 5V requiring a voltage divider before the ESP32's 3.3V ADC
- The VEML6075 is preferred over the SI1145 for true UV index (UVA + UVB); the SI1145 is retained for solar irradiance (visible + IR, W/m²)
- Node-RED is the right home for Weather Underground posting and Google Sheets posting — it is always-on, has HTTP request nodes, and keeps retry/error logic off the battery-powered ESP32
- Rain accumulation (rolling 60-min window, daily total) is computed in Node-RED from raw tip events — more reliable than preserving state across ESP32 deep sleep cycles in RTC memory
- The AS3935 lightning detector interrupt pin must be wired to a deep-sleep-wakeup-capable GPIO so strike events can wake the ESP32 between scheduled cycles. Rain gauge tip interrupt has the same requirement.
- Tucson's 300+ annual sun days and intense UV make this location ideal for solar power and make the UV/irradiance sensors particularly valuable
- Lat/lon is a first-class field in every sensor payload — fixed coordinates for the weather station, GPS-sourced for future mobile sensors (hiking monitor, Pleasure-Way)

---

## Phase 2 — Confirmed Bill of Materials

All items verified on Amazon as of the planning session (May 2026). On-hand items confirmed against `JCTsh-Parts-Inventory.md` — do not purchase these.

### On Hand — No Purchase Needed

| Item | Qty Available | Source |
|---|---|---|
| ESP32 DevKitC-32 38-pin | 4 on hand (1 allocated to porch sensor) — use 1 for weather station | Parts inventory |
| BME280 temp/humidity/pressure | 6 on hand | Parts inventory |
| Perfboard 5×7cm | ~33 on hand | Parts inventory |
| Female pin header strips | Selection on hand — confirm 19-pin ×2 available | Parts inventory |
| M3 brass standoff kit | Selection on hand — confirm 10mm male-female available | Parts inventory |
| Green + yellow LEDs (5mm) | Selection on hand | Parts inventory |
| Resistor assortment | Selection on hand — includes 330Ω (LEDs) and 10kΩ (voltage divider) | Parts inventory |

### To Purchase

| Item | Description | Link | Est. Price |
|---|---|---|---|
| VEML6075 | UV index (UVA + UVB), I2C | [Amazon](https://www.amazon.com/JESSINIE-VEML6075-Ultraviolet-Intensity-Detection/dp/B0BBLV1WWT) | ~$10 |
| SI1145 | Solar irradiance (visible + IR, W/m²), I2C | [Amazon](https://www.amazon.com/Adafruit-SI1145-Digital-Visible-ADA1777/dp/B00OKCSVUU) | ~$10 |
| SparkFun Weather Meter Kit | Wind speed + wind direction + rain gauge — RJ11 terminated, reed switch based | [Amazon](https://www.amazon.com/Weather-Meter-Kit-Anemometer-terminated/dp/B084DBXMPX) | ~$70 |
| Ambient Weather SRS100LX | Solar radiation shield for BME280 | [Amazon](https://www.amazon.com/Ambient-Weather-SRS100LX-Temperature-Radiation/dp/B003EB3GE4) | ~$20 |
| YETLEBOX IP67 enclosure (5.9×3.9×2.8") | Weatherproof housing — outdoor installation per Build Standards Section 1.1 | [Amazon](https://www.amazon.com/YETLEBOX-Waterproof-Electrical-Stainless-Enclosure/dp/B0BZHHMLFT) | ~$15 |
| AITRIP DS3231 RTC (3-pack) | Real-time clock, I2C, battery backup | [Amazon](https://www.amazon.com/AITRIP-Precision-AT24C32-Arduino-Raspberry/dp/B09KPC8JZQ) | ~$8 |
| CR2032 coin cells | Backup battery for DS3231 | Amazon / any | ~$5 |
| WWZMDiB Micro SD module (3-pack) | Local data logging backup | [Amazon](https://www.amazon.com/WWZMDiB-Adater-Module-Support-Arduino/dp/B0B779R5TZ) | ~$8 |
| 32GB microSD card | Storage for SD module | Amazon | ~$8 |
| Electronics-Salon RJ11/RJ12 4-way breakout | Terminal block breakout for SparkFun kit RJ11 cables | [Amazon](https://www.amazon.com/Electronics-Salon-4-Way-Breakout-Terminal-Connector/dp/B017B69D3U) | ~$12 |
| SparkFun AS3935 lightning detector | Lightning detection to 40km — Tucson monsoon season | [Amazon](https://www.amazon.com/SparkFun-Lightning-Detector-AS3935/dp/B07WFKWGC8) | ~$25 |
| Waveshare 6V 5W solar panel | Monocrystalline, matches CN3791 input | [Amazon](https://www.amazon.com/Solar-Panel-6V-Performance156-Monocrystalline/dp/B07PNTRSNY) | ~$18 |
| KBT 3.7V 6000mAh LiPo (JST) | ~40+ hours autonomy without sun | [Amazon](https://www.amazon.com/KBT-3-7V-6000mAh-Li-Polymer-Battery/dp/B0BJPSMQYK) | ~$18 |
| Taidacent CN3791 MPPT charger (6V) | Solar → LiPo MPPT charging, up to 2A | [Amazon](https://www.amazon.com/Taidacent-Chargers-Battery-Controller-Charging/dp/B089ZVSQ4K) | ~$10 |
| Dorhea MT3608 boost converter (10-pack) | LiPo (3.2–4.2V) → regulated 5V for ESP32 | [Amazon](https://www.amazon.com/MT3608-Converter-Adjustable-Voltage-Regulator/dp/B0BGLGL9RV) | ~$10 |

### Estimated Purchase Cost

| Category | Est. Cost |
|---|---|
| Environmental sensors (VEML6075, SI1145) | ~$20 |
| Mechanical sensors (SparkFun kit) | ~$70 |
| Ancillary / support modules | ~$81 |
| Power system | ~$56 |
| **Total to purchase** | **~$227** |

*(BME280, ESP32, perfboard, headers, standoffs, LEDs, resistors already on hand — ~$50 saved)*

### Power Budget Summary

| Parameter | Value |
|---|---|
| Solar panel peak output (Tucson) | ~830mA @ 6V |
| Daily solar energy (~6 sun-hours) | ~30 Wh |
| Active consumption (ESP32 + all sensors) | ~150mA @ 5V |
| Deep sleep consumption | ~2–5mA |
| Effective avg with 5-min wake cycle | ~10–15mA |
| Battery autonomy (no sun) | ~40+ hours |

---

## Phased Build Strategy

This is the most complex JCTsh component to date. The strategy below breaks the build into seven self-contained phases, each of which produces a working, testable system before the next phase begins. **No phase starts until the previous phase is confirmed working.**

| Phase | Name | Location | Power |
|---|---|---|---|
| A | Bench Proof | Bench | USB |
| B | Full Sensor Array | Bench | USB |
| C | Full Software Integration | Bench | USB |
| D | Power System | Bench | Solar/LiPo |
| E | Perfboard and Enclosure | Bench → Indoor | Solar/LiPo |
| F | Outdoor Deployment | Outdoors | Solar/LiPo |

The two guiding principles: **all software is finished before anything is soldered**, and **the station is a fully integrated JCTsh component before it ever goes outdoors.** Hardware phases build up the platform. Software phases make it complete. Enclosure and outdoor deployment are the last steps, not the integration point.

---

### Build Phase A — Bench Proof (ESP32 + BME280)

**Goal:** Confirm the development environment, ESP32 toolchain, and basic I2C sensor operation before any other hardware is involved.

**What gets built:**
- ESP32 flashed via Arduino IDE or PlatformIO
- BME280 wired to I2C (GPIO 21/22)
- Serial monitor confirms temp, humidity, pressure readings
- WiFi connects to home network

**Success criteria:** Serial output shows valid sensor readings. WiFi connects.

**Why first:** If the dev environment or ESP32 has any issue, it's cheapest to discover here with one sensor and a USB cable.

---

### Build Phase B — Full Sensor Array (Bench)

**Goal:** Validate all sensors on the shared buses simultaneously, and confirm all signal types are readable.

**What gets built:**
- VEML6075 and SI1145 added to I2C bus
- DS3231 RTC added to I2C bus — confirm time is set and held across power cycle
- SparkFun Weather Meter Kit wired via RJ11 breakout board
- Voltage divider built for wind vane (5V → 3.3V)
- Rain gauge interrupt confirmed on a GPIO pin
- Anemometer pulse counting confirmed
- AS3935 lightning detector wired (SPI)
- SD card module wired (SPI)
- Serial output shows all sensors reading simultaneously with no conflicts

**Success criteria:** All sensors produce valid readings with no I2C or SPI conflicts. Rain gauge and anemometer pulses counted correctly. RTC holds time after power cycle.

**Why here:** I2C address conflicts, SPI pin assignment conflicts, and GPIO interrupt issues are all much easier to diagnose on the bench with full serial visibility. Resolve all of these before adding software complexity.

---

### Build Phase C — Full Software Integration (Bench, USB Power)

**Goal:** Complete all software — external data pipeline and full JCTsh integration — while still on the breadboard with USB power and easy debug access. This is the last phase before the prototype is considered feature-complete. Nothing gets soldered until this phase passes.

**What gets built:**

*External data pipeline:*
- Weather Underground PWS HTTP upload confirmed (live data visible on WU site)
- Google Apps Script web app deployed and tested
- Google Sheets receives data and populates correctly
- RTC timestamps attached to all records
- SD card local log running as backup
- Deep sleep cycle implemented: wake → read → post to WU + Sheets + MQTT → sleep

*JCTsh integration (bench, all software):*
- MQTT publishing: weather data, log messages, and heartbeat on confirmed JCTsh topics
- Dedicated Mosquitto account created for the weather station
- Node-RED flow: ingests MQTT weather data, routes to HA entities
- Home Assistant entities: all weather sensors exposed
- SmartThings exposure: confirmed values via HA REST API → virtual entities → SmartThings
- Watchdog: heartbeat monitored, test alert fires to Pixel 10 Pro on missed heartbeat
- Phase 3 architecture checklist fully signed off (see below)

**Success criteria:** Data appears on Weather Underground, Google Sheets, and in Home Assistant on every wake cycle. SD card log grows. RTC timestamp is correct after sleep/wake. SmartThings shows weather station temperature. Watchdog fires a test alert. All Phase 3 checklist items checked off.

**Why here:** Integration bugs (MQTT topic mismatches, HA entity config, Node-RED logic errors, SmartThings mapping) are software problems — they are fastest to debug with the ESP32 on the bench, USB serial available, and no power or weather constraints. Every issue found here is one less issue to diagnose outdoors.

---

### Build Phase D — Power System (Bench)

**Goal:** Validate the solar + battery power chain in isolation before committing to perfboard layout.

**What gets built:**
- CN3791 MPPT charger wired: solar panel input, LiPo output
- MT3608 boost converter pre-set to 5V output, wired between LiPo and ESP32 VIN
- LiPo charges from solar panel under direct Tucson sun or lamp
- Full system (ESP32 + all sensors) runs from LiPo via boost converter through complete sleep/wake cycles
- Battery voltage monitored via ESP32 ADC (voltage divider on LiPo +) and reported in MQTT telemetry
- Deep sleep current measured — confirm < 5mA during sleep

**Success criteria:** System runs from battery for 2+ hours through multiple sleep/wake cycles with no resets. Solar panel charges battery measurably in direct sun. Sleep current is acceptable. Battery voltage appears in HA.

**Why before perfboard:** Power system faults (wrong voltage, instability under load, boost converter oscillation, sleep current bleed) are easiest to debug with breadboard access to every node. Locking this down before soldering avoids rework.

---

### Build Phase E — Perfboard and Enclosure

**Goal:** Migrate from breadboard prototype to a permanent, weatherproof installation. This phase is purely physical — all software is already done and proven.

**What gets built:**
- All connections migrated from breadboard to perfboard
- Perfboard mounted inside IP67 enclosure with appropriate standoffs
- BME280 mounted in SRS100LX radiation shield, wired through cable gland
- UV and irradiance sensors (VEML6075, SI1145) positioned for unobstructed sky view
- RJ11 cables from SparkFun kit routed through cable glands and strain-relieved
- Solar panel wired in through cable gland
- LiPo secured inside enclosure
- All cable glands sealed
- Full software cycle runs with enclosure closed — confirm nothing changed in the migration

**Success criteria:** All Phase C success criteria still pass with enclosure closed. No connections lost in the breadboard-to-perfboard migration. Enclosure closes and seals cleanly.

---

### Build Phase F — Outdoor Deployment

**Goal:** Mount the completed, proven station in its permanent outdoor location.

**What gets built:**
- Mounting pole/bracket installed
- Station mounted at correct height (wind sensors ~10ft per WMO recommendation)
- Solar panel oriented south at ~32° tilt (Tucson latitude = optimal year-round)
- 48-hour unattended operation confirmed
- Weather Underground data stream verified as continuous
- HA dashboard and SmartThings confirmed live with real outdoor data

**Success criteria:** Station runs unattended for 48 hours with no gaps in WU data stream or MQTT heartbeat. Battery voltage holds overnight. Watchdog stays silent.

---

## Phase 3 — Architecture and Integration Design

### Data Flow

```
Sensors (I2C + GPIO interrupts)
      ↓
ESP32 / ESPHome (wake → read → publish → sleep)
      ↓  MQTT
jctsh/components/weather-station/data
jctsh/components/weather-station/log
jctsh/components/weather-station/heartbeat
jctsh/components/weather-station/lightning
      ↓
Mosquitto broker (raspberrypi.local)
      ↓
Node-RED (always-on)
   ├── → Weather Underground PWS API (HTTP POST)
   ├── → Google Sheets via Apps Script endpoint (HTTP POST)
   │       catches jctsh/components/+/data wildcard —
   │       all environmental sensors feed one archive
   ├── → Home Assistant (REST API port 8123)
   │       temperature, humidity, rain, lightning entities
   └── → SmartThings (via HA entity exposure)
```

Node-RED owns all external HTTP posting. The ESP32 publishes to MQTT only — no direct HTTP calls from the device. This keeps wake cycles fast and retry/error logic on the always-on Pi.

### MQTT Topics

| Topic | Content |
|---|---|
| `jctsh/components/weather-station/data` | Full sensor payload (see schema below) |
| `jctsh/components/weather-station/log` | Standard JSON log messages + heartbeat log entry |
| `jctsh/components/weather-station/heartbeat` | Standard JSON heartbeat (monitored by Node-RED watchdog) |
| `jctsh/components/weather-station/lightning` | Strike event: `{ "component": "weather-station", "distance_km": N, "energy": N }` |

### Standard Sensor Payload

Every data message includes lat/lon as first-class fields. Fixed for the weather station; GPS-sourced for future mobile sensors.

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

Rain accumulation (`rainin`, `dailyrainin` for WU) is computed by Node-RED from `rain_tips` events — not on the ESP32.

### MQTT Account

Dedicated Mosquitto account `weather-station` — created before first flash per Build Standards Section 2.7. Add to credentials table in root `CLAUDE.md`.

### Heartbeat

5-minute interval. Published to both `/log` and `/heartbeat` topics per Build Standards Section 4.1. Heartbeat payload includes `battery_v` and `rssi_dbm` as state fields.

### Watchdog

Existing Node-RED watchdog flow (built during garage-radar project, `core/node-red/watchdog.flow.json`) catches `jctsh/+/+/heartbeat` via wildcard automatically. No new watchdog work required — confirm heartbeat topic matches `jctsh/components/weather-station/heartbeat` and the watchdog fires a test alert during Build Phase C.

### SmartThings Integration

| Value | SmartThings device type | Integration path |
|---|---|---|
| Temperature | Temperature Sensor capability | HA entity-exposure feature (Settings → SmartThings → Configure) |
| Rain active (boolean) | Contact Sensor (open = raining) | HA entity-exposure feature |
| Lightning strike | Virtual Switch (momentary ON) | Node-RED → HA REST API → virtual switch → SmartThings |

Wind speed, UV index, irradiance, humidity, and pressure are exposed in HA only — no SmartThings value for those.

### Timeout and Timer Logic

| Timeout | Where | Purpose |
|---|---|---|
| 5-minute deep sleep interval | ESPHome | Primary wake / read / publish / sleep cycle |
| Rain gauge debounce ~10ms | ESPHome | Suppress reed switch contact bounce on tip |
| AS3935 interrupt wakeup | ESPHome (ext. wakeup GPIO) | Wake ESP32 on lightning strike between scheduled cycles |
| Rain gauge tip interrupt wakeup | ESPHome (ext. wakeup GPIO) | Wake ESP32 on rain tip between scheduled cycles |
| Rolling 60-min rain accumulator | Node-RED | Computes `rainin` for WU from raw tip events |
| Daily rain accumulator (midnight reset) | Node-RED | Computes `dailyrainin` for WU |
| Lightning event cooldown ~60s | ESPHome | Suppress duplicate AS3935 events per strike |
| Heartbeat 5-min interval | ESPHome | Watchdog visibility and dashboard |

### LED Indicators

| LED | Color | State it reflects | GPIO |
|---|---|---|---|
| WiFi / MQTT | Green | Connected and publishing | TBD in Phase 4 |
| Charging | Yellow | Solar → LiPo charge active | TBD in Phase 4 |

Both colors confirmed on hand per parts inventory. 330Ω current-limiting resistors on hand. GPIOs assigned in Phase 4 after full GPIO allocation table is built.

### Environmental Data Architecture

The weather station is the first member of a planned JCTsh environmental sensor family. The Google Sheets archive and Node-RED data handler are designed for multiple sources from day one. See `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md` for the full multi-source design, payload schema standard, and planned device family (porch sensor, hiking monitor, Pleasure-Way).

### Phase 3 Checklist — Completed

| Item | Status | Decision |
|---|---|---|
| MQTT topic naming | ✅ Done | `jctsh/components/weather-station/data`, `/log`, `/heartbeat`, `/lightning` — follows garage-radar `components` precedent |
| MQTT account | ✅ Done | Dedicated account `weather-station` — created before first flash |
| Heartbeat | ✅ Done | 5-min interval to both `/log` and `/heartbeat` — includes `battery_v` and `rssi_dbm` |
| Message logging | ✅ Done | Standard JSON to `/log` — Node-RED wildcard routes automatically |
| Watchdog | ✅ Done | Existing watchdog catches `/heartbeat` wildcard automatically — no new flow needed |
| SmartThings device type | ✅ Done | Temperature Sensor + Contact Sensor (rain) via HA entity-exposure; lightning via virtual switch |
| SmartThings integration path | ✅ Done | Node-RED → HA REST API → entity → SmartThings (no direct path) |
| Timeout / timer logic | ✅ Done | See timeout table above |
| LED indicators | ✅ Done | Green (WiFi/MQTT), Yellow (charging) — GPIOs assigned in Phase 4 |

## Future Enhancements (Deliberately Deferred)

These were considered and explicitly deferred. Not forgotten — just not in scope for the initial build.

| Enhancement | Why Deferred |
|---|---|
| Air quality sensors (PM2.5, CO₂, VOC) | Adds complexity and cost; primary sensors are the priority |
| Soil moisture sensor | Only relevant if landscaping is added; easy to add later via separate I2C node |
| Local display (OLED/TFT) | Nice to have but station is outdoors; data is accessible via WU and HA |
| Fan-assisted ventilation for radiation shield | Improves accuracy in low-wind conditions; passive shield sufficient for initial build |
| LoRa radio backup | Would allow operation if WiFi is unavailable; not needed with current placement |
| Leaf wetness sensor | Agricultural use only — not in scope for this installation |
| Porch sensor | Planned next environmental sensor — will reuse this architecture and data handler |
| Hiking monitor | Mobile sensor — GPS-sourced lat/lon via Pixel hotspot; deferred until weather station is deployed |
| Pleasure-Way sensor node | RV environmental monitoring — interior + exterior; deferred until weather station is deployed |