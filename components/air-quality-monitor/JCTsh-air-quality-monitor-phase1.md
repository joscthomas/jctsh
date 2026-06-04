# JCTsh Air Quality Monitor — Phase 1 Planning Document
**Author:** Joseph C Thomas (JCT)
**Purpose:** Phase 1 discovery and feature decisions for the JCTsh air quality monitor (air-quality-monitor component). Covers feature analysis, all resolved decisions, deferred items, BOM, and open questions for Phase 2.
**Version:** 1.1
**Version description:** BOM updated — SEN55, Adafruit #5964 adapter breakout, and JST GH 6-pin cable moved from To Order to Ordered. SEN55 5V power requirement noted; Adafruit breakout handles level shifting and boost. Open Question 1 (connector) removed — resolved by breakout board selection. Status updated to Parts Ordered.
**Project:** JCTsh Air Quality Monitor
**Status:** Phase 1 Complete — Parts Ordered — Ready for Phase 2
**Related files:** `README.md`, `CLAUDE.md`, `ENVIRONMENT.md`, `JCTsh-Environmental-Data-Architecture.md`, `JCTsh-Build-Standards.md`, `JCTsh-Component-Planning-Pattern.md`, `jctsh-parts-inventory.md`, `JCTsh-hiking-sensor-phase1.md`

---

## What This Component Is

A portable, clip-mounted air quality sensor carried on hikes alongside the hiking monitor. Measures PM1.0, PM2.5, PM4.0, PM10, VOC index, and NOx index in real time using a Sensirion SEN55 module. A single RGB LED provides immediate field awareness of PM2.5 air quality level. No display.

Logs timestamped readings to onboard flash storage during hikes (no WiFi). Syncs automatically with JCTsh on return home via WiFi — publishing to the existing environmental data pipeline built by the hiking sensor project (MQTT → Node-RED → Google Sheets). No new pipeline infrastructure required.

This component is part of the JCTsh environmental sensor family defined in `JCTsh-Environmental-Data-Architecture.md`. It must conform to the standard environmental message payload and MQTT topic convention.

---

## Hiking Context

This device is a companion to the hiking monitor. It clips to the Osprey hydration pack via carabiner — a separate, independent unit. It operates entirely independently of the hiking monitor; there is no inter-device communication.

- **Motivation:** Wildfire smoke, haboobs, trail dust (silica), and summer ozone are real and variable in the Tucson area. A fixed AQI station miles away does not capture actual trail exposure.
- **Carry:** Clip case with carabiner, attached to pack
- **Field feedback:** RGB LED driven by PM2.5 thresholds — Green (Good), Yellow (Moderate), Red (Unhealthy)
- **Data value:** Primarily post-hike analysis — full AQI dataset correlated to GPS track and environmental readings by timestamp in Google Sheets

---

## Architecture Overview

Identical operating mode pattern to the hiking monitor. See `components/hiking-sensor/` for the reference implementation. Claude Code must read those files and apply the same patterns — do not re-derive them.

**Field mode (during hike):** No WiFi, no MQTT. Reads sensors on duty-cycle interval, timestamps each reading using NTP-synced clock, stores to onboard flash. RGB LED updates on each reading cycle.

**Home mode (in cradle/charging):** Connected to JCTnet1 WiFi. Publishes stored hike readings to MQTT in sequence using original hike timestamps. Publishes 5-minute heartbeat per JCTsh standards.

**Data pipeline:** The environmental data pipeline (Google Sheets + Apps Script + Node-RED wildcard handler) is built as part of the hiking sensor project. The air quality monitor publishes to `jctsh/components/air-quality-monitor/data` — the existing Node-RED `jctsh/components/+/data` wildcard handler catches it automatically. No new pipeline work required.

**Timestamp correlation:** Same approach as hiking monitor — sensor readings correlated to GaiaGPS track and hiking monitor environmental readings by matching timestamps after the hike.

---

## Resolved Decisions

### Sensor
| Decision | Rationale |
|---|---|
| Sensirion SEN55 | PM1.0, PM2.5, PM4.0, PM10, VOC index, NOx index — all in one module. NOx included for ozone precursor awareness. Integrated fan + laser particle counter. I2C address 0x69 (fixed). Requires 5V power — handled by Adafruit #5964 adapter breakout. |
| Adafruit SEN54/SEN55 Adapter Breakout (#5964) | Provides JST GH connector interface to SEN55, level shifting, and onboard boost converter (5V at 100mA) — allows 3.3V ESP32 logic to drive the SEN55 without a separate 5V supply for the sensor. STEMMA QT / standard 0.1" header output to ESP32 I2C. |
| JST GH 6-pin cable | Connects SEN55 to Adafruit #5964 adapter. |

### Microcontroller
| Decision | Rationale |
|---|---|
| ESP32 DevKitC-32 (38-pin, CP2102, USB-C) | On hand (Bag 1, 1 remaining after hiking sensor allocation). Consistent with JCTsh ecosystem. |
| ESPHome firmware | Required per CLAUDE.md for all JCTsh ESP32 components. |
| Custom C++ ESPHome component | Required for SEN55 (no native ESPHome platform) and for LittleFS offline storage and WiFi replay — follows hiking monitor pattern exactly. |

### Field Output
| Decision | Rationale |
|---|---|
| RGB LED — PM2.5 threshold indicator | Single RGB LED module from Greekcreit sensor kit (Plastic Box). Immediate field awareness without display complexity. |
| No display | Data value is in post-hike analysis, not moment-to-moment reading. Simpler enclosure, lighter weight. |

**RGB LED threshold mapping:**

| Color | PM2.5 Range | EPA Category |
|---|---|---|
| Green | < 12 μg/m³ | Good |
| Yellow | 12–35 μg/m³ | Moderate |
| Red | > 35 μg/m³ | Unhealthy |

### Power
| Decision | Rationale |
|---|---|
| EEMB LiPo pouch 603449 (1100mAh) | On hand (Bag 7). Flat form factor suits clip case. Estimated runtime ~58–68 hours at ~13–15mA average draw — far exceeds any hike duration. |
| TP4056 + boost combined module | On hand (Bag 8). Same module as hiking monitor — charges LiPo and boosts to 5V out → ESP32 VIN. The Adafruit #5964 breakout provides its own internal boost for the SEN55; TP4056 output feeds ESP32 only. |
| JST solar port — external | Low cost to include at enclosure design stage; TP4056+boost module supports it natively. SUNYIMA panels on hand (Bag 6) for backpacking use. |
| Micro USB charging port — external | Charging access, same as hiking monitor. |

**Estimated power budget:**

| Consumer | Active | Duty-cycled Average |
|---|---|---|
| SEN55 fan + sensor | ~70mA | ~6mA (10s active per 2-min cycle) |
| SEN55 idle | ~5mA | ~5mA |
| ESP32 (light sleep) | ~80mA active | ~2mA average |
| RGB LED | negligible | negligible |
| **Total estimated** | — | **~13–15mA** |

### Carry and Enclosure
| Decision | Rationale |
|---|---|
| Separate clip case with carabiner | Independent of hiking monitor; clips to pack shoulder strap or sternum strap. |
| 3D-printed enclosure | Air intake and exhaust ports required for SEN55 fan airflow — custom enclosure is necessary. Light color PETG to minimize solar gain. |
| SEN55 approx. module size | 59mm × 37mm × 23mm — this is the dominant enclosure constraint. |

### Fan Power Management
Follows hiking monitor pattern. See `components/hiking-sensor/hiking_logger.h` and associated firmware. Claude Code applies the same duty-cycle approach — do not re-derive.

### Offline Logging and WiFi Replay
Follows hiking monitor pattern exactly. See `components/hiking-sensor/` for the reference implementation. Claude Code reads those files and applies the same LittleFS approach — do not re-derive.

### JCTsh Integration
| Decision | Rationale |
|---|---|
| MQTT topic: `jctsh/components/air-quality-monitor/data` | Standard environmental sensor family convention |
| MQTT topic: `jctsh/components/air-quality-monitor/log` | Standard log topic |
| MQTT topic: `jctsh/components/air-quality-monitor/heartbeat` | Standard heartbeat topic; home mode only |
| Node-RED wildcard handler catches data automatically | Existing `jctsh/components/+/data` subscription — no new Node-RED flow needed |
| Google Sheets archive | Existing pipeline; AQI fields already in schema |
| No SmartThings integration | No real-time state to expose |
| No Home Assistant integration | Not needed |
| Dedicated Mosquitto account | `air-quality-monitor` — per JCTsh-Build-Standards.md Section 2.7 |
| Watchdog | Standard JCTsh watchdog monitors heartbeat; alerts expected during hikes |

---

## Standard Environmental Payload

Conforms to `JCTsh-Environmental-Data-Architecture.md`. Fields sent by this device:

```json
{
  "component": "air-quality-monitor",
  "ts": "2026-06-03T09:15:00Z",
  "lat": null,
  "lon": null,
  "pm1_ug_m3": 4.2,
  "pm25_ug_m3": 11.8,
  "pm4_ug_m3": 13.1,
  "pm10_ug_m3": 14.0,
  "voc_index": 112,
  "nox_index": 18,
  "battery_v": 3.91,
  "rssi_dbm": -71
}
```

`lat` and `lon` are always null. `rssi_dbm` is 0 for field-mode readings (no WiFi at time of logging). Derived fields are not applicable to this payload. Temperature, humidity, and pressure are not included — those come from the hiking monitor.

---

## Bill of Materials

### On Hand
| Component | Qty | Location | Notes |
|---|---|---|---|
| ESP32 DevKitC-32 (38-pin, CP2102, USB-C) | 1 | Bag 1 | 1 remaining after hiking sensor |
| EEMB LiPo pouch 603449 (1100mAh) | 1 | Bag 7 | Verify polarity before connecting |
| TP4056 + boost combined module | 1 | Bag 8 | Same module as hiking monitor |
| RGB LED module | 1 | Plastic Box | From Greekcreit 37-module kit |
| SUNYIMA solar panel (5.5V, 80mA) | 1 | Bag 6 | Backpacking use only |
| Perfboard | 1 | Bag 9 | Size TBD at Phase 2 — SEN55 + adapter footprint is dominant constraint |
| Female pin header strips | As needed | Plastic Box | |
| M3 standoffs, nuts, screws | As needed | Plastic Box | |
| Resistors | As needed | Bag 17 | RGB LED current limiting |
| Breadboard | 1 | Bag 12 | Prototyping phase |
| Jumper wires | As needed | Plastic Box | |

### Ordered
| Component | Notes |
|---|---|
| Sensirion SEN55 | PM1.0/2.5/4.0/10, VOC, NOx. I2C address 0x69 (fixed). Integrated fan. ~59mm × 37mm × 23mm. Requires 5V — supplied by Adafruit #5964 onboard boost. |
| Adafruit SEN54/SEN55 Adapter Breakout (#5964) | JST GH connector, onboard 5V boost, level shifting, STEMMA QT output. https://www.adafruit.com/product/5964 |
| JST GH 6-pin cable | Connects SEN55 to Adafruit #5964 adapter. |

---

## MQTT Component Name
`air-quality-monitor`

Topics:
- `jctsh/components/air-quality-monitor/data`
- `jctsh/components/air-quality-monitor/log`
- `jctsh/components/air-quality-monitor/heartbeat`

---

## Deferred Features

| Feature | Status |
|---|---|
| Bluetooth / real-time data share to hiking monitor display | Evaluated and deferred — BLE pairing state and reconnect logic add field failure modes; data value is in post-hike record; enclosure and firmware complexity not justified |
| Deep sleep between readings | Deferred to firmware phase — implement after basic operation confirmed; consistent with hiking monitor approach |
| Solar panel mount/clip design | Deferred to enclosure design phase |
| NOx threshold LED indicator | VOC index covers field awareness adequately; NOx is more useful in post-hike Sheets analysis |

---

## Open Questions for Phase 2

1. **SEN55 ESPHome component:** Confirm whether a community ESPHome external component exists for SEN55 before committing to writing one from scratch. If available and maintained, use it.
2. **Fan transistor:** Confirm NPN transistor (2N2222 or equivalent) available in Greekcreit kit or resistor/component assortment for fan duty-cycle switching before finalizing BOM.
3. **Perfboard size:** Determine required perfboard footprint after SEN55 + Adafruit adapter physical dimensions are confirmed with parts in hand.
4. **Enclosure intake/exhaust:** SEN55 specifies intake and exhaust port placement — confirm orientation requirements before enclosure design begins.
5. **LiPo polarity:** Verify JST connector polarity between EEMB pouch and TP4056+boost module before first connection (same requirement as hiking monitor).
6. **Parts inventory update:** Add SEN55, Adafruit adapter, and JST cable to `jctsh-parts-inventory.md` at the appropriate Claude Code step.

---

## Phase 2 Entry Criteria

Phase 1 is complete. Phase 2 (Hardware Selection) begins when:
- SEN55, Adafruit #5964 adapter, and JST GH cable received
- Fan transistor availability confirmed (on hand or to order)
- Hiking sensor build complete (this project inherits its pipeline and patterns)

---

## Implementation Note for Claude Code

The firmware architecture for this component — LittleFS offline logging, WiFi replay, fan duty-cycle via transistor, custom C++ ESPHome component, heartbeat, MQTT log format, watchdog — follows the hiking monitor pattern. Read `components/hiking-sensor/` files before beginning any firmware work. Apply those patterns directly. Do not re-derive them from first principles.

---

*Phase 1 completed June 2026. Parts ordered June 2026. Build begins after hiking sensor is complete.*
