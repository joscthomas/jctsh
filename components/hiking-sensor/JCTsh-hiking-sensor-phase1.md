# JCTsh Hiking Monitor — Phase 1 Planning Document
**Author:** Joseph C Thomas (JCT)
**Purpose:** Phase 1 discovery and feature decisions for the JCTsh hiking environmental sensor (hiking-monitor component). Covers feature analysis, all resolved decisions, deferred items, BOM, shopping list, and open questions for Phase 2.
**Version:** 2.5
**Version description:** GPS correlation and Pixel hotspot sync updated from deferred/manual to planned iterative additions. GPS correlation approach updated: GPSLogger automatic lat/lon population via Node-RED pipeline (Steps 19–20) replaces manual post-hike GaiaGPS timestamp matching. Pixel hotspot sync added as Step 21 — second WiFi network in ESPHome YAML. Both added as post-Step-18 iterative refinements in the Claude Code instructions. Motivation updated: hiking sensor used while traveling, not just at home. No other changes from v2.4.
**Project:** JCTsh Hiking Monitor
**Status:** Phase 1 Complete — Parts Ordered — Build In Progress (Step 14 perfboard complete)
**Related files:** `README.md`, `CLAUDE.md`, `ENVIRONMENT.md`, `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`, `JCTsh-Build-Standards.md`, `JCTsh-Component-Planning-Pattern.md`, `jctsh-parts-inventory.md`

---

## What This Component Is

A portable, body-carried environmental sensor for use on hikes in the Tucson area and one annual backpacking trip. Measures temperature, humidity, barometric pressure, and UV index in real time. Displays readings locally on an e-ink display. Logs timestamped readings to onboard flash storage during the hike. Syncs automatically with JCTsh on return home via WiFi — publishing to the standard environmental data pipeline (MQTT → Node-RED → Google Sheets).

This component is part of the JCTsh environmental sensor family defined in `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`. It must conform to the standard environmental message payload and MQTT topic convention.

---

## Hiking Context

- **Day hikes:** Tucson area, 6–10 miles, 2–2.5 mph with hiking buddy / 2 mph solo
- **Terrain:** Sonoran Desert, mostly open, occasionally bushwhacking
- **Gear:** Osprey hydration pack (most hikes), shorts and short-sleeve hiking shirt, wide brim sun hat
- **Phone:** Google Pixel 10 Pro XL running GaiaGPS — tracks every hike independently
- **Backpacking:** One trip per year, 3–6 days, with hiking buddy
- **Emergency messaging:** Pixel satellite messaging capability — no LoRa or separate radio needed

---

## Architecture Overview

The device operates in two modes:

**Field mode (during hike):** No WiFi, no MQTT. Reads sensors every 2 minutes, timestamps each reading using NTP-synced system clock, stores to onboard flash storage. Display updates every 2 minutes. Button wakes display on demand.

**Home mode (in cradle):** Connected to JCTnet1 WiFi. Publishes stored hike readings to MQTT in sequence using original hike timestamps. Node-RED wildcard handler routes to Google Sheets automatically. Publishes 5-minute heartbeat per JCTsh standards.

**GPS correlation:** GPSLogger runs passively on the Pixel 10 Pro XL and posts coordinates to a Node-RED HTTP-in listener on the home Pi over cellular. Node-RED populates `lat`/`lon` in each sensor reading payload by matching the nearest GPS trackpoint by timestamp at upload time. No GPS hardware on the device. GaiaGPS continues to run independently for hike navigation. This pipeline is built as Steps 19–20 (iterative refinement after core build is proven).

**Pixel hotspot sync:** When the Pixel hotspot is active during travel, the device connects and replays its onboard flash buffer to the home Mosquitto broker over cellular. Built as Step 21. Not needed for local day hikes; valuable when hiking while traveling away from home.

**Clock synchronization:** Device stays powered in charging cradle between hikes, connected to WiFi, clock synced via NTP. Clock remains accurate across any hike duration — no RTC hardware needed.

---

## Resolved Decisions

### Sensors
| Sensor | Decision | Rationale |
|---|---|---|
| Temperature / Humidity / Pressure | BME280 (genuine GY-BME280) | On hand (3 spares); proven in JCTsh; native ESPHome support |
| UV Index | Adafruit LTR-390 | VEML6075 discontinued; LTR-390 is direct successor — digital I2C, true UV measurement, native ESPHome `ltr390` platform; must face open sky — enclosure design must accommodate |

### Microcontroller
| Decision | Rationale |
|---|---|
| ESP32 DevKitC-32 (38-pin, CP2102, USB-C) | On hand (2 available); consistent with JCTsh ecosystem |
| ESPHome firmware | Required per CLAUDE.md for all future ESP32 components |
| One custom C++ ESPHome component | Required for onboard flash storage and WiFi replay — the only part ESPHome cannot handle declaratively |

### Display
| Decision | Rationale |
|---|---|
| Waveshare 2.13" e-ink, 250×122, SSD1680, partial refresh | Best outdoor/sunlight readability; zero static power draw; 2-minute update interval matches slow refresh perfectly; explicit ESPHome support |
| Single screen, no cycling | Four fields fit comfortably; no second button needed |

**Display layout:**
```
Temp:      87°F    Humidity: 32%
UV Index:  9.2     Pressure: ↓
```
Pressure shown as trend arrow (↑ rising / → steady / ↓ falling) — meteorologically actionable on trail; raw hPa value not displayed.

### Power
| Decision | Rationale |
|---|---|
| EEMB 1100mAh LiPo pouch (603449) | Flat form factor — 51mm × 34mm × 6mm; ~40% smaller enclosure volume vs. 18650; significantly better belt/chest carry comfort; built-in PCM protection |
| TP4056 + boost combined module (33mm × 23mm) | Single module handles charging and 3.7V→5V boost; solar VIN+ pad accepts SUNYIMA panel input directly |
| Micro USB charging port — external | Only charging port visible on enclosure exterior |
| USB-C (ESP32) — internal only | Used for initial flash and emergency recovery only; OTA handles all subsequent firmware updates |
| JST connector — external | Solar panel input to TP4056+boost module VIN+ pad; used for backpacking trips |
| Voltage divider to ESP32 ADC | Battery voltage monitoring; maps to approximate charge level; no fuel gauge IC needed |
| No display of battery level | Battery life between charges is not a concern for day hikes; voltage divider data still logged in MQTT payload as `battery_v` |

**Power architecture:**
```
SUNYIMA solar panel (5.5V, optional) ─┐
Micro USB (5V charging) ──────────────┤→ TP4056+boost module → 5V out → ESP32 VIN
EEMB LiPo pouch (3.7V) ──────────────┘
```

**Enclosure size comparison — why LiPo pouch was chosen:**

| | 18650 + AEDIKO (original) | LiPo pouch + TP4056+boost (chosen) |
|---|---|---|
| Estimated enclosure | ~80mm × 55mm × 25mm | ~75mm × 45mm × 20mm |
| Volume | ~110 cm³ | ~68 cm³ (~40% smaller) |
| Shape | Blocky, cylinder-dominated | Flat slab |
| Belt/chest comfort | Moderate — protrudes | Much better — lies flat against body |

AEDIKO modules and 18650 cells remain in inventory for future projects.

**LiPo connector polarity warning:** Verify JST connector polarity before connecting LiPo pouch to TP4056+boost module — do not assume red = positive on the module side without checking.

### Storage and Logging
| Decision | Rationale |
|---|---|
| onboard flash storage | Trivially small data volume (~36KB per 6-hour hike); no SD card hardware needed |
| 2-minute logging interval | Sufficient resolution for environmental variation; ~180 readings per 6-hour hike |
| Original hike timestamps preserved | Readings published to MQTT with `ts` from time of measurement, not time of upload |

### Clock
| Decision | Rationale |
|---|---|
| No RTC hardware | Device stays powered in cradle between hikes; NTP sync via home WiFi; clock accurate at hike start |
| NTP on WiFi connect | Standard ESPHome SNTP component; timezone: America/Phoenix |

### GPS and Track Correlation
| Decision | Rationale |
|---|---|
| No GPS hardware on device | GPSLogger on Pixel 10 Pro XL provides the GPS track; phone always carried |
| GPSLogger automatic lat/lon population | GPSLogger posts to Node-RED HTTP-in listener over cellular; Node-RED matches nearest trackpoint by timestamp and populates `lat`/`lon` at upload time. Built as Steps 19–20 (iterative refinement after core build). Replaces earlier manual GaiaGPS correlation approach. |
| Pixel hotspot sync | Second WiFi network in ESPHome YAML — device connects to Pixel hotspot when home WiFi unavailable, replaying onboard flash buffer over cellular. Built as Step 21. Valuable when traveling; not needed for local day hikes. |
| Timestamp correlation | Each sensor reading timestamp matched to nearest GPSLogger trackpoint (±5 minute window); NTP-synced clock ensures timestamp accuracy |

### lat/lon Fields
| Decision | Rationale |
|---|---|
| `"lat": null, "lon": null` initially; populated by Node-RED pipeline in Steps 19–20 | No GPS on device; Node-RED populates from GPSLogger trackpoint store at upload time. Null for readings where no GPS trackpoint is available within ±5 minutes (e.g., before pipeline is built, or when GPSLogger is not running). |

### UI
| Decision | Rationale |
|---|---|
| Single button | Wake/update display on demand |
| No waypoint button | GaiaGPS on phone already handles waypoint marking with meaningful names; device adds nothing to that workflow |

### Carry Method
| Decision | Rationale |
|---|---|
| Chest strap mount (primary) | Sensor faces torso — naturally shaded, in moving air; display faces outward for reading; most accurate temperature position |
| Belt clip with carabiner (secondary) | For hikes without hydration pack; sensor facing torso on belt |

### Enclosure
| Decision | Rationale |
|---|---|
| 3D-printed, white or light PETG | Minimizes solar gain on enclosure body |
| Stevenson-screen louvered port for BME280 | Shades sensor from direct radiation; allows airflow; integrated into enclosure design |
| LTR-390 on top face | Must see open sky; separate from shielded BME280 port |
| Micro USB port external | Charging access |
| JST connector external | Solar panel connection |
| USB-C internal | Emergency reflash only |
| Single button on side | Display wake |
| Carabiner bail or loop at top | Attachment point |
| Target footprint | ~75mm × 45mm × 20mm — flat slab, LiPo pouch is dominant constraint |

### Charging Cradle
| Decision | Rationale |
|---|---|
| Simple 3D-printed stand | Holds device upright with Micro USB connected; device stays on between hikes; NTP sync maintained |

### Solar Charging (Backpacking)
| Decision | Rationale |
|---|---|
| JST connector on enclosure routes to TP4056+boost VIN+ pad | Solar input supported natively by module; SUNYIMA panels (5.5V, 80mA) on hand — 10 units; verify panel voltage under load before finalizing wiring |
| Optional use only | Not needed for day hikes; plugged in for backpacking trips |
| Deep sleep between readings | Reduces average current draw significantly; one panel may balance consumption in sunny conditions |

### JCTsh Integration
| Decision | Rationale |
|---|---|
| MQTT topic: `jctsh/components/hiking-monitor/data` | Follows environmental sensor family convention |
| MQTT topic: `jctsh/components/hiking-monitor/log` | Standard log topic |
| MQTT topic: `jctsh/components/hiking-monitor/heartbeat` | Standard heartbeat topic; publishes when home WiFi connected |
| Node-RED wildcard handler catches data automatically | Existing `jctsh/components/+/data` subscription; no new Node-RED flow needed for data routing |
| Google Sheets archive | Permanent queryable record of all hike sensor data; pipeline built as part of this project |
| No SmartThings integration | No real-time state to expose |
| Watchdog behavior | Standard JCTsh watchdog logs device offline/online; alerts expected and normal during hikes |
| Dedicated Mosquitto account | `hiking-monitor` — created per JCTsh-Build-Standards.md Section 2.7 |

### Data Pipeline (New — Built as Part of This Project)
This project builds the JCTsh environmental data pipeline for the first time. All subsequent environmental sensors (weather station, porch sensor, Pleasure-Way) will inherit it.

| Piece | What it is |
|---|---|
| Google Sheet | Environmental archive spreadsheet with standard column schema from core/data-pipeline/JCTsh-Environmental-Data-Architecture.md |
| Google Apps Script web app | JavaScript REST endpoint deployed from the Sheet; accepts JSON POST; appends one row; authenticated via secret key in URL |
| Node-RED wildcard handler flow | Subscribes to `jctsh/components/+/data`; computes derived fields (dew_point_f, heat_index_f); POSTs to Apps Script; logs success/failure |
| Node-RED environment variables | Apps Script URL and secret key — not in source control |

### Deferred Features
| Feature | Status |
|---|---|
| Health sensing (HR, SpO2, skin temp, IMU) | Explicitly deferred — planned as a separate project using the LilyGO T-WATCH-S3 Plus; see Future Projects section below |
| Air quality sensing (PM2.5, VOC, NOx) | Explicitly deferred — planned as a separate standalone companion device (SEN55); see Future Projects section below |
| Hiking observations pipeline | Explicitly deferred — planned as a separate software-only project; see Future Projects section below |
| Aspiration fan (forced airflow over BME280) | Deferred to Phase 2+ — evaluate temperature accuracy first; may not be needed |
| LTR-390 enclosure glazing | Deferred to enclosure design — sensor may need UV-transparent window if recessed |
| Deep sleep implementation | Deferred to firmware phase — implement after basic operation confirmed; significant battery life improvement for backpacking |
| Solar panel clip/mount design | Deferred to enclosure design phase |
| Compass / magnetometer | Not needed — phone handles navigation |
| Bluetooth / real-time GaiaGPS feed | Not needed — timestamp correlation approach is cleaner |
| Touchscreen | Not needed |
| LoRa radio | Not needed — Pixel satellite messaging handles emergency comms |

---

## Standard Environmental Payload

Conforms to `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`. Fields sent by this device:

```json
{
  "component": "hiking-monitor",
  "ts": "2026-05-27T14:32:00Z",
  "lat": null,
  "lon": null,
  "temp_f": 87.4,
  "humidity_pct": 32.1,
  "pressure_hpa": 1005.2,
  "uv_index": 9.2,
  "battery_v": 3.94,
  "rssi_dbm": -67
}
```

`rssi_dbm` — WiFi signal strength in decibels relative to a milliwatt. Diagnostic field confirming clean connection on return home. Provided natively by ESPHome.

`lat` and `lon` are always null for this device. Filter on `lat IS NOT NULL` in Sheets queries to exclude hiking-monitor rows from location-based analysis.

Derived fields (`dew_point_f`, `heat_index_f`) computed by Node-RED, not sent by device.

---

## Bill of Materials

### On Hand
| Component | Qty | Notes |
|---|---|---|
| ESP32 DevKitC-32 (38-pin, CP2102, USB-C) | 1 | From hiBCTR 6-pack |
| BME280 (genuine GY-BME280) | 1 | From 3 spare units on hand |
| SUNYIMA mini solar panel (5.5V, 80mA) | 1 | From 10-unit inventory (backpacking use only) |
| Perfboard (5×7cm recommended) | 1 | From Chanzon 34-pack |
| Female pin header strips | As needed | From Glarks 120-pack |
| M3 standoffs, nuts, screws | As needed | From ZYAMY 150-pack |
| Breadboard | 1 | For prototyping phase |
| LEDs, resistors | As needed | From assortments on hand |

### Ordered
| Component | Amazon Link | Notes |
|---|---|---|
| EEMB 1100mAh LiPo pouch 603449 (4-pack) | https://www.amazon.com/EEMB-1100mAh-Battery-Rechargeable-Connector/dp/B08VRYS8FT | 51×34×6mm flat; 3.7V; JST-PHR-02; built-in PCM protection; verify polarity before connecting |
| TP4056 + boost combined module (6-pack) | https://www.amazon.com/Battery-Charger-Discharge-Integrated-Lithium/dp/B098989NRZ | 33×23mm; charges LiPo and boosts to 5V out; VIN+ accepts solar input; verify SUNYIMA panel voltage under load |
| Adafruit LTR-390 UV sensor | https://www.amazon.com/LTR390-UV-Light-Sensor-Stemma/dp/B0BPR31P59 | I2C; native ESPHome `ltr390` platform; replaces discontinued VEML6075 |
| Waveshare 2.13" e-ink display (V4, SSD1680) | https://www.amazon.com/waveshare-2-13inch-HAT-Compatible-Resolution/dp/B071S8HT76 | Verify V4 at checkout; partial refresh; ESPHome supported |
| Tactile pushbutton assortment | https://www.amazon.com/QTEATAK-Momentary-Tactile-Button-Assortment/dp/B07VQF8P2Y | 200 pcs, 6×6mm through-hole |
| JST 2-pin connector pairs (22AWG) | https://www.amazon.com/RGBZONE-20Pairs-Connector-Cable-Fellow/dp/B013WTV270 | Solar panel to TP4056+boost VIN+ pad; verify pitch at build time or solder direct |

---

## MQTT Component Name
`hiking-monitor`

Topics:
- `jctsh/components/hiking-monitor/data`
- `jctsh/components/hiking-monitor/log`
- `jctsh/components/hiking-monitor/heartbeat`

---

## Future Projects — Related

### JCTsh Hiking Health Monitor (LilyGO T-WATCH-S3 Plus)

During Phase 1 planning, health sensing capabilities (heart rate, SpO2, skin temperature, step counting/activity) were evaluated as potential additions to the hiking monitor. The conclusion was that these metrics require reliable wrist skin contact, which conflicts with the hiking monitor's clip-on environmental sensor form factor.

The natural solution is a dedicated wrist-worn companion device. The **LilyGO T-WATCH-S3 Plus** (~$60) is the recommended platform:

- ESP32-S3 — same ecosystem as all JCTsh components
- MAX30102 heart rate and SpO2 sensor — integrated, wrist-mounted, skin contact solved
- MPU9250 9-axis IMU — accelerometer, gyroscope, magnetometer; step counting and activity detection
- Wi-Fi and Bluetooth 5.0
- 600mAh LiPo with charging controller
- AMOLED display
- Programmable via Arduino IDE or ESP-IDF

**Integration architecture (planned):** Publishes health readings to `jctsh/components/hiking-health/data` on home WiFi reconnect, using the standard environmental payload pattern. Health fields (`heart_rate_bpm`, `spo2_pct`, `steps`, `skin_temp_f`) added to `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md` schema when the project begins. Google Sheets archive receives both environmental and health data streams, joinable by timestamp.

**Combined data picture:** hiking monitor environmental data + hiking health monitor physiological data + GaiaGPS GPS track — all correlated by timestamp in a single Sheets workbook.

**Status:** Identified and deferred May 2026. Plan as a separate JCTsh component project using the standard planning pattern when ready. No parts ordered.

---

### JCTsh Air Quality Monitor (Standalone Companion Device)

During Phase 1 planning, air quality sensing (PM2.5, VOC, NOx) was evaluated as a potential addition to the hiking monitor. The conclusion was that the PM sensor fan draws ~100mA — comparable to the entire rest of the device — and requires physical air intake/exhaust ports that complicate the enclosure. A separate device is the correct solution.

**Recommended platform:** ESP32 (on hand) + Sensirion SEN55 — PM1.0, PM2.5, PM4.0, PM10, VOC index, NOx index all in one I2C module. Same onboard flash logging and WiFi replay pattern as the hiking monitor. Duty-cycle the fan via GPIO transistor to reduce average draw.

**Motivation — Tucson-specific:** wildfire smoke, haboobs, trail dust (silica), and summer ozone are real and variable. A fixed AQI station miles away does not capture actual trail exposure.

**Status:** Identified and deferred May 2026. Build the hiking monitor first. Plan as a separate JCTsh component project when ready. No parts ordered.

---

### JCTsh Hiking Observations Pipeline (Software Only)

During Phase 1 planning, a voice observation capture system was designed for recording field observations during hikes. No ESP32 or hardware required — entirely a phone + Google Apps Script + Sheets pipeline.

**How it works:**
1. Speak an observation into Google Recorder beginning with the keyword "observation" (e.g. "observation, saw first saguaro bloom of the season")
2. After the hike, share the transcript to Google Docs (one tap) — or automatically via Tasker in the future
3. Google Apps Script processor detects the keyword, extracts text, assigns categories, archives to the Hiking Observations sheet in the Google Sheets workbook
4. Correlated to environmental sensor data and GaiaGPS track by timestamp

**Category classification:** Automatic — Apps Script scans transcript text against a keyword taxonomy (vegetation, wildlife, weather, visibility, sky, air_quality, trail, subjective). Multiple categories per observation. No manual tagging.

**Implementation path:**
- **Path A (starting point):** Manual share transcript to Google Docs after hike → Apps Script processes → Sheets. Reliable, no Tasker dependency, includes a deliberate review moment.
- **Path B (future enhancement):** Tasker auto-publishes to MQTT when phone reconnects to home WiFi → same downstream processing. Eliminates manual step. Requires testing Tasker access to Google Recorder content provider on Pixel 10 Pro before committing.

Build Path A first; upgrade to Path B once proven.

**Data architecture:** Separate `Hiking Observations` sheet in the same Google Sheets workbook. Timestamp is the join key to Environmental Data sheet and GaiaGPS track. Full architecture defined in `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`.

**Combined data picture:** Where you were (GaiaGPS) + what conditions were (hiking monitor) + what you observed (observations pipeline) — all correlated by timestamp.

**Status:** Identified and deferred May 2026. No hardware or software to purchase. Plan as a separate JCTsh project when ready — start with Path A after the hiking monitor data pipeline is built, since it shares the same Apps Script and Sheets infrastructure.

---

## Open Questions for Phase 2

1. **Enclosure design:** What 3D printing approach — design from scratch or adapt an existing open-source Stevenson screen enclosure? Are STL files available for similar devices?
2. **LTR-390 glazing:** Does the UV sensor need a UV-transparent window if recessed in the enclosure, or can it be flush-mounted on the top face without glazing?
3. **Waveshare display connection:** The V4 HAT form factor is designed for Pi GPIO — confirm SPI wiring to ESP32 DevKitC-32 GPIO pins before finalizing enclosure layout.
4. **ESPHome custom component scope:** Confirm onboard flash write/read/replay logic can be contained in a single custom component without requiring full Arduino framework migration.
5. **Google Apps Script deployment:** Confirm Apps Script web app URL pattern and secret key approach before Node-RED flow is built.
6. **TP4056+boost solar input:** Verify SUNYIMA panel voltage under load is within module's acceptable input range before finalizing solar wiring.
7. **LiPo connector polarity:** Verify JST polarity match between EEMB pouch and TP4056+boost module before first connection.
8. **Parts inventory update:** Add received components to `jctsh-parts-inventory.md` at appropriate Claude Code step. Also add 18650 cells confirmed on hand.

---

## Phase 2 Entry Criteria

Phase 1 is complete. Phase 2 (Hardware Selection and Enclosure Layout) begins when:
- All ordered parts are received
- LiPo connector polarity is verified
- Enclosure size target is confirmed with parts in hand
- Waveshare display SPI wiring to ESP32 DevKitC-32 is verified compatible

---

*Phase 1 completed through interactive planning session, May 2026. Battery decision revised to LiPo pouch in v2.1. Health sensing and air quality future project notes added in v2.2 and v2.3. Hiking observations future project note added in v2.4. All feature decisions resolved. Data pipeline build included in project scope. All components ordered.*