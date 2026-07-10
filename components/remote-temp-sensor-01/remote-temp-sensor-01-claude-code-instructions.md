# JCTsh Remote Temp Sensor 01 — Claude Code Instructions
**Author:** Joseph C Thomas (JCT)
**Purpose:** Step-by-step build instructions for `remote-temp-sensor-01`, converting the decisions made in `JCTsh-remote-temp-sensor-01-phase1.md` (Phases 1–3) into an executable build.
**Project:** JCT Smart Home (JCTsh)
**Version:** 1.0
**Version description:** Initial release. Covers the bench electronics/firmware build only — enclosure design and backyard installation are deliberately deferred to a follow-on card (see "Future Enhancement" below), same split hiking-sensor used between its own bench build and its later enclosure card (CARD-0009).
**Related files:** `JCTsh-remote-temp-sensor-01-phase1.md`, `CLAUDE.md`, `JCTsh-Build-Standards.md`, `components/front-porch-temp-sensor/`, `components/hiking-sensor/`

---

## Overview

`remote-temp-sensor-01` is a standalone, solar+battery-powered outdoor environmental sensor for a full-sun backyard location. It measures temperature, humidity, pressure (BME280), ambient light (BH1750), and UV index (LTR-390), publishing a reading every 5 minutes via a wake/publish/deep-sleep firmware cycle — power-budget analysis in the Phase 1–3 doc showed continuous WiFi operation is not viable on the SUNYIMA solar panel this device uses.

Unlike hiking-sensor, this device never leaves WiFi range — it's a fixed location — so it does not need offline flash logging or field/home mode switching. Unlike front-porch-temp-sensor, it is not wall-powered and is not sheltered, so it needs a real enclosure (deferred to a follow-on card) and a deep-sleep power architecture.

---

## Working Pattern

Claude Code creates documentation and configuration files. Joseph follows those documents to perform physical assembly, wiring, flashing, and configuration work outside of Claude Code. Joseph reports results back, and Claude Code updates documentation to reflect actual findings, deviations, and lessons learned. Do not proceed to the next step until Joseph confirms the current step is complete.

---

## Hardware Context

| Component | Detail |
|---|---|
| Microcontroller | ESP32 DevKitC-32, 38-pin, CP2102 USB-C (Bag 1 spare) |
| Temperature/humidity/pressure sensor | BME280 breakout (genuine GY-BME280 — same counterfeit warning as front-porch-temp-sensor applies, confirm humidity reads non-NaN) |
| Light sensor | BH1750 breakout (GY-302, I2C) |
| UV sensor | LTR-390 breakout (Adafruit #4831, STEMMA QT/I2C) |
| Firmware | ESPHome, wake/publish/deep-sleep cycle — no offline flash logging (fixed location, always in WiFi range) |
| Battery | Single EVE 18650 cell (INR18650/33V, 3.6V nominal, 3200mAh) — swappable, held in the AEDIKO charger+holder module |
| Charger/boost | AEDIKO 18650 charger+holder module (Bag 4) |
| Solar | SUNYIMA mini solar panel, 5.5V 80mA (Bag 6) |
| Sensor power switch | BC557B PNP transistor (Music Response bin), on hand — **substituting for a P-FET**, which is the original CARD-0027 design but not currently in inventory. Functionally equivalent at this current level (sensors draw well under the BC557B's 0.1A rating), at zero purchase cost. **Alternative not taken:** buying a dedicated P-FET remains available if the BC557B proves inadequate in testing (lower on-resistance/voltage drop, zero static gate current vs. the BC557B's small continuous base current while switched on) — not needed by default, this is a known trade-off, not an oversight. |
| Perfboard | Chanzon FR4, 5×7cm |
| Enclosure | **Deferred to a follow-on card** — see Future Enhancement section |
| LEDs | None — matches front-porch-temp-sensor's decision; saves power on every wake cycle |

**GPIO assignments:**
| GPIO | Assignment |
|---|---|
| GPIO21 | I2C SDA (shared bus — BME280 + BH1750 + LTR-390) |
| GPIO22 | I2C SCL (shared bus) |
| GPIO34 | `battery_v` ADC — voltage divider midpoint (input-only pin, ADC1) |
| GPIO35 | `solar_v` ADC — voltage divider midpoint (input-only pin, ADC1) |
| GPIO27 | Sensor power switch control — drives the BC557B's base (through a current-limiting resistor); active-low (GPIO LOW → transistor ON → sensors powered) |

**I2C addressing:**
- BME280 default address: 0x76
- BH1750 default address: 0x23 (ADDR pin tied to GND)
- LTR-390 default address: 0x53
- No conflicts, no level shifter needed — same shared-bus pattern as hiking-sensor's BME280+LTR-390.

**Sensor power switch circuit (BC557B PNP, high-side):**
```
3.3V rail ──► BC557B Emitter
              BC557B Collector ──► Sensors (BME280, BH1750, LTR-390 VCC)
GPIO27 ──[10kΩ]──► BC557B Base
```
GPIO27 LOW → base pulled low relative to emitter → transistor ON → sensors powered. GPIO27 HIGH (default/idle) → transistor OFF → sensors fully disconnected during deep sleep. This addresses the CARD-0027-class finding that ESP32 deep sleep does not cut power to downstream peripherals — sensors would otherwise draw their own current for the entire sleep interval, which is ~99% of this device's operating life.

**Voltage dividers (`battery_v`, `solar_v`):** 68kΩ/68kΩ equal-resistor dividers, same pattern and resistor values as hiking-sensor (`components/hiking-sensor/voltage-divider.md`) — halves the input voltage, firmware multiplies the ADC reading by 2 to recover the real value. Resistors from Bag 17 assortment.

**Charger module quiescent current — known unresolved item, tested in this build (Step 6 below).**

---

## Network / Integration Architecture

```
BME280 (I2C 0x76) ──┐
BH1750 (I2C 0x23)  ──┼── ESP32 DevKitC-32 (ESPHome, deep sleep 5min cycle)
LTR-390 (I2C 0x53) ──┘        │
                               │ MQTT (on wake only)
                               ▼
                    Mosquitto broker (raspberrypi.local:1883)
                         │         │
                         │         └──► Node-RED
                         │                │ routes /log → Python log server
                         │                │ watchdog on /heartbeat
                         │                │ wildcard /data handler → Google Sheets
                         ▼
                    Home Assistant → SmartThings entity exposure → Google Home
```

**MQTT topics:**
- `jctsh/components/remote-temp-sensor-01/data`
- `jctsh/components/remote-temp-sensor-01/log`
- `jctsh/components/remote-temp-sensor-01/heartbeat`

**Heartbeat:** folded into the 5-minute wake/publish cycle — no separate always-on interval timer. Every successful wake that publishes data satisfies the heartbeat requirement.

**SmartThings/Google Home:** expose via HA's SmartThings integration entity-exposure feature (Settings → Devices & Services → SmartThings → Configure) once HA entities exist from the MQTT discovery/Node-RED bridge — no virtual switches needed, this is read-only sensor data.

**Timeouts:** WiFi/MQTT connect timeout lives in ESPHome firmware — if not connected within ~20–30s of waking, abandon the attempt and return to deep sleep rather than draining the battery holding a connection open.

---

## Step 0 — Read Build Standards

**Claude Code does:**
Read `JCTsh-Build-Standards.md` in full. This build touches: §2 ESPHome standards (boilerplate, MQTT publishing patterns, GPIO assignment, deep-sleep sequencing), §2.14 battery-powered component safety standards (PCM-protected cells — note the EVE 18650 is sold **unprotected**, relying on the AEDIKO module's onboard PCB protection instead — confirm this is acceptable per §2.14 or flag it), §3 MQTT standards, §4 observability standards (heartbeat, log format, watchdog). State explicitly which standards apply before writing any code or config.

**Joseph confirms:**
Acknowledged — proceed.

---

## BENCH PHASE

All steps in this section are performed on the workbench, on breadboard first per JCTsh-Build-Standards.md §1.2, before any perfboard transfer. No step in this section requires the component to be in its final backyard location.

## Step 1 — Create MQTT account

**Claude Code does:**
Generate a strong random password. Document the `mosquitto_passwd` command to create the `remote-temp-sensor-01` account per JCTsh-Build-Standards.md §2.11, including the passwd-file ownership fix.

**Joseph does:**
Run the command on the Pi via SSH.

**Joseph confirms:**
Account created, ownership fixed, Mosquitto restarted without error.

---

## Step 2 — Create secrets.yaml

**Claude Code does:**
Create `components/remote-temp-sensor-01/secrets.yaml.template` and confirm `.gitignore` covers `secrets.yaml` for this directory.

**Joseph does:**
Populate `secrets.yaml` with WiFi credentials and the new MQTT account password.

**Joseph confirms:**
File in place, not tracked by git.

---

## Step 3 — Breadboard wiring: sensors + power switch + dividers

**Claude Code does:**
Create `wiring.md` and `ESP32-project-pins.md` (full 38-pin table, per JCTsh-Build-Standards.md's per-project pin table requirement) covering: I2C bus wiring for all three sensors, the BC557B high-side switch circuit, and both voltage dividers.

**Joseph does:**
Wire on breadboard: ESP32 + BME280 + BH1750 + LTR-390 on the shared I2C bus, BC557B switch circuit gating sensor VCC, both voltage dividers. Power the ESP32 via USB for this step — do not wire the AEDIKO/battery/solar circuit yet.

**Joseph confirms:**
Wiring complete, photo or description of connections for the record.

---

## Step 4 — ESPHome base config and sensor validation (USB powered, no sleep yet)

**Claude Code does:**
Write the initial `remote-temp-sensor-01.yaml` — standard ESPHome boilerplate (JCTsh-Build-Standards.md §2.8), I2C bus, BME280/BH1750/LTR-390 sensor definitions, standard `on_connect`/heartbeat MQTT publish patterns (§2.7). No deep sleep yet — this step validates sensors work before adding sleep complexity. Confirm BME280 reports real humidity (not NaN — counterfeit BMP280 check).

**Joseph does:**
Flash via USB. Confirm readings on the log dashboard / HA.

**Joseph confirms:**
All three sensors reporting plausible values.

---

## Step 5 — Sensor power switch validation

**Claude Code does:**
Add the GPIO27-controlled switch logic and update the YAML to power the sensors on before each read, then off.

**Joseph does:**
With a multimeter on the sensor VCC rail, confirm voltage present when GPIO27 is driven low and absent when driven high.

**Joseph confirms:**
Switch verified functional in both states.

---

## Step 6 — AEDIKO charger module quiescent current test

**Claude Code does:**
Write up the test procedure (already specified in `JCTsh-remote-temp-sensor-01-phase1.md`, "Charger Module Quiescent Current — Test and Mitigation Plan") as a standalone bench test doc, reusing hiking-sensor's CARD-0026 tester-rig method.

**Joseph does:**
Wire one EVE 18650 cell into the AEDIKO module, boost output to a spare ESP32 forced into deep sleep, multimeter in series on the battery's positive lead. Take the unloaded and ESP32-loaded readings.

**Joseph confirms:**
Reports the measured quiescent current in mA/µA.

**Claude Code does:**
Record the result in both this doc and `JCTsh-remote-temp-sensor-01-phase1.md`. If the result is small (per the Phase 1–3 doc's mitigation table), proceed as planned. If significant, pause here and bring the TPL5111-class nanopower timer question back to a Claude chat planning session before continuing — this would be a real architecture change, not a bench-step fix.

---

## Step 7 — Deep sleep wake/publish cycle firmware

**Claude Code does:**
Implement the 5-minute wake → power sensors on (GPIO27 low) → read → publish `/data` and `/heartbeat` → power sensors off (GPIO27 high) → `deep_sleep.enter` cycle. Include the 20–30s WiFi/MQTT connect timeout fallback into deep sleep (per Phase 3 timeout decision). Reference hiking-sensor's `on_boot` priority sequencing pattern (JCTsh-Build-Standards.md §2.13) for correctly ordering sensor power-up before I2C reads.

**Joseph does:**
Flash via USB, observe several wake cycles on the log dashboard, confirm ~5-minute spacing and successful publishes.

**Joseph confirms:**
At least 3 consecutive successful wake/publish cycles observed at the expected interval.

---

## Step 8 — Perfboard transfer

**Claude Code does:**
Create `perfboard-layout.md` following the front-porch-temp-sensor precedent.

**Joseph does:**
Transfer the validated breadboard circuit to perfboard: ESP32 + BME280 + BH1750 + LTR-390 + BC557B switch + both dividers. Continuity-check before power-on.

**Joseph confirms:**
Perfboard build complete, all continuity checks pass, device boots and completes a wake cycle identically to the breadboard version.

---

## Step 9 — Battery + solar bench validation

**Claude Code does:**
Document the bench validation procedure — power the perfboard build from the AEDIKO module + 18650 (no USB), monitor `battery_v` over several wake cycles, then introduce a lamp or partial sun on the solar panel and confirm `solar_v` rises and (per the environmental architecture's charging-state derivation) `solar_v > battery_v + ~0.3V` when illuminated.

**Joseph does:**
Run the bench test as documented.

**Joseph confirms:**
`battery_v` and `solar_v` both reporting plausible values; charging state derivation behaves as expected under a light source.

---

## Step 10 — Heartbeat/watchdog and Node-RED registration

**Claude Code does:**
Confirm the existing Node-RED watchdog wildcard subscription catches this device's `/heartbeat` topic automatically — no new flow needed (per JCTsh-Build-Standards.md §4.4). Confirm the `/data` wildcard handler routes to Google Sheets automatically.

**Joseph does:**
Confirm both in the Node-RED editor and Google Sheets.

**Joseph confirms:**
Device appears in the watchdog's tracked component list; readings appearing in the Environmental Data sheet.

---

## Step 11 — HA / SmartThings entity exposure

**Claude Code does:**
Document the HA entity-exposure steps (Settings → Devices & Services → SmartThings → Configure) for this device's temp/humidity/UV entities.

**Joseph does:**
Perform the exposure in the HA UI, confirm entities appear in Google Home.

**Joseph confirms:**
Entities visible in Google Home.

---

## Bench Phase Complete — Install Phase Begins

All bench steps above are confirmed complete. The device has been:
- Fully wired and perfboard-built with all three sensors, the sensor power switch, and both voltage dividers
- Validated on USB power, then on battery+solar power
- Running the 5-minute wake/publish/deep-sleep cycle with the AEDIKO module's quiescent current measured and recorded
- Integrated with the log dashboard, watchdog, Google Sheets, and HA/SmartThings/Google Home

Do not proceed to any install/enclosure work until every bench step above is confirmed complete.

---

## INSTALL PHASE

**Deliberately not detailed in this instruction set.** Per the Component Planning Pattern, enclosure and final mounting is a distinct phase — and per the Phase 1–3 planning doc's open questions (exact mounting location/coordinates, battery hatch mechanism, vent insert dimensions, screw length, solar panel mounting bracket), several CAD-level decisions depend on measurements and part choices this bench phase will only just have resolved (P-FET/BC557B validated in practice, AEDIKO quiescent current known, actual perfboard footprint known). Same split hiking-sensor used: firmware/electronics build completed first, enclosure (CARD-0009) planned and built as its own follow-on effort once the electronics were proven.

See "Future Enhancement" below.

---

## Future Enhancement — Enclosure Design and Backyard Installation

Once the bench phase above is complete, open a new planning pass (or a follow-on Claude Code instruction set) covering:
- Exact backyard mounting point from `house-lot-coordinates.md`, with full-sun exposure confirmed at that spot
- Enclosure CAD, reusing hiking-sensor's OpenSCAD/Tinkercad toolchain and the louvered vent-insert pattern for the BME280 (re-derived for this enclosure's own opening dimensions, not copied verbatim)
- Battery-access hatch mechanism (thumbscrew panel vs. friction-fit door), separate cavity from the main electronics
- Solar panel external mounting bracket, tilted toward true south at roughly Tucson's latitude angle
- M3 screw length confirmation once enclosure wall/insert dimensions exist — do not assume the on-hand M3×6 kit screws are sufficient (hiking-sensor needed 30mm)
- Filament purchase at Xerocraft (PLA test-fit, then ASA final print) — second entry in the 3D-printing backlog behind hiking-sensor

## Future Enhancement — Soil Moisture / DS18B20

Deferred from Phase 1 sensor scope — capacitive soil moisture sensor + waterproof DS18B20 soil/surface probe, if the garden-watering use case becomes a priority later. Would need one additional ADC pin (soil moisture, analog) and one additional GPIO (DS18B20 OneWire) — GPIO32/33 are still free for this.

## Future Enhancement — TPL5111 Nanopower Timer

Only pursue if Step 6's quiescent-current measurement shows the AEDIKO module's own draw is a real problem (see the Phase 1–3 doc's mitigation table). Would require a new architecture pass and a part purchase — not assumed needed by default.

---

## Notes for Claude Code

- Step 0 is mandatory: read `JCTsh-Build-Standards.md` in full, state which sections apply, confirm before writing any code or config
- Read `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md` — payload schema and MQTT topic convention defined there must be followed exactly (fields: `ts`, `lat`, `lon`, `temp_f`, `humidity_pct`, `pressure_hpa`, `illuminance_lx`, `uv_index`, `battery_v`, `solar_v`, `rssi_dbm`)
- `lat`/`lon` are hardcoded constants for this fixed sensor (from `house-lot-coordinates.md`, exact point TBD in the install phase) — not GPS-derived, not null
- No offline flash logging needed — this device is never expected to leave WiFi range, unlike hiking-sensor
- Log format: JSON to `jctsh/components/remote-temp-sensor-01/log` — `{ "component": "remote-temp-sensor-01", "category": "<cat>", "message": "<text>" }`
- Heartbeat and data publish share the same 5-minute wake cycle — no separate always-on interval timer
- MQTT account: create dedicated Mosquitto account before first flash — see JCTsh-Build-Standards.md §2.7/§2.11
- Add new account to credentials table in root `CLAUDE.md`
- Record new device IP, hostname, and MAC in `jctsh-network.md` once ready to flash (deferred from Phase 3)
- Update `jctsh-parts-inventory.md` at the end of the bench phase — deduct all used parts, and correct the AEDIKO module's inventory entry with the measured quiescent current from Step 6
- Bench-first: all bench steps must be confirmed complete before any install-phase work begins
