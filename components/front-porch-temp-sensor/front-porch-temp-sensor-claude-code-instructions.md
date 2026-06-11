# JCTsh Front Porch Temp Sensor — Claude Code Instructions
**Author:** Joseph C Thomas (JCT)
**Purpose:** Step-by-step build instructions for the front-porch-temp-sensor component.
**Project:** JCT Smart Home (JCTsh)
**Version:** 1.1
**Version description:** Aligned with CLAUDE.md, JCTsh-Build-Standards.md v1.1, and Planning Pattern v1.6. Added: MQTT /log and /heartbeat topics, 5-minute heartbeat, Node-RED watchdog registration, dedicated Mosquitto account creation step, integration-notes.md and integration.md steps, pinout PNG requirement, SmartThings and LED Phase 3 decisions, all required documents per Section 7.1 Build Standards.
**Related files:** README.md, CLAUDE.md, JCTsh-Build-Standards.md, JCTsh-Parts-Inventory.md, components/garage-radar/

---

## Overview

The front-porch-temp-sensor monitors outdoor temperature, humidity, barometric pressure, and light level on the front porch. It sends push notifications to both household phones when the temperature rises above a configurable threshold while the front door is open during daylight hours. A reminder notification fires 15 minutes later if the door is still open. A clear notification fires when the temperature drops back below the threshold.

The primary use case: Robin wants to know when to close the front door before the house starts warming up.

---

## Working Pattern

Claude Code creates documentation and configuration files. Joseph follows those documents to perform physical assembly, wiring, flashing, and configuration outside of Claude Code. Joseph reports results back, and Claude Code updates documentation to reflect actual findings, deviations, and lessons learned. Do not proceed to the next step until Joseph confirms the current step is complete.

---

## Hardware Context

| Component | Detail |
|---|---|
| Microcontroller | ESP32 DevKitC-32, 38-pin, CP2102 USB-C (hiBCTR 6-pack) |
| Temperature/humidity/pressure sensor | BME280 breakout (Podazz 3-pack, I2C, 5V, onboard regulator) |
| Light sensor | BH1750 breakout (hiBCTR GY-302, I2C) |
| Firmware | ESPHome |
| Perfboard | Chanzon FR4, 5×7cm |
| Mounting | M3 brass standoffs — open standoff mount (no enclosure — location is sheltered under porch roof overhang) |
| Power | 5V USB wall charger + USB-A to USB-C cable, front porch outlet |
| Location | Front porch, under roof overhang — sheltered from rain and direct sun |
| LEDs | None — omitted from v1 (no status indication required for this location) |

**GPIO assignments:**
| GPIO | Assignment |
|---|---|
| GPIO21 | I2C SDA (shared — BME280 + BH1750) |
| GPIO22 | I2C SCL (shared — BME280 + BH1750) |

**I2C addressing:**
- BME280 default address: 0x76
- BH1750 default address: 0x23 (ADDR pin tied to GND)
- No conflict. No level shifter needed. Pull-up resistors included on breakout boards.

**BME280 wiring note:** The Podazz BME280 is labeled 5V and has an onboard voltage regulator. Power from ESP32 3.3V — do not use VIN/5V for this sensor.

**BMP280 counterfeit warning:** Some modules labeled "BME280" are actually BMP280 with no humidity sensor. ESPHome will report humidity as NaN. Validation step in Step 4 confirms genuine BME280.

**Enclosure decision:** Open standoff mount per JCTsh-Build-Standards.md Section 1.1. Location is sheltered under the front porch roof overhang — no weather exposure. BME280 and BH1750 must remain open to ambient air and light; enclosing them would compromise readings.

---

## Network / Integration Architecture

```
BME280 (I2C 0x76) ──┐
                     ├── ESP32 DevKitC-32 (ESPHome)
BH1750 (I2C 0x23) ──┘        │
                              │ MQTT
                              ▼
                    Mosquitto broker (raspberrypi.local:1883)
                         │         │
                         │         └──► Node-RED
                         │                │ routes /log → Python log server
                         │                │ monitors /heartbeat (watchdog)
                         │                └──► (no flow logic required for v1)
                         │
                         ▼
                    Home Assistant (raspberrypi.local:8123)
                    ├── Dashboard card (temp, humidity, pressure, lux)
                    ├── input_number.front_porch_temp_threshold (default 80°F)
                    ├── input_number.front_porch_lux_threshold (default 50 lux)
                    └── Automations
                          Alert + Reminder (mode: single)
                          Clear (mode: single)
                              │
                              ▼
                    HA Companion App
                    ├── notify.mobile_app_<joseph_device>
                    └── notify.mobile_app_<robin_device>
```

**MQTT topics:**

| Topic | Direction | Content |
|---|---|---|
| `jctsh/components/front-porch-temp-sensor/temperature` | ESP32 → broker | Temperature in °F |
| `jctsh/components/front-porch-temp-sensor/humidity` | ESP32 → broker | Humidity in % |
| `jctsh/components/front-porch-temp-sensor/pressure` | ESP32 → broker | Pressure in hPa |
| `jctsh/components/front-porch-temp-sensor/illuminance` | ESP32 → broker | Light level in lx |
| `jctsh/components/front-porch-temp-sensor/log` | ESP32 → broker | JSON log messages — routed to Python log server by Node-RED wildcard subscription |
| `jctsh/components/front-porch-temp-sensor/heartbeat` | ESP32 → broker | JSON heartbeat every 5 minutes — monitored by Node-RED watchdog wildcard subscription |

**Log message format** (per CLAUDE.md):
```json
{ "component": "front-porch-temp-sensor", "category": "System", "message": "..." }
```
Valid categories: `MQTT`, `System`, `Sensor`, `Alert`, `Test`

**Heartbeat format** (per JCTsh-Build-Standards.md Section 4.1):
- Log topic: `{ "component": "front-porch-temp-sensor", "category": "System", "message": "Heartbeat — uptime: Xh Xm, RSSI: -XXdBm, temp: XX.X°F" }`
- Heartbeat topic: `{ "component": "front-porch-temp-sensor", "uptime": "Xh Xm", "rssi": -XX, "temp": XX.X }`

**Update interval:** 60 seconds for all sensor readings.

**Heartbeat interval:** 5 minutes.

**Node-RED:** No new flow logic required for v1. The existing wildcard subscriptions (`jctsh/+/+/log` and `jctsh/+/+/heartbeat`) automatically catch this component's messages. No Node-RED changes needed.

**SmartThings:** Not used in v1. The notification use case is fully served by HA → Companion app. SmartThings surfacing is explicitly deferred (see Future Enhancements).

**Front door entity:** `binary_sensor.front_door_door` (`on` = open, `off` = closed)

**Timeout/timer logic locations:**
| Timeout | Location | Purpose |
|---|---|---|
| 60 seconds | ESPHome `update_interval` | Sensor polling rate |
| 5 minutes | ESPHome interval component | Heartbeat publish cadence |
| 15 minutes | HA automation `delay` | Reminder notification window |
| 10 minutes | Node-RED watchdog | Heartbeat expiry detection |

---

## Step 1 — Investigate Existing Patterns

**Claude Code does:** Read and document findings from the following files before writing any configuration. Record findings in `components/front-porch-temp-sensor/integration-notes.md`:

1. `components/garage-radar/garage-radar.yaml` — ESPHome YAML structure, MQTT topic pattern, heartbeat implementation, secrets references
2. `components/garage-radar/secrets.yaml.template` — secrets template format
3. `components/garage-radar/flashing.md` — flash procedure to use as reference
4. `core/node-red/core.flow.json` — confirm wildcard `/log` and `/heartbeat` subscriptions are present (do not modify)
5. Root `CLAUDE.md` credentials table — note the existing MQTT accounts to avoid naming conflicts

The integration-notes.md must document:
- How garage-radar implements heartbeat (interval, topics, payload format)
- Confirmed wildcard subscriptions present in Node-RED (no new flow needed)
- Existing MQTT accounts listed in CLAUDE.md credentials table
- Any deviation from expected patterns found during investigation

**Joseph does:** Review integration-notes.md for accuracy.

**Joseph confirms:** Investigation findings look correct, ready to proceed.

---

## Step 2 — Create Dedicated MQTT Account

**Claude Code does:** Create `components/front-porch-temp-sensor/mqtt-account-setup.md` with the exact commands to create the dedicated Mosquitto account for this component:

```bash
sudo mosquitto_passwd -b /etc/mosquitto/passwd front-porch-temp-sensor <password>
sudo chown root:mosquitto /etc/mosquitto/passwd
sudo systemctl restart mosquitto
```

Document the ownership gotcha: `sudo mosquitto_passwd` resets `/etc/mosquitto/passwd` group to `root`. The `chown` command must always follow immediately or Mosquitto will fail to read the file.

Document where to store the password: `components/front-porch-temp-sensor/secrets.yaml` (gitignored).

Document the CLAUDE.md update required: add `front-porch-temp-sensor` row to the credentials table in root CLAUDE.md.

**Joseph does:**
1. Choose a password for the `front-porch-temp-sensor` MQTT account
2. Run the commands in mqtt-account-setup.md on the Pi
3. Confirm Mosquitto restarted without errors
4. Add the account to the credentials table in root CLAUDE.md

**Joseph confirms:** MQTT account created, Mosquitto running, CLAUDE.md updated.

---

## Step 3 — ESPHome Configuration and Secrets Template

**Claude Code does:** Using the garage-radar YAML and integration-notes.md findings as reference, create:

1. `components/front-porch-temp-sensor/front-porch-temp-sensor.yaml` — ESPHome configuration
2. `components/front-porch-temp-sensor/secrets.yaml.template` — secrets template (no real credentials)

The ESPHome YAML must include:
- Device name: `front-porch-temp-sensor`
- mDNS hostname: `front-porch-temp-sensor.local`
- MQTT enabled with topic prefix `jctsh/components/front-porch-temp-sensor` — match garage-radar pattern
- MQTT credentials from `!secret` references
- WiFi credentials from `!secret` references
- OTA password from `!secret` references
- I2C bus on GPIO21 (SDA) / GPIO22 (SCL)
- BME280 platform on I2C address 0x76, update_interval 60s:
  - temperature in °F (apply Celsius → Fahrenheit filter)
  - humidity in %
  - pressure in hPa
- BH1750 platform on I2C address 0x23, update_interval 60s:
  - illuminance in lx
- Interval component publishing heartbeat every 5 minutes to both:
  - `jctsh/components/front-porch-temp-sensor/log` — JSON log format per CLAUDE.md
  - `jctsh/components/front-porch-temp-sensor/heartbeat` — JSON heartbeat format per JCTsh-Build-Standards.md Section 4.1
  - Include uptime, RSSI, and current temperature in both payloads
- Log messages for: WiFi connected, MQTT connected, MQTT disconnected, MQTT reconnected — per JCTsh-Build-Standards.md Section 4.3 log event table

**Joseph does:** Review both files for correctness. Copy secrets.yaml.template to secrets.yaml and fill in actual credentials (WiFi, MQTT password for `front-porch-temp-sensor` account, OTA password).

**Joseph confirms:** YAML looks correct, secrets.yaml populated, ready to wire and flash.

---

## Step 4 — Wiring Reference Document

**Claude Code does:** Create `components/front-porch-temp-sensor/wiring.md` documenting the complete breadboard prototype wiring.

Must include:

**ESP32 → BME280**
| BME280 Pin | ESP32 Pin | Notes |
|---|---|---|
| VCC | 3.3V | Use 3.3V — not VIN/5V despite the "5V" label on the module |
| GND | GND | |
| SDA | GPIO21 | Default I2C SDA |
| SCL | GPIO22 | Default I2C SCL |

**ESP32 → BH1750**
| BH1750 Pin | ESP32 Pin | Notes |
|---|---|---|
| VCC | 3.3V | |
| GND | GND | |
| SDA | GPIO21 | Shared I2C bus — connect to same rail as BME280 SDA |
| SCL | GPIO22 | Shared I2C bus — connect to same rail as BME280 SCL |
| ADDR | GND | Sets I2C address to 0x23 |

Include a schematic section and breadboard assembly notes. Include the GPIO pin label orientation warning from JCTsh-Build-Standards.md Section 2.6: ESP32 DevKit pin labels face down when inserted in a breadboard — mark key GPIO rows with masking tape before wiring.

Include a note to place `ESP32pins.png` (pinout reference) in the component directory. Claude Code cannot generate this image — Joseph must copy it from `components/garage-radar/ESP32pins.png`.

**Joseph does:**
1. Copy `components/garage-radar/ESP32pins.png` to `components/front-porch-temp-sensor/ESP32pins.png`
2. Wire up the breadboard prototype per wiring.md

**Joseph confirms:** Wiring complete, ready to flash.

---

## Step 5 — Flash and Validate ESPHome Firmware

**Claude Code does:** Create `components/front-porch-temp-sensor/flashing.md` based on `components/garage-radar/flashing.md`. Include:
- First-time USB flash procedure (ESPHome dashboard or CLI)
- How to confirm device appears in ESPHome dashboard after boot
- How to check MQTT topics are publishing (MQTT Explorer or mosquitto_sub)
- OTA update procedure for all subsequent flashes
- Validation checklist:
  - Temperature reading is plausible (not 0, not NaN) — expected ~70–115°F range in Tucson
  - Humidity reading is plausible — if NaN, sensor is BMP280 not BME280 (swap required)
  - Pressure reading is plausible — Tucson is ~750m elevation, expect ~925 hPa (not sea-level ~1013 hPa)
  - Illuminance reading changes when light source is moved near/away
  - All four sensor entities appear in HA
  - Log messages appearing at `http://raspberrypi.local/` (Basic Auth, user: `jctsh`)
  - Heartbeat appearing in log dashboard every 5 minutes

**Joseph does:** Follow flashing.md — flash via USB, confirm all entities in HA, confirm log messages and heartbeat in dashboard.

**Joseph confirms:** Report back:
- Temperature (°F), humidity (%), pressure (hPa), illuminance (lx)
- All four entities visible in HA: yes/no
- Log messages visible in dashboard: yes/no
- Heartbeat visible in dashboard: yes/no
- Any anomalies

**Claude Code does:** Update flashing.md with actual readings and any deviations.

---

## Step 6 — HA Integration

**Claude Code does:** Create `components/front-porch-temp-sensor/integration.md` documenting all HA configuration for this component. This document is the single reference for all HA setup steps.

---

## Step 7 — HA Helpers

**Claude Code does:** Add to `integration.md` — section for creating the two `input_number` helpers in HA UI:

| Helper | Entity ID | Min | Max | Step | Default | Unit | Purpose |
|---|---|---|---|---|---|---|---|
| Front Porch Temp Threshold | `input_number.front_porch_temp_threshold` | 60 | 110 | 1 | 80 | °F | Temperature alert threshold |
| Front Porch Lux Threshold | `input_number.front_porch_lux_threshold` | 0 | 500 | 5 | 50 | lx | Minimum lux to consider daytime |

Creation path: HA Settings → Devices & Services → Helpers → Add Helper → Number.

**Joseph does:** Create both helpers in HA UI.

**Joseph confirms:** Both helpers visible in Developer Tools → States.

---

## Step 8 — Confirm Phone Notify Entity IDs

**Claude Code does:** Add to `integration.md` — section explaining how to find the `notify.mobile_app_*` entity IDs for both phones:
- HA Developer Tools → Actions → search "notify.mobile_app"
- Both phones must appear — if not, install HA Companion app (Google Play: "Home Assistant" by Nabu Casa), connect to `http://raspberrypi.local:8123`, grant notification permissions, then restart HA

**Joseph does:** Confirm both entity IDs and report back.

**Joseph confirms:**
- Joseph's Pixel 10 Pro: `notify.mobile_app_____________`
- Robin's Pixel 7: `notify.mobile_app_____________`

**Claude Code does:** Record the confirmed entity IDs in integration.md. Use them in Step 9 automation YAML — do not use placeholders.

---

## Step 9 — HA Automations

**Claude Code does:** Using confirmed notify entity IDs from Step 8, add to `integration.md` — complete YAML for both automations, ready to paste into HA UI (Settings → Automations → Edit in YAML).

### Automation 1 — Front Porch Warm - Close Door (`mode: single`)

- **Trigger:** `numeric_state` — temperature stays ≥ `input_number.front_porch_temp_threshold` for 10 minutes
- **Condition:** time 6am–10pm
- **Actions:**
  1. Notify both phones — title: "Front Porch Warm", message includes current temperature and "Consider closing the door."
- **Mode:** `single`

### Automation 2 — Front Porch Cool - Open Door (`mode: single`)

- **Trigger:** `numeric_state` — temperature stays < `input_number.front_porch_temp_threshold` for 10 minutes
- **Condition:** time 6am–1pm
- **Actions:**
  1. Notify both phones — title: "Front Porch Cool", message includes current temperature and "Good time to open the door."
- **Mode:** `single`

**Joseph does:** Create both automations in HA UI per integration.md.

**Joseph confirms:** Both automations created and enabled.

---

## Step 10 — HA Dashboard Card

**Claude Code does:** Add to `integration.md` — section for adding the dashboard card. Include complete card YAML for an Entities or Glance card showing: temperature, humidity, pressure, illuminance. Card should be addable via HA dashboard editor → Add Card → Manual.

**Joseph does:** Add the dashboard card per integration.md.

**Joseph confirms:** Card visible on HA dashboard with live values.

---

## Step 11 — End-to-End Test

**Claude Code does:** Create `components/front-porch-temp-sensor/testing.md` with the full validation procedure:

1. **Sensor validation** — all four values updating every ~60 seconds in HA
2. **Log dashboard check** — log messages visible at `http://raspberrypi.local/` under `front-porch-temp-sensor`
3. **Heartbeat check** — heartbeat message appearing every 5 minutes in log dashboard
4. **Watchdog check** — confirm `jctsh/components/front-porch-temp-sensor/heartbeat` topic is publishing; the Node-RED watchdog wildcard subscription catches it automatically — no configuration needed
5. **Lux sensor test** — cover BH1750, confirm lux drops; uncover, confirm lux rises
6. **Alert suppression — door closed** — close front door, lower temp threshold below current temp, confirm no alert fires
7. **Alert suppression — low lux** — cover BH1750, lower temp threshold, open front door, confirm no alert fires (lux condition blocks it)
8. **Full alert test** — open front door, uncover BH1750, lower threshold below current temp, confirm both phones receive alert within 60 seconds
9. **Reminder test** — leave door open after alert fires, wait 15 minutes, confirm reminder notification on both phones
10. **Clear test** — raise threshold above current temp, confirm both phones receive clear notification
11. **Restore** — set temp threshold back to 80°F, set lux threshold back to 50

**Joseph does:** Run full test procedure and report results for each step.

**Joseph confirms:** All tests passed, or report failures.

**Claude Code does:** Update testing.md with actual results. Update any other documents if deviations found.

---

## Step 12 — Permanent Build

**Claude Code does:** Create `components/front-porch-temp-sensor/perfboard-layout.md` for transferring the breadboard build to 5×7cm perfboard:
- ESP32 DevKit on two 19-pin female header strips (removable — do not solder directly)
- BME280 and BH1750 on female header strips sized to their pin counts
- Component placement for airflow and light exposure — BME280 and BH1750 must remain open to ambient conditions
- M3 brass standoff mounting pattern (10mm standoffs per Build Standards Section 1.3)
- Soldering sequence and continuity check procedure

**Joseph does:** Transfer to perfboard per perfboard-layout.md. Validate all four sensors still reading correctly after transfer.

**Joseph confirms:** Perfboard build complete, all sensors reading correctly.

---

## Step 13 — Mounting

**Claude Code does:** Create `components/front-porch-temp-sensor/mounting.md`:
- Mount location: front porch, under roof overhang, near outlet
- BH1750 must face outward toward open sky — not toward a wall
- BME280 should have several cm separation from ESP32 (ESP32 generates slight heat)
- USB cable routing to nearby outlet
- OTA update procedure from final mounted location (no USB required after initial flash)

**Joseph does:** Mount permanently per mounting.md.

**Joseph confirms:** Mounted, sensor reading correctly from final position, all four values plausible in HA.

**Claude Code does:** Update mounting.md with actual installation details and any deviations.

---

## Step 14 — README and Final Housekeeping

**Claude Code does:** Create `components/front-porch-temp-sensor/README.md` following the garage-radar README as the closest model. Must include:
- What the component does
- Hardware table
- Wiring table (pin-by-pin)
- MQTT topics (all six: temperature, humidity, pressure, illuminance, log, heartbeat)
- ESPHome configuration summary (update interval, heartbeat interval, I2C addresses)
- HA integration summary (helpers, automations, dashboard)
- Notification logic (alert trigger conditions, reminder logic, clear logic)
- Known behaviors / tuning notes
- Deferred future enhancements
- Build document index (all files in component directory)

Also do the following final housekeeping:
1. Update root `README.md` Components list to add `front-porch-temp-sensor`
2. Add an entry to `JCTsh-Parts-Inventory.md` inventory update log: ESP32 ×1 used, BME280 ×1 used, BH1750 ×1 used, perfboard ×1 used

**Joseph confirms:** README accurate and complete. Root README and parts inventory updated.

---

## Future Enhancements

### Google Home Voice Query
Expose temperature and humidity to Google Home so either phone can ask "Hey Google, what's the temperature on the front porch?" Requires connecting HA to Google Home — planned as a separate future project. The free manual Google Assistant integration has active setup friction (Actions Console sunset, OAuth issues, 30-day re-activation). Deferred from v1.

### SmartThings Surfacing
Surface temperature and humidity in SmartThings to enable SmartThings routines to react to outdoor temperature. No immediate use case — notification via HA Companion app is sufficient. SmartThings device type would be an environmental sensor capability. Deferred from v1.

### Humidity and Pressure Automations
BME280 provides humidity and pressure at no additional cost. Future automations could react to high humidity or use pressure trends as a storm indicator. Deferred from v1.

### Option B Trigger
Alert when the front door is opened while temperature is already above threshold. Not needed for the primary use case — door is typically opened in the morning before it gets hot. Could be added as a second automation trigger. Deferred from v1.

### LED Status Indicators
Add a green LED for WiFi/MQTT connected state and a red LED for fault/disconnected state. Not included in v1 — no status indication required at this location. If added: green on GPIO4, red on GPIO2 is reserved (onboard LED), use GPIO25 — 330Ω resistors per JCTsh-Build-Standards.md Section 8.

### Configurable Threshold via Voice
Allow Robin to set the temperature threshold by voice. Requires Google Home integration (see above). Deferred.

---

## Notes for Claude Code

- **Read first:** Read `JCTsh-Build-Standards.md` and root `CLAUDE.md` before beginning any work. Then read all files in `components/garage-radar/` as the reference model. Do not invent conventions — match existing patterns.
- **Integration-notes.md is required:** Complete Step 1 investigation before writing any configuration. The heartbeat implementation in particular must match the garage-radar pattern — do not guess at the ESPHome interval component syntax.
- **MQTT account must exist before first flash:** Step 2 (MQTT account creation) must be confirmed complete before Step 5 (flash). A missing account causes silent MQTT connection failure.
- **Log format:** JSON to `jctsh/components/front-porch-temp-sensor/log` — `{ "component": "front-porch-temp-sensor", "category": "<cat>", "message": "<text>" }`. Node-RED wildcard subscription routes it automatically — no Node-RED changes needed.
- **Heartbeat:** Publish every 5 minutes to both `/log` and `/heartbeat` topics. The Node-RED watchdog wildcard `jctsh/+/+/heartbeat` catches it automatically — no watchdog configuration needed.
- **HA entity IDs:** ESPHome MQTT discovery generates entity IDs from device name + sensor name. Confirm actual entity IDs after flashing in Step 5 — automation YAML in Step 9 must use confirmed IDs, not assumed ones.
- **Notify entity IDs:** Do not write automation YAML with placeholder notify entity IDs. Wait for Joseph to confirm actual IDs in Step 8 before writing Step 9 YAML.
- **Temperature units:** ESPHome BME280 outputs Celsius by default. Apply Fahrenheit conversion filter — match garage-radar pattern exactly.
- **Secrets:** Never commit secrets.yaml. Confirm .gitignore covers it — match garage-radar pattern.
- **Breadboard before perfboard:** Steps 1–11 use the breadboard prototype. Steps 12–14 do the permanent build. Do not skip to perfboard before full end-to-end test passes.
- **Pinout PNG:** Claude Code cannot generate the ESP32pins.png — instruct Joseph to copy it from `components/garage-radar/ESP32pins.png` in Step 4.
- **SmartThings:** Not used in v1. Do not add any SmartThings integration steps.
- **Node-RED:** No new flow required for v1. Do not modify existing Node-RED flows.
- **Parts inventory:** Update `JCTsh-Parts-Inventory.md` in Step 14 — record ESP32 ×1, BME280 ×1, BH1750 ×1, perfboard ×1 consumed.