# JCTsh Hiking Monitor — Phase 1 Planning Document
**Author:** Joseph C Thomas (JCT)
**Purpose:** Phase 1 discovery and feature decisions for the JCTsh hiking environmental sensor (hiking-monitor component). Covers feature analysis, all resolved decisions, deferred items, BOM, shopping list, and open questions for Phase 2.
**Version:** 2.0
**Version description:** Complete rewrite from v1.0 brainstorm. All features resolved through interactive planning session. Incorporates JCTsh-Environmental-Data-Architecture.md standards, parts inventory, and confirmed hardware decisions. Ready for Phase 2 hardware selection.
**Project:** JCTsh Hiking Monitor
**Status:** Phase 1 Complete — Ready for Phase 2
**Related files:** `README.md`, `CLAUDE.md`, `ENVIRONMENT.md`, `JCTsh-Environmental-Data-Architecture.md`, `JCTsh-Build-Standards.md`, `JCTsh-Component-Planning-Pattern.md`, `jctsh-parts-inventory.md`

---

## What This Component Is

A portable, body-carried environmental sensor for use on hikes in the Tucson area and one annual backpacking trip. Measures temperature, humidity, barometric pressure, and UV index in real time. Displays readings locally on an e-ink display. Logs timestamped readings to onboard flash storage during the hike. Syncs automatically with JCTsh on return home via WiFi — publishing to the standard environmental data pipeline (MQTT → Node-RED → Google Sheets).

This component is part of the JCTsh environmental sensor family defined in `JCTsh-Environmental-Data-Architecture.md`. It must conform to the standard environmental message payload and MQTT topic convention.

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

**Field mode (during hike):** No WiFi, no MQTT. Reads sensors every 2 minutes, timestamps each reading using NTP-synced system clock, stores to LittleFS onboard flash. Display updates every 2 minutes. Button wakes display on demand.

**Home mode (in cradle):** Connected to JCTnet1 WiFi. Publishes stored hike readings to MQTT in sequence using original hike timestamps. Node-RED wildcard handler routes to Google Sheets automatically. Publishes 5-minute heartbeat per JCTsh standards.

**GaiaGPS correlation:** GaiaGPS tracks every hike independently on the Pixel 10 Pro XL. Sensor readings are correlated to GPS track by matching timestamps after the hike. No GPS hardware on the device. No phone hotspot required during the hike.

**Clock synchronization:** Device stays powered in charging cradle between hikes, connected to WiFi, clock synced via NTP. Clock remains accurate across any hike duration — no RTC hardware needed.

---

## Resolved Decisions

### Sensors
| Sensor | Decision | Rationale |
|---|---|---|
| Temperature / Humidity / Pressure | BME280 (genuine GY-BME280) | On hand (3 spares); proven in JCTsh; native ESPHome support |
| UV Index | VEML6075 (Adafruit breakout) | Standard payload field `uv_index` already defined in architecture; I2C alongside BME280; native ESPHome support; must face open sky — enclosure design must accommodate |

### Microcontroller
| Decision | Rationale |
|---|---|
| ESP32 DevKitC-32 (38-pin, CP2102, USB-C) | On hand (2 available); consistent with JCTsh ecosystem |
| ESPHome firmware | Required per CLAUDE.md for all future ESP32 components |
| One custom C++ ESPHome component | Required for LittleFS offline storage and WiFi replay — the only part ESPHome cannot handle declaratively |

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
| 18650 LiPo cell | On hand; robust for field use |
| AEDIKO charger + holder module | On hand (10 pairs); handles charging and power output |
| Micro USB charging port — external | Only charging port visible on enclosure exterior |
| USB-C (ESP32) — internal only | Used for initial flash and emergency recovery only; OTA handles all subsequent firmware updates |
| JST 2-pin connector — external | Solar panel input to AEDIKO VIN+ pad; used for backpacking trips |
| Voltage divider to ESP32 ADC | Battery voltage monitoring; maps to approximate charge level; no fuel gauge IC needed |
| No display of battery level | Battery life between charges is not a concern for day hikes; voltage divider data still logged in MQTT payload as `battery_v` |

### Storage and Logging
| Decision | Rationale |
|---|---|
| LittleFS onboard flash | Trivially small data volume (~36KB per 6-hour hike); no SD card hardware needed |
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
| No GPS hardware on device | GaiaGPS on Pixel 10 Pro XL tracks every hike independently; phone always carried |
| No phone hotspot during hike | Not needed; sensor data and GPS track are independent streams correlated by timestamp after the hike |
| Timestamp correlation | Each sensor reading timestamp matched to nearest GaiaGPS trackpoint timestamp after hike; at 2.5 mph and NTP-synced clock, position accuracy is well within acceptable range |

### lat/lon Fields
| Decision | Rationale |
|---|---|
| `"lat": null, "lon": null` in all hiking readings | No GPS on device; JSON null is unambiguous and filterable in Sheets; avoids confusion with real coordinates including 0,0 (Gulf of Guinea) |

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
| VEML6075 on top face | Must see open sky; separate from shielded BME280 port |
| Micro USB port external | Charging access |
| JST connector external | Solar panel connection |
| USB-C internal | Emergency reflash only |
| Single button on side | Display wake |
| Carabiner bail or loop at top | Attachment point |
| Target footprint | ~70mm × 45mm × 30mm (matchbox size) — 18650 cell is dominant constraint |

### Charging Cradle
| Decision | Rationale |
|---|---|
| Simple 3D-printed stand | Holds device upright with Micro USB connected; device stays on between hikes; NTP sync maintained |

### Solar Charging (Backpacking)
| Decision | Rationale |
|---|---|
| JST connector on enclosure routes to AEDIKO VIN+ | Solar input already supported by AEDIKO module; SUNYIMA panels (5.5V, 80mA) on hand — 10 units |
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
| Google Sheet | Environmental archive spreadsheet with standard column schema from JCTsh-Environmental-Data-Architecture.md |
| Google Apps Script web app | JavaScript REST endpoint deployed from the Sheet; accepts JSON POST; appends one row; authenticated via secret key in URL |
| Node-RED wildcard handler flow | Subscribes to `jctsh/components/+/data`; computes derived fields (dew_point_f, heat_index_f); POSTs to Apps Script; logs success/failure |
| Node-RED environment variables | Apps Script URL and secret key — not in source control |

### Deferred Features
| Feature | Status |
|---|---|
| Aspiration fan (forced airflow over BME280) | Deferred to Phase 2+ — evaluate temperature accuracy first; may not be needed |
| UV sensor enclosure glazing | Deferred to enclosure design — VEML6075 may need fused quartz or UV-transparent window if recessed |
| Deep sleep implementation | Deferred to firmware phase — implement after basic operation confirmed; significant battery life improvement for backpacking |
| Solar panel clip/mount design | Deferred to enclosure design phase |
| Compass / magnetometer | Not needed — phone handles navigation |
| Bluetooth / real-time GaiaGPS feed | Not needed — timestamp correlation approach is cleaner |
| VOC / gas sensor | Not relevant — open air hiking environment |
| Touchscreen | Not needed |
| LoRa radio | Not needed — Pixel satellite messaging handles emergency comms |

---

## Standard Environmental Payload

Conforms to `JCTsh-Environmental-Data-Architecture.md`. Fields sent by this device:

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

`lat` and `lon` are always null for this device. They are included in the payload to satisfy the architecture's "always present" requirement while clearly signaling no GPS data. Filter on `lat IS NOT NULL` in Sheets queries to exclude hiking-monitor rows from location-based analysis.

Derived fields (`dew_point_f`, `heat_index_f`) computed by Node-RED, not sent by device.

---

## Bill of Materials

### On Hand
| Component | Qty | Notes |
|---|---|---|
| ESP32 DevKitC-32 (38-pin, CP2102, USB-C) | 1 | From hiBCTR 6-pack |
| BME280 (genuine GY-BME280) | 1 | From 3 spare units on hand |
| AEDIKO 18650 charger + holder module | 1 | From 10-pair inventory |
| 18650 LiPo cell | 1 | On hand — **update inventory in Claude Code instructions** |
| SUNYIMA mini solar panel (5.5V, 80mA) | 1 | From 10-unit inventory (backpacking use) |
| Perfboard (5×7cm recommended) | 1 | From Chanzon 34-pack |
| Female pin header strips | As needed | From Glarks 120-pack |
| M3 standoffs, nuts, screws | As needed | From ZYAMY 150-pack |
| Breadboard | 1 | For prototyping phase |
| LEDs, resistors | As needed | From assortments on hand |

### To Purchase
| Component | Amazon Link | Notes |
|---|---|---|
| VEML6075 UV sensor (Adafruit #3964) | https://www.amazon.com/Adafruit-VEML6075-Index-Sensor-Breakout/dp/B07JQ1VN5K | I2C, 3.3V/5V; native ESPHome support |
| Waveshare 2.13" e-ink display (V4, SSD1680) | https://www.amazon.com/waveshare-2-13inch-HAT-Compatible-Resolution/dp/B071S8HT76 | Verify V4 version at checkout; partial refresh; ESPHome supported |
| Tactile pushbutton assortment | https://www.amazon.com/QTEATAK-Momentary-Tactile-Button-Assortment/dp/B07VQF8P2Y | 200 pcs, 10 values, 6×6mm, through-hole; useful across all future JCTsh projects |
| JST 2-pin connector pairs (22AWG) | https://www.amazon.com/RGBZONE-20Pairs-Connector-Cable-Female/dp/B013WTV270 | Solar panel to AEDIKO VIN+ pad; verify pitch at order time or solder direct to pads |

---

## MQTT Component Name
`hiking-monitor`

Topics:
- `jctsh/components/hiking-monitor/data`
- `jctsh/components/hiking-monitor/log`
- `jctsh/components/hiking-monitor/heartbeat`

---

## Open Questions for Phase 2

1. **Enclosure design:** What 3D printing approach — design from scratch or adapt an existing open-source Stevenson screen enclosure? Are STL files available for similar devices?
2. **VEML6075 glazing:** Does the UV sensor need a UV-transparent window if recessed in the enclosure, or can it be flush-mounted on the top face without glazing?
3. **Waveshare display connection:** The V4 HAT form factor is designed for Pi GPIO — confirm SPI wiring to ESP32 DevKitC-32 GPIO pins before finalizing enclosure layout.
4. **ESPHome custom component scope:** Confirm LittleFS write/read/replay logic can be contained in a single custom component without requiring full Arduino framework migration.
5. **Google Apps Script deployment:** Confirm Apps Script web app URL pattern and secret key approach before Node-RED flow is built.
6. **Parts inventory update:** Add 18650 cells to `jctsh-parts-inventory.md` at appropriate Claude Code step.

---

## Phase 2 Entry Criteria

Phase 1 is complete. Phase 2 (Hardware Selection) begins when:
- Parts orders are placed and received
- Enclosure size target is confirmed
- Waveshare display SPI wiring to ESP32 DevKitC-32 is verified compatible

---

*Phase 1 completed through interactive planning session, May 2026. All feature decisions resolved. Data pipeline build included in project scope.*
