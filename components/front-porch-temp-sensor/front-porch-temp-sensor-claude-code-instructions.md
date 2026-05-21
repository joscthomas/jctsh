# JCTsh Front Porch Temp Sensor — Claude Code Instructions
**Author:** Joseph C Thomas (JCT)
**Purpose:** Step-by-step build instructions for the front-porch-temp-sensor component.
**Project:** JCT Smart Home (JCTsh)
**Version:** 1.0
**Version description:** Initial release. Produced from Phase 4 of the JCTsh Component Planning Pattern.
**Related files:** README.md, CLAUDE.md, components/garage-radar/

---

## Overview

The front-porch-temp-sensor monitors outdoor temperature, humidity, barometric pressure, and light level on the front porch. It sends push notifications to both household phones when the temperature rises above a configurable threshold while the front door is open during daylight hours. A reminder notification fires 15 minutes later if the door is still open. A clear notification fires when the temperature drops back below the threshold.

The primary use case: Robin wants to know when to close the front door before the house starts warming up.

---

## Working Pattern

Claude Code creates documentation and configuration files. Joseph follows those documents to perform physical assembly, wiring, flashing, and HA configuration outside of Claude Code. Joseph reports results back, and Claude Code updates documentation to reflect actual findings, deviations, and lessons learned. Do not proceed to the next step until Joseph confirms the current step is complete.

---

## Hardware Context

| Component | Detail |
|---|---|
| Microcontroller | ESP32 DevKitC-32, 38-pin, CP2102 USB-C (hiBCTR 6-pack) |
| Temperature/humidity/pressure sensor | BME280 breakout (Podazz 3-pack, I2C, 5V, onboard regulator) |
| Light sensor | BH1750 breakout (hiBCTR GY-302, I2C) |
| Firmware | ESPHome |
| Perfboard | Chanzon FR4, 5×7cm recommended |
| Mounting | M3 brass standoffs — open standoff mount convention (no enclosure) |
| Power | 5V USB wall charger + USB-A to USB-C cable, front porch outlet |
| Location | Front porch, under roof overhang — sheltered from rain and direct sun |

**I2C bus:** Both sensors share GPIO21 (SDA) and GPIO22 (SCL).
- BME280 default I2C address: 0x76
- BH1750 default I2C address: 0x23
- No address conflict. No level shifter needed. No pull-up resistors needed (included on breakout boards).

**BME280 wiring note:** The Podazz BME280 is labeled 5V and has an onboard voltage regulator. Power from ESP32 3.3V pin — do not use VIN/5V for this sensor.

**BMP280 counterfeit warning:** Some cheap modules labeled "BME280" are actually BMP280 and have no humidity sensor. ESPHome will report humidity as NaN if this is the case. Validation step in Step 3 confirms genuine BME280.

---

## Network / Integration Architecture

```
BME280 (I2C 0x76) ──┐
                     ├── ESP32 DevKitC-32 (ESPHome)
BH1750 (I2C 0x23) ──┘        │
                              │ MQTT discovery
                              ▼
                    Mosquitto broker (Raspberry Pi)
                              │
                              ▼
                    Home Assistant
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

**MQTT topic prefix:** `jctsh/components/front-porch-temp-sensor`

**Front door entity:** `binary_sensor.front_door_door` (`on` = open, `off` = closed)

**Update interval:** 60 seconds for all sensors.

---

## Step 1 — ESPHome Configuration File

**Claude Code does:**

Read `components/garage-radar/garage-radar.yaml` and `components/garage-radar/secrets.yaml.template` as reference models. Then create the following files for the front-porch-temp-sensor component:

1. `components/front-porch-temp-sensor/front-porch-temp-sensor.yaml` — ESPHome configuration
2. `components/front-porch-temp-sensor/secrets.yaml.template` — secrets template (no real credentials)

The ESPHome YAML must include:
- Device name: `front-porch-temp-sensor`
- mDNS hostname: `front-porch-temp-sensor.local`
- MQTT discovery enabled — same pattern as garage-radar
- MQTT topic prefix: `jctsh/components/front-porch-temp-sensor`
- BME280 sensor on I2C address 0x76, GPIO21/GPIO22, update_interval 60s
  - temperature entity, unit °F
  - humidity entity, unit %
  - pressure entity, unit hPa
- BH1750 sensor on I2C address 0x23, GPIO21/GPIO22, update_interval 60s
  - illuminance entity, unit lx
- OTA password-protected (from secrets.yaml)
- WiFi credentials from secrets.yaml
- MQTT credentials from secrets.yaml
- Friendly names matching the front-porch-temp-sensor naming convention

**Joseph does:** Nothing yet — review the generated files and confirm they look correct before proceeding.

**Joseph confirms:** Files look correct, ready to proceed to wiring.

---

## Step 2 — Wiring Reference Document

**Claude Code does:**

Create `components/front-porch-temp-sensor/wiring.md` documenting the complete wiring for breadboard prototype build.

The document must cover:

### ESP32 → BME280
| BME280 Pin | ESP32 Pin | Notes |
|---|---|---|
| VCC | 3.3V | Use 3.3V — not VIN/5V despite the "5V" label |
| GND | GND | |
| SDA | GPIO21 | Default I2C SDA |
| SCL | GPIO22 | Default I2C SCL |

### ESP32 → BH1750
| BH1750 Pin | ESP32 Pin | Notes |
|---|---|---|
| VCC | 3.3V | |
| GND | GND | |
| SDA | GPIO21 | Shared I2C bus with BME280 |
| SCL | GPIO22 | Shared I2C bus with BME280 |
| ADDR | GND | Sets I2C address to 0x23 (low = 0x23, high = 0x5C) |

Both sensors share the same SDA and SCL lines — connect both SDA pins to GPIO21 and both SCL pins to GPIO22. The I2C bus supports multiple devices simultaneously.

Include a schematic section and any assembly notes relevant to breadboard prototype.

**Joseph does:** Wire up the breadboard prototype per wiring.md.

**Joseph confirms:** Wiring complete, ready to flash.

---

## Step 3 — Flash and Validate ESPHome Firmware

**Claude Code does:** Create `components/front-porch-temp-sensor/flashing.md` documenting the ESPHome flash procedure. Base it on `components/garage-radar/flashing.md` as a reference. Include:
- Copy secrets.yaml.template to secrets.yaml and fill in credentials
- First-time USB flash procedure using ESPHome dashboard or CLI
- How to confirm the device appears in ESPHome dashboard after boot
- How to check MQTT discovery in HA (Settings → Devices & Services → ESPHome or MQTT)
- Validation checklist:
  - Temperature reading is plausible (not 0, not NaN)
  - Humidity reading is plausible — if NaN, sensor is BMP280 not BME280 (see BMP280 warning in Hardware Context)
  - Pressure reading is plausible (~1013 hPa at sea level; Tucson is ~750m elevation so expect ~925 hPa)
  - Illuminance reading changes when light source is moved near/away from sensor
  - All four entities appear in HA

**Joseph does:** Follow flashing.md — copy and fill secrets.yaml, flash via USB, confirm all four entities appear in HA with plausible values.

**Joseph confirms:** Report back:
- Temperature reading (°F)
- Humidity reading (%)
- Pressure reading (hPa)
- Illuminance reading (lux)
- All four entities visible in HA: yes/no
- Any anomalies

**Claude Code does:** Update flashing.md with actual readings and any deviations from expected values.

---

## Step 4 — HA Helpers

**Claude Code does:** Create `components/front-porch-temp-sensor/ha-helpers.md` documenting the two `input_number` helpers to create in HA UI.

| Helper | Entity ID | Min | Max | Step | Default | Unit | Purpose |
|---|---|---|---|---|---|---|---|
| Front Porch Temp Threshold | `input_number.front_porch_temp_threshold` | 60 | 110 | 1 | 80 | °F | Temperature alert threshold |
| Front Porch Lux Threshold | `input_number.front_porch_lux_threshold` | 0 | 500 | 5 | 50 | lx | Minimum lux to consider daytime |

Document the creation path: HA Settings → Devices & Services → Helpers → Add Helper → Number.

**Joseph does:** Create both helpers in HA UI per ha-helpers.md.

**Joseph confirms:** Both helpers created and visible in Developer Tools → States.

---

## Step 5 — Confirm Phone Notify Entity IDs

**Claude Code does:** Create `components/front-porch-temp-sensor/notify-entities.md` explaining how to find the `notify.mobile_app_*` entity IDs for both phones. Document the path: HA Developer Tools → Actions → search "notify.mobile_app" — both phones should appear if the HA Companion app is installed and connected on each device.

Include instructions for installing the HA Companion app if not already present:
- Google Play Store → "Home Assistant" (by Nabu Casa)
- On first launch: connect to HA instance local URL (e.g. `http://raspberrypi.local:8123`)
- Grant notification permissions when prompted
- After connecting, restart HA — the `notify.mobile_app_<device>` action will register

**Joseph does:** Confirm both `notify.mobile_app_*` entity IDs — one for Joseph's Pixel 10 Pro, one for Robin's Pixel 7. Install Companion app on either phone if not already present.

**Joseph confirms:** Report back the exact entity IDs for both phones:
- Joseph's phone: `notify.mobile_app_____________`
- Robin's phone: `notify.mobile_app_____________`

**Claude Code does:** Record the confirmed entity IDs in notify-entities.md and use them in the automation YAML in Step 6.

---

## Step 6 — HA Automations

**Claude Code does:** Using the confirmed notify entity IDs from Step 5, create `components/front-porch-temp-sensor/ha-automations.md` containing the complete YAML for both automations, ready to paste into HA UI (Settings → Automations → Edit in YAML).

### Automation 1 — Front Porch Temp Alert + Reminder (`mode: single`)

Logic:
- **Trigger:** `sensor.front_porch_temp_sensor_temperature` rises above `input_number.front_porch_temp_threshold`
- **Conditions:**
  - `binary_sensor.front_door_door` is `on` (open)
  - `sensor.front_porch_temp_sensor_illuminance` is above `input_number.front_porch_lux_threshold`
- **Actions:**
  1. Send notification to both phones: title "Front Porch Temp Alert", message includes current temperature value via template (e.g. "Front porch is {{ states('sensor.front_porch_temp_sensor_temperature') | round(1) }}°F and the front door is open. Consider closing the door.")
  2. `delay: 00:15:00`
  3. Condition: `binary_sensor.front_door_door` is still `on`
  4. If condition met: send reminder notification to both phones: title "Front Porch Temp Reminder", message "Front porch is still {{ states('sensor.front_porch_temp_sensor_temperature') | round(1) }}°F and the front door is still open."
- **Mode:** `single`

### Automation 2 — Front Porch Temp Clear (`mode: single`)

Logic:
- **Trigger:** `sensor.front_porch_temp_sensor_temperature` drops below `input_number.front_porch_temp_threshold`
- **Conditions:** None
- **Actions:**
  1. Send notification to both phones: title "Front Porch Temp OK", message "Front porch temperature has dropped to {{ states('sensor.front_porch_temp_sensor_temperature') | round(1) }}°F."
- **Mode:** `single`

**Joseph does:** Create both automations in HA UI per ha-automations.md.

**Joseph confirms:** Both automations created and enabled in HA.

---

## Step 7 — HA Dashboard Card

**Claude Code does:** Create `components/front-porch-temp-sensor/ha-dashboard.md` documenting how to add a dashboard card showing all four sensor values. Suggest an Entities card or a Glance card with:
- Temperature
- Humidity
- Pressure
- Illuminance

Include the YAML for the card so it can be added via the HA dashboard editor.

**Joseph does:** Add the dashboard card per ha-dashboard.md.

**Joseph confirms:** Card visible on HA dashboard with live values.

---

## Step 8 — End-to-End Test

**Claude Code does:** Create `components/front-porch-temp-sensor/end-to-end-test.md` with a test procedure covering:

1. **Sensor validation** — confirm all four values updating every ~60 seconds in HA
2. **Daytime lux test** — cover the BH1750 with hand, confirm lux drops; uncover, confirm lux rises
3. **Alert suppression test (door closed)** — close the front door, temporarily lower `input_number.front_porch_temp_threshold` below current temperature in HA Developer Tools → States, confirm no notification fires (door closed suppresses alert)
4. **Alert suppression test (nighttime)** — cover BH1750, temporarily lower threshold, confirm no notification fires (low lux suppresses alert)
5. **Full alert test** — open the front door, ensure BH1750 is uncovered, lower threshold below current temperature, confirm both phones receive alert notification within 60 seconds
6. **Reminder test** — leave door open after alert fires, wait 15 minutes, confirm reminder notification arrives on both phones
7. **Clear test** — raise threshold above current temperature, confirm both phones receive clear notification
8. **Restore** — set threshold back to 80°F, set lux threshold back to 50

**Joseph does:** Run through the full test procedure and report results for each step.

**Joseph confirms:** All tests passed, or report any failures.

**Claude Code does:** Update end-to-end-test.md with actual test results. Update any other documents if deviations were found during testing.

---

## Step 9 — Permanent Build and Mounting

**Claude Code does:** Create `components/front-porch-temp-sensor/perfboard-layout.md` with guidance for transferring the breadboard build to the 5×7cm perfboard using the open standoff mount convention. Include:
- Component placement recommendations (ESP32 on female headers for removability, BME280 and BH1750 positioned for good airflow and light exposure)
- M3 standoff mounting pattern
- Note that BME280 and BH1750 must not be enclosed — they need exposure to ambient air and light

Create `components/front-porch-temp-sensor/mounting.md` with guidance for mounting the perfboard assembly on the front porch:
- Position the BH1750 to face outward toward ambient light, not toward a wall
- Keep BME280 away from heat sources (the ESP32 itself generates slight heat — leave a few cm of separation if possible)
- Route USB cable to nearby outlet
- OTA update procedure after permanent installation (no USB required)

**Joseph does:** Transfer to perfboard and mount on the front porch per both documents.

**Joseph confirms:** Permanent build complete, sensor reading correctly from final mounted position.

**Claude Code does:** Update mounting.md with actual installation details and any deviations.

---

## Step 10 — README

**Claude Code does:** Create `components/front-porch-temp-sensor/README.md` following the conventions of existing component READMEs in the repo (see `components/garage-radar/README.md` as the closest model). The README must document:
- What the component does
- Hardware table
- Wiring table
- ESPHome configuration summary (MQTT topics, update interval, I2C addresses)
- HA integration (helpers, automations, dashboard)
- Notification logic (alert, reminder, clear)
- Deferred future enhancements
- Build document index (all files in the component directory)

**Joseph confirms:** README looks accurate and complete.

---

## Future Enhancements

### Google Home Voice Query
Expose temperature and humidity to Google Home so either phone can ask "Hey Google, what's the temperature on the front porch?" Requires connecting HA to Google Home — planned as a separate future project using the free manual Google Assistant integration or a suitable broker. Deferred from v1 due to setup complexity unrelated to the sensor build itself.

### SmartThings Surfacing
Surface temperature and humidity values in SmartThings via HA virtual sensor devices. Would enable SmartThings routines to react to outdoor temperature. Deferred from v1 — no immediate use case requiring SmartThings involvement.

### Humidity and Pressure Automations
The BME280 provides humidity and pressure at no additional cost. Future automations could react to humidity (e.g. high humidity alert) or pressure trends (barometric pressure drop as a storm indicator). Deferred from v1.

### Option B Trigger
Alert when the front door is opened while temperature is already above threshold. Not needed for the primary use case (door is typically opened in the morning before it gets hot) but could be added as a second automation trigger. Deferred from v1.

### Configurable Threshold via Voice
Allow Robin to set the temperature threshold by voice command. Requires Google Home integration (see above). Deferred.

---

## Notes for Claude Code

- **Reference model:** `components/garage-radar/` is the closest existing component — ESPHome firmware, MQTT discovery, HA integration. Read all files in that directory before writing any configuration.
- **Naming convention:** Component name is `front-porch-temp-sensor`. ESPHome device name, MQTT prefix, and HA entity IDs must all follow this name consistently.
- **HA entity IDs:** ESPHome MQTT discovery will generate entity IDs based on the device name and sensor names defined in the YAML. Confirm actual entity IDs after flashing in Step 3 — the automation YAML in Step 6 must use the actual IDs, not assumed ones.
- **Notify entity IDs:** Do not write automation YAML with placeholder notify entity IDs. Wait for Joseph to confirm actual IDs in Step 5 before writing Step 6 YAML.
- **Temperature units:** ESPHome BME280 component outputs Celsius by default. Configure `unit_of_measurement: "°F"` and use ESPHome's `filters: - lambda: return x * (9.0/5.0) + 32;` to convert, or set `unit_of_measurement` in the platform config. Confirm the approach matches garage-radar conventions.
- **Lux threshold default:** 50 lux reliably distinguishes daylight from darkness for the Tucson environment. Joseph may tune this after installation via the HA dashboard — no code change required.
- **mode: single on automations:** Both automations use `mode: single`. This ensures the alert fires once per threshold crossing and the 15-minute reminder delay is not restarted by subsequent sensor updates while the automation is running.
- **Secrets:** Never commit secrets.yaml. Confirm .gitignore covers it — check garage-radar component for the existing pattern.
- **Perfboard build:** Steps 1–8 use the breadboard prototype. Steps 9–10 transfer to permanent perfboard build. Do not skip straight to perfboard — validate on breadboard first.
