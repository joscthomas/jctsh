# JCTsh Air Quality Monitor — Phase 1 Planning Document
**Author:** Joseph C Thomas (JCT)
**Purpose:** Phase 1 discovery and feature decisions for the JCTsh air quality monitor (air-quality-monitor component). Covers feature analysis, all resolved decisions, deferred items, BOM, and open questions for Phase 2.
**Version:** 1.2
**Version description:** Corrected SEN54→SEN55 inventory mislabel; clarified hiking-monitor dependency is architectural (firmware pattern, field-proven) not physical (not gated by hiking-monitor's enclosure). Resolved ESPHome sen5x native component question and SEN5x intake/exhaust orientation research (flagged low-confidence — source PDF unreadable). Closed Phase 3 (timeout/timer logic decision — match hiking-monitor, explicitly avoid CARD-0045's `wifi.ap:`/`reboot_timeout` bug). Moved remaining physical checks (perfboard footprint, LiPo polarity) from Phase 2 planning blockers to Phase 4 bench steps.
**Project:** JCTsh Air Quality Monitor
**Status:** Phase 1–3 Complete — Ready for Phase 4
**Related files:** `README.md`, `CLAUDE.md`, `ENVIRONMENT.md`, `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`, `JCTsh-Build-Standards.md`, `JCTsh-Component-Planning-Pattern.md`, `jctsh-parts-inventory.md`, `JCTsh-hiking-monitor-phase1.md`

---

## What This Component Is

A portable, clip-mounted air quality sensor carried on hikes alongside the hiking monitor. Measures PM1.0, PM2.5, PM4.0, PM10, VOC index, and NOx index in real time using a Sensirion SEN55 module. A single RGB LED provides immediate field awareness of PM2.5 air quality level. No display.

Logs timestamped readings to onboard flash storage during hikes (no WiFi). Syncs automatically with JCTsh on return home via WiFi — publishing to the existing environmental data pipeline built by the hiking monitor project (MQTT → Node-RED → Google Sheets). No new pipeline infrastructure required.

This component is part of the JCTsh environmental sensor family defined in `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`. It must conform to the standard environmental message payload and MQTT topic convention.

---

## Hiking Context

This device is a companion to the hiking monitor. It clips to the Osprey hydration pack via carabiner — a separate, independent unit. It operates entirely independently of the hiking monitor; there is no inter-device communication.

- **Motivation:** Wildfire smoke, haboobs, trail dust (silica), and summer ozone are real and variable in the Tucson area. A fixed AQI station miles away does not capture actual trail exposure.
- **Carry:** Clip case with carabiner, attached to pack
- **Field feedback:** RGB LED driven by PM2.5 thresholds — Green (Good), Yellow (Moderate), Red (Unhealthy)
- **Data value:** Primarily post-hike analysis — full AQI dataset correlated to GPS track and environmental readings by timestamp in Google Sheets

---

## Architecture Overview

Identical operating mode pattern to the hiking monitor. See `components/hiking-monitor/` for the reference implementation. Claude Code must read those files and apply the same patterns — do not re-derive them.

**Field mode (during hike):** No WiFi, no MQTT. Reads sensors on duty-cycle interval, timestamps each reading using NTP-synced clock, stores to onboard flash. RGB LED updates on each reading cycle.

**Home mode (in cradle/charging):** Connected to JCTnet1 WiFi. Publishes stored hike readings to MQTT in sequence using original hike timestamps. Publishes 5-minute heartbeat per JCTsh standards.

**Data pipeline:** The environmental data pipeline (Google Sheets + Apps Script + Node-RED wildcard handler) is built as part of the hiking monitor project. The air quality monitor publishes to `jctsh/components/air-quality-monitor/data` — the existing Node-RED `jctsh/components/+/data` wildcard handler catches it automatically. No new pipeline work required.

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
| ESP32 DevKitC-32 (38-pin, CP2102, USB-C) | On hand (Bag 1, 1 remaining after hiking monitor allocation). Consistent with JCTsh ecosystem. |
| ESPHome firmware | Required per CLAUDE.md for all JCTsh ESP32 components. |
| Custom C++ ESPHome component | **Corrected 2026-07-09:** SEN55 itself needs no custom component — ESPHome's native `sen5x` sensor platform supports it directly over I2C. A custom component is still required for onboard flash storage and WiFi replay — follows hiking monitor pattern exactly, unrelated to the sensor driver. |

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
| EEMB LiPo pouch 603449 (1100mAh) | On hand (Bag 7). Flat form factor suits clip case. Estimated runtime ~58–68 hours at ~13–15mA average draw — far exceeds any hike duration. **Superseded 2026-08-19 (Claude Code instructions v1.1):** this estimate never accounted for the boost module's own quiescent draw (same blind spot CARD-0026 found on hiking-monitor, ~22.6mA measured there); with the boost module as planned here, real runtime likely would have been closer to ~30 hours. See the instructions doc's recalculated ~73–85h estimate under the LDO decision below. |
| TP4056 + boost combined module | **Superseded 2026-08-19** — boost stage no longer used; replaced with a direct LiPo-to-LDO architecture (MCP1700, Bag 32) per `JCTsh-Build-Standards.md` §2.14 point 7, decided while starting Phase 5 execution (CARD-0012). TP4056 half (charging, on hand, Bag 8) is unchanged and still used. See `air-quality-monitor-claude-code-instructions.md` v1.1 Hardware Context for the full reasoning. The Adafruit #5964 breakout's own internal 5V boost for the SEN55 is unaffected either way — it never depended on this module. |
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
| 3D-printed enclosure | **Material corrected 2026-08-20** — white ASA for final print (matches hiking-monitor's own upgrade for Tucson UV/heat resistance), not PETG as originally stated; PLA still used for the test-fit print. Houses ESP32, perfboard, LiPo, LDO, TP4056, inline switch. **No custom intake/exhaust venting needed** (superseded 2026-08-20, see SEN55 mounting row below) — the only enclosure-wall penetration required is a small cable pass-through for the SEN55's JST-GH cable, same pattern as the solar JST exit hole. |
| **SEN55 external mount (decided 2026-08-20)** | The SEN55 module has its own sealed metal housing with an integrated fan shield (Sensirion's own design) — it does not need the JCTsh enclosure to provide airflow. 3M double-sided foam tape (on hand, Plastic Box) mounts the SEN55 directly to the smooth exterior surface of the 3D-printed enclosure, connected to the internal Adafruit #5964 adapter via the existing 100mm JST-GH cable (Bag 25) through a small pass-through hole. This removes the SEN55 module (59mm × 37mm × 23mm — previously "the dominant enclosure constraint") from the internal footprint entirely; only the small adapter board needs to fit inside alongside the perfboard. |

### Fan Power Management
Follows hiking monitor pattern. See `components/hiking-monitor/hiking_logger.h` and associated firmware. Claude Code applies the same duty-cycle approach — do not re-derive.

### Offline Logging and WiFi Replay
Follows hiking monitor pattern exactly. See `components/hiking-monitor/` for the reference implementation. Claude Code reads those files and applies the same onboard flash logging approach — do not re-derive.

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
| Timeout/timer logic | **Superseded 2026-08-20** (replaces the 2026-07-09 decision below) — the original reasoning assumed home mode only happens docked/charging at home, USB-powered. That's false: the solar JST input and USB charging both share the dock-detect (`IN+`) signal with the physical home dock, so dock-detect can go HIGH mid-hike, on battery, with no home WiFi in range. Rather than a bare `reboot_timeout` (which CARD-0045 found unreliable alongside a `wifi.ap:` fallback block), **field duty-cycle logging now runs unconditionally, independent of dock-detect state** — dock-detect HIGH only triggers a background WiFi connection *attempt*, gated to a bounded window (target: 2 minutes) before disabling the WiFi radio (`wifi.disable`) rather than retrying indefinitely, then re-attempting periodically (target: 15–20 minutes) for as long as dock-detect stays HIGH. Logging only pauses once WiFi **and** MQTT actually connect — successfully, whether via `JCTnet1` at home or the Pixel hotspot in the field (see the new hotspot fallback network below) — at which point the device behaves exactly like hiking-monitor's home mode (drain the SPIFFS backlog, then publish live). No hard cap on the number of periodic retry cycles — only on how long each individual attempt window runs, since there's no cost to trying again later if the panel/USB is still connected. Exact implementation (interval/lambda structure) is a Phase 4 task, not specified further here.<br><br>**Original 2026-07-09 decision (superseded):** no elaborate custom WiFi/MQTT connect-timeout logic — match hiking-monitor's existing approach (no explicit `reboot_timeout` override), which is reasonable here since home mode only happens while docked/charging (USB-powered, not battery-critical). Explicitly do not inherit hiking-monitor's `wifi.ap:` + `reboot_timeout` bug interaction (CARD-0045) — when writing the actual YAML in Phase 4, confirm whether an `ap:` fallback block is actually needed for this device before including one; if included, be aware the default timeout may not function as expected. |
| Hotspot fallback network | **Added 2026-08-20** — since USB charging (and solar) can now trigger dock-detect away from home, add the same Pixel hotspot as a second WiFi network, matching hiking-monitor's `secrets.yaml.template` pattern (`hotspot_ssid`/`hotspot_password`). Without this, a field dock-detect trigger had no real network to find and would always exhaust its retry window. |
| MQTT broker hostname | **Corrected 2026-08-20** — `secrets.yaml.template` currently points `mqtt_broker` at `pi1.local`, which only resolves on the home LAN. Now that field connections via the hotspot are a real path, this must be `jctsh.duckdns.org` (the same DuckDNS + port-forward path hiking-monitor already uses, per `CLAUDE.md`'s MQTT internet-exposure section) so a field-mode MQTT publish can actually reach the broker. |

---

## Standard Environmental Payload

Conforms to `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`. Fields sent by this device:

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

**Updated 2026-08-19** — SEN55/adapter/cable moved here from "Ordered" (arrived and allocated 2026-07-01/07-09, this table just hadn't caught up); BC547B, MCP1700 LDO, and the inline power switch added (all decided/found this session, see `air-quality-monitor-claude-code-instructions.md` v1.1). TP4056+boost row split — boost stage no longer used, see the LDO row.

| Component | Qty | Location | Notes |
|---|---|---|---|
| ESP32 DevKitC-32 (38-pin, CP2102, USB-C) | 1 | Bag 1 | 1 remaining after hiking monitor |
| Sensirion SEN55 (SparkFun SEN-23715) | 1 | Plastic Box | PM1.0/2.5/4.0/10, VOC, NOx. I2C address 0x69 (fixed). Integrated fan. ~59mm × 37mm × 23mm. Requires 5V — supplied by Adafruit #5964 onboard boost. |
| Adafruit SEN54/SEN55 Adapter Breakout (#5964) | 1 | Bag 25 | JST GH connector, onboard 5V boost, level shifting, STEMMA QT output. |
| JST GH 1.25mm 6-pin cable (100mm) | 1 | Bag 25 | Connects SEN55 to Adafruit #5964 adapter |
| EEMB LiPo pouch 603449 (1100mAh) | 1 | Bag 7 | Verify polarity before connecting |
| TP4056 + boost combined module | 1 | Bag 8 | Charging half only — boost stage unused, see MCP1700 row |
| MCP1700-3302E/TO LDO | 1 | Bag 32 | Direct LiPo-to-3.3V, replaces the boost stage per `JCTsh-Build-Standards.md` §2.14 point 7 |
| BC547B NPN transistor | 1 | Music Response bin | SEN55 power-gate, low-side switch (GPIO27) |
| Inline power switch (Gebildet SS12D10) | 1 | Bag 23 | From the slide-switch assortment — true transport/storage off, wired directly in the battery+ path |
| RGB LED module | 1 | Plastic Box | From Greekcreit 37-module kit |
| SUNYIMA solar panel (5.5V, 80mA) | 1 | Bag 6 | Backpacking use only |
| Perfboard | 1 | Bag 9 | **Moved 2026-08-20:** size TBD at Step 9 (perfboard transfer), not Step 3 — measuring before there's a real layout to size against was premature. Working assumption: same 5×7cm Chanzon FR4 hiking-monitor uses will probably work; SEN55 + adapter footprint is the dominant constraint to confirm/adjust that against. |
| Female pin header strips | As needed | Plastic Box | |
| M3 standoffs, nuts, screws | As needed | Plastic Box | |
| Resistors | As needed | Bag 17 | SEN55 gate base/pull-down, both voltage dividers — **not** the RGB LED, confirmed 2026-08-19 to be a KY-016 module with its own onboard current-limiting resistors, see `wiring.md` |
| Breadboard | 1 | Bag 12 | Prototyping phase |
| Jumper wires | As needed | Plastic Box | |

### Ordered

Nothing currently on order — everything needed is on hand (see above).

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

1. ~~SEN55 ESPHome component~~ **Confirmed 2026-07-09, high confidence:** ESPHome has a **native, built-in `sen5x` sensor platform** (esphome.io/components/sensor/sen5x/) supporting SEN50/SEN54/SEN55 directly over I2C — no custom component needed for the sensor itself. Source: ESPHome's own official documentation page. Simplifies the original assumption in this doc's Hardware Context — a custom component is still needed for the onboard-flash-logging/WiFi-replay pattern (inherited from hiking-monitor), but that's unrelated to reading the sensor.
2. **Fan/SEN55 power-gate transistor bench test — moved to Phase 4.** On-hand BC547B NPN (50 in stock, Music Response bin, 0.1A/45V rated) should comfortably cover the SEN55's ~70mA duty-cycled power draw on paper — same substitution pattern as remote-temp-sensor-01's BC557B. This is a calculation, not a measurement — confirmed with an actual bench test (transistor switching the SEN55, multimeter check) as a Phase 4 bench step, not a blocking Phase 2 planning item.
3. ~~Perfboard size — moved to Phase 4.~~ **Moved again 2026-08-20, to Step 9 (perfboard transfer), and scope narrowed:** with the SEN55 external-mount decision below, the SEN55 module itself (59mm × 37mm × 23mm) is no longer part of the internal footprint question at all — only the small Adafruit #5964 adapter needs to fit inside alongside the perfboard. Working assumption: the same 5×7cm Chanzon FR4 board hiking-monitor uses will work, confirmed/adjusted at Step 9 per `wiring.md`'s measurement procedure.
4. ~~Enclosure intake/exhaust~~ **Resolved 2026-08-20 — moot, not just deferred.** SEN55 external-mount decision (see Carry and Enclosure section above) means the sensor's own sealed metal housing/fan shield handles its airflow directly from ambient air — it's mounted outside the JCTsh enclosure via 3M tape, not inside it. No custom intake/exhaust venting needed in the enclosure at all; the low-confidence Sensirion orientation research below no longer needs re-verification for this build. (Original finding kept for reference, not deleted: WebSearch reported, attributed to Sensirion's Mechanical Design and Assembly Guidelines for SEN5x — two air inlets + one air outlet must stay unobstructed and directly coupled to ambient air; inlets positioned **above** the outlet; opening face ideally pointing **downward**; avoid strong external airflow across openings. **Caveat: both direct PDF fetch attempts failed** — this summary came from WebSearch's own synthesis of search-result snippets, not from reading Sensirion's primary document.)
5. **LiPo polarity — moved to Phase 4.** Verify JST connector polarity between EEMB pouch and TP4056+boost module before first connection (same requirement as hiking monitor) — a Phase 4 bench step, performed right before first battery connection.
6. ~~Parts inventory update~~ **Done 2026-07-09, medium confidence:** SEN55 (corrected from mislabeled "SEN54"), Adafruit adapter, and JST cable all confirmed in `jctsh-parts-inventory.md`. The "SEN-23715 = SEN55" correction is confirmed against SparkFun's own product listing for that part number — but the physical item in the Plastic Box hasn't been checked against its label/silkscreen to confirm it's actually SEN-23715 and not something else. Worth a 30-second physical glance next time the box is open.

**Phase 3 status: Complete.** Full Phase 3 Required Checklist (MQTT topic naming, MQTT account, heartbeat, message logging, watchdog, SmartThings type+path, LED indicators, timeout/timer logic) resolved — see "JCTsh Integration" table above and the timeout decision (2026-07-09, matches hiking-monitor's approach, explicitly does not inherit the CARD-0045 `wifi.ap:`/`reboot_timeout` bug). Bench/install boundary is a Phase 4 concern, not a Phase 3 gap.

---

## Phase 2 — Status: Effectively Complete

- SEN55, Adafruit #5964 adapter, and JST GH cable received — **done** (confirmed 2026-07-09; `jctsh-parts-inventory.md`'s SparkFun SEN-23715 entry was mislabeled "SEN54," corrected — it is the genuine SEN55, matching this plan's requirement including NOx)
- Fan/SEN55 power-gate transistor — likely satisfied by the on-hand BC547B NPN (50 in stock, 0.1A rated, covers the SEN55's ~70mA duty-cycled draw); formal bench confirmation **moved to Phase 4**
- **Hiking-monitor firmware architecture proven** (this project inherits its pipeline and patterns) — **done**, field-confirmed via CARD-0008 (2026-06-17 camping trip: hotspot connection, cellular MQTT reach, SPIFFS replay all working). This criterion is about the *firmware pattern* (onboard flash logging, WiFi replay, field/home mode), not the physical device — hiking-monitor's enclosure (CARD-0009) is a separate, unrelated deliverable and does **not** gate this project.
- Perfboard footprint measurement and LiPo/TP4056 polarity check — physical tasks, **moved to Phase 4** bench steps rather than treated as Phase 2 planning blockers

## Phase 3 — Status: Complete

See Phase 3 status note above (JCTsh Integration table, timeout decision). Ready for Phase 4.

---

## Implementation Note for Claude Code

The firmware architecture for this component — onboard flash logging, WiFi replay, fan/SEN55 duty-cycle via transistor, custom C++ ESPHome component (for logging/replay only — SEN55 itself uses ESPHome's native `sen5x` platform), heartbeat, MQTT log format, watchdog — follows the hiking monitor pattern. Read `components/hiking-monitor/` files before beginning any firmware work. Apply those patterns directly. Do not re-derive them from first principles.

---

*Phase 1 completed June 2026. Parts ordered June 2026, all received and confirmed correct (2026-07-09). Phases 1–3 complete as of 2026-07-09. Ready for Phase 4 (Claude Code instructions) — see `air-quality-monitor-claude-code-instructions.md`.*
