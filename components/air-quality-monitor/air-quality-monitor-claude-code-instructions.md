# JCTsh Air Quality Monitor — Claude Code Instructions
**Author:** Joseph C Thomas (JCT)
**Purpose:** Step-by-step build instructions for `air-quality-monitor`, converting the decisions made in `JCTsh-air-quality-monitor-phase1.md` (Phases 1–3) into an executable build.
**Project:** JCT Smart Home (JCTsh)
**Version:** 1.0
**Version description:** Initial release. Covers the bench electronics/firmware build only — clip-case enclosure design is deliberately deferred to a follow-on card, same split used for hiking-sensor (CARD-0009) and remote-temp-sensor-01.
**Related files:** `JCTsh-air-quality-monitor-phase1.md`, `CLAUDE.md`, `JCTsh-Build-Standards.md`, `components/hiking-sensor/` (reference implementation — read before any firmware work, do not re-derive its patterns)

---

## Overview

`air-quality-monitor` is a portable, clip-mounted air quality sensor (PM1.0/2.5/4.0/10, VOC index, NOx index via a Sensirion SEN55) carried on hikes alongside hiking-monitor. It follows hiking-monitor's operating-mode architecture exactly: field mode (duty-cycle logging to onboard flash while away from WiFi) and home mode (WiFi replay of the stored hike's readings while docked/charging). A single RGB LED gives real-time PM2.5 field awareness without a display.

This project inherits hiking-monitor's *firmware architecture* — it does not depend on hiking-sensor's physical enclosure, which remains a separate, unfinished, unrelated deliverable (CARD-0009).

---

## Working Pattern

Claude Code creates documentation and configuration files. Joseph follows those documents to perform physical assembly, wiring, flashing, and configuration work outside of Claude Code. Joseph reports results back, and Claude Code updates documentation to reflect actual findings, deviations, and lessons learned. Do not proceed to the next step until Joseph confirms the current step is complete.

---

## Hardware Context

| Component | Detail |
|---|---|
| Microcontroller | ESP32 DevKitC-32, 38-pin, CP2102 USB-C (Bag 1, 1 remaining after hiking-sensor) |
| Air quality sensor | Sensirion SEN55 (SparkFun SEN-23715 — corrected 2026-07-09, was mislabeled SEN54 in inventory). PM1.0/2.5/4.0/10, VOC index, NOx index. I2C address 0x69 (fixed). Integrated fan. ~59mm × 37mm × 23mm. |
| Adapter | Adafruit SEN54/SEN55 Adapter Breakout (#5964) — JST GH connector, onboard 5V boost (100mA), level shifting, STEMMA QT/0.1" I2C output. Lets 3.3V ESP32 logic drive the 5V SEN55 with no separate 5V supply. |
| ESPHome sensor driver | **Native `sen5x` platform** (esphome.io/components/sensor/sen5x/) — supports SEN50/54/55 directly over I2C. No custom component needed for the sensor itself. |
| Field indicator | RGB LED (Greekcreit kit, Plastic Box) — PM2.5 threshold color: green (<12 µg/m³), yellow (12–35), red (>35) |
| Power | EEMB LiPo pouch 603449 1100mAh (Bag 7) + TP4056+boost combined module (Bag 8) — same pattern as hiking-sensor |
| SEN55 power gate | BC547B NPN transistor (Music Response bin) as a low-side switch, duty-cycling the SEN55 on/off to manage its ~70mA active draw — same substitution-for-purchased-part pattern as remote-temp-sensor-01's BC557B |
| Custom firmware component | Required for onboard flash logging + WiFi replay only (SEN55 reading itself uses the native platform above) — reuse `components/hiking-sensor/hiking_logger.h`, rename prefix per its own template instructions |
| Perfboard | Chanzon FR4, size TBD — measured in Step 3 below (SEN55 + adapter footprint is the dominant constraint) |
| Enclosure | **Deferred to a follow-on card** — clip case + carabiner, 3D-printed, air intake/exhaust ports for the SEN55 fan (see Future Enhancement section) |

**GPIO assignments:**
| GPIO | Assignment |
|---|---|
| GPIO21 | I2C SDA (SEN55 via Adafruit adapter) |
| GPIO22 | I2C SCL |
| GPIO34 | `battery_v` ADC — voltage divider midpoint (input-only pin, ADC1), 68kΩ/68kΩ divider, same pattern as hiking-sensor |
| GPIO32 | Dock-detect divider — same 68kΩ/100kΩ pattern and pin as hiking-sensor's `IN+` divider (USB present → HIGH, absent → LOW) |
| GPIO27 | SEN55 power-gate control — BC547B base via resistor, **active-high** (low-side switch: GPIO HIGH → transistor ON → SEN55 GND return connected → powered) |
| GPIO18 | RGB LED — Red |
| GPIO19 | RGB LED — Green |
| GPIO23 | RGB LED — Blue |

**Open assumption to confirm in Step 1, not yet settled:** unlike hiking-sensor, this doc does not currently plan a manual on/off slide switch — the BOM's "Field Output" section lists only the RGB LED, no switch. The working assumption is that mode is determined purely by dock-detect (USB connected = home/charging mode, USB absent = field/duty-cycle mode), which is simpler than hiking-sensor's switch+dock combination. **Confirm this is actually the intended design before wiring** — if a manual override is wanted (e.g., to force sleep without unplugging, or to distinguish "charging only" from "charging + syncing"), that changes the GPIO table above.

**I2C addressing:** SEN55 only (0x69, fixed) — no other I2C devices on this bus, no conflicts, no bus-sharing concerns.

---

## Network / Integration Architecture

```
SEN55 (I2C 0x69, via Adafruit #5964 adapter) ── ESP32 DevKitC-32 (ESPHome)
                                                      │
                                    Field mode: duty-cycle log to flash
                                    Home mode: WiFi replay to MQTT
                                                      │ MQTT
                                                      ▼
                                    Mosquitto broker (raspberrypi.local:1883)
                                         │
                                         └──► Node-RED
                                                │ routes /log → Python log server
                                                │ watchdog on /heartbeat
                                                │ wildcard /data handler → Google Sheets
```

**MQTT topics:**
- `jctsh/components/air-quality-monitor/data`
- `jctsh/components/air-quality-monitor/log`
- `jctsh/components/air-quality-monitor/heartbeat` (home mode only)

**No SmartThings, no Home Assistant integration** — no real-time state to expose (per Phase 3 decision).

**Timeout policy (Phase 3 decision, 2026-07-09):** match hiking-sensor's approach — no elaborate custom WiFi/MQTT connect-timeout logic, reasonable since home mode only happens while docked/charging (USB-powered). **Do not blindly copy hiking-sensor's `wifi.ap:` fallback block** — confirm in Step 4 below whether this device actually needs one before including it; if included, be aware of the known ESPHome bug (CARD-0045) where `reboot_timeout` doesn't apply when `wifi.ap:` is configured.

---

## Step 0 — Read Build Standards

**Claude Code does:**
Read `JCTsh-Build-Standards.md` in full. This build touches: §2 ESPHome standards (boilerplate, MQTT publishing patterns, GPIO assignment, deep-sleep/duty-cycle sequencing per §2.13), §2.10 onboard flash logging (field mode pattern), §2.14 battery safety standards, §3 MQTT standards, §4 observability standards, §8 LED indicator standards (RGB threshold pattern). Also read `components/hiking-sensor/` in full — this build must match its firmware pattern, not re-derive it. State explicitly which standards apply before writing any code or config.

**Joseph confirms:**
Acknowledged — proceed.

---

## BENCH PHASE

All steps in this section are performed on the workbench, on breadboard first per JCTsh-Build-Standards.md §1.2, before any perfboard transfer.

## Step 1 — Confirm mode-switching design

**Claude Code does:**
Present the dock-detect-only assumption (see Hardware Context above) for confirmation before any wiring or firmware work begins, since it affects the GPIO table.

**Joseph confirms:**
Dock-detect-only is correct, or specifies a manual switch requirement (and, if so, its intended behavior).

---

## Step 2 — Create MQTT account and secrets.yaml

**Claude Code does:**
Generate a strong random password, document the `mosquitto_passwd` command for the `air-quality-monitor` account (JCTsh-Build-Standards.md §2.11), create `secrets.yaml.template`, confirm `.gitignore` coverage.

**Joseph does:**
Run the account-creation command on the Pi; populate `secrets.yaml`.

**Joseph confirms:**
Account created, secrets file in place and untracked by git.

---

## Step 3 — Breadboard wiring and perfboard footprint measurement

**Claude Code does:**
Create `wiring.md` and `ESP32-project-pins.md` (full 38-pin table) covering: I2C bus to the SEN55/adapter, the BC547B SEN55 power-gate circuit, the `battery_v` divider, and the dock-detect divider (matching hiking-sensor's exact values). Also document the perfboard footprint measurement procedure (SEN55 module + Adafruit adapter physical dimensions, laid out to determine minimum board size).

**Joseph does:**
Wire on breadboard, powered via USB. Physically measure the SEN55 + adapter footprint and report back.

**Joseph confirms:**
Wiring complete; perfboard size determined.

**Claude Code does:**
Record the confirmed perfboard size in this doc and the BOM.

---

## Step 4 — ESPHome base config and SEN55 validation

**Claude Code does:**
Write the initial `air-quality-monitor.yaml` — standard boilerplate (§2.8), I2C bus, native `sen5x` sensor platform, standard `on_connect`/heartbeat MQTT patterns (§2.7). Resolve Step 1's mode-switching design into the `wifi:` block — per the timeout policy above, do not include a `wifi.ap:` fallback unless Step 1 established a real need for it.

**Joseph does:**
Flash via USB. Confirm PM/VOC/NOx readings on the log dashboard.

**Joseph confirms:**
All SEN55 fields reporting plausible values.

---

## Step 5 — RGB LED threshold logic

**Claude Code does:**
Implement the PM2.5 → RGB color mapping (green <12, yellow 12–35, red >35 µg/m³) on GPIO18/19/23.

**Joseph does:**
Verify LED color changes correctly across the three PM2.5 ranges (can simulate with a known particulate source, or verify logic against manually-set test values).

**Joseph confirms:**
All three color states verified.

---

## Step 6 — SEN55 power-gate transistor bench test

**Claude Code does:**
Document the bench test procedure for the BC547B low-side switch — confirm it reliably powers the SEN55 on/off via GPIO27, and measure actual current draw in both states with a multimeter (this both validates the transistor choice and replaces the "reasoned, not measured" fan-transistor estimate from the Phase 1 doc with a real number).

**Joseph does:**
Run the bench test.

**Joseph confirms:**
Reports measured on/off current; transistor confirmed adequate (or flags an issue if not).

---

## Step 7 — LiPo polarity check and power validation

**Claude Code does:**
Document the JST polarity verification procedure (same requirement as hiking-sensor) before first battery connection.

**Joseph does:**
Verify polarity, connect the EEMB LiPo pouch to the TP4056+boost module, confirm normal charge/power behavior.

**Joseph confirms:**
Polarity correct, battery connected and functioning normally.

---

## Step 8 — Field/home mode duty-cycle and WiFi replay firmware

**Claude Code does:**
Implement the field-mode duty-cycle logging (SEN55 power-gated on for ~10s active per 2-minute cycle per the Phase 1 power budget, reading via the native `sen5x` platform, logged to flash via the adapted `hiking_logger.h` pattern) and home-mode WiFi replay (dock-detect triggers replay of stored readings to MQTT using original timestamps, per hiking-sensor's exact pattern). Include the 5-minute heartbeat in home mode only.

**Joseph does:**
Flash via USB, simulate a field session (undock, wait through a few duty cycles) then redock and confirm replay.

**Joseph confirms:**
Field-mode logging and home-mode replay both work as expected, matching hiking-sensor's proven behavior.

---

## Step 9 — Perfboard transfer

**Claude Code does:**
Create `perfboard-layout.md` using the footprint confirmed in Step 3.

**Joseph does:**
Transfer the validated breadboard circuit to perfboard: ESP32 + SEN55/adapter + BC547B gate + RGB LED + both dividers. Continuity-check before power-on.

**Joseph confirms:**
Perfboard build complete, device boots and operates identically to the breadboard version.

---

## Step 10 — Heartbeat/watchdog registration

**Claude Code does:**
Confirm the existing Node-RED watchdog wildcard subscription and `/data` wildcard handler catch this device automatically — no new flows needed.

**Joseph does:**
Confirm in the Node-RED editor and Google Sheets.

**Joseph confirms:**
Device appears in the watchdog's tracked component list; readings appearing in the Environmental Data sheet after a simulated home-mode sync.

---

## Bench Phase Complete — Install Phase Begins

All bench steps above are confirmed complete. The device has been:
- Fully wired and perfboard-built with the SEN55/adapter, power-gate transistor, RGB LED, and both dividers
- Validated on USB power and on battery power
- Running field-mode duty-cycle logging and home-mode WiFi replay, matching hiking-sensor's proven pattern
- Integrated with the log dashboard, watchdog, and Google Sheets

Do not proceed to any install/carry-case work until every bench step above is confirmed complete.

---

## INSTALL PHASE

**Deliberately not detailed in this instruction set** — same split as hiking-sensor (CARD-0009) and remote-temp-sensor-01. Enclosure/carry-case design depends on measurements and confirmations this bench phase produces (actual perfboard footprint, confirmed power-gate transistor behavior, confirmed mode-switching design) that don't exist yet.

See "Future Enhancement" below.

---

## Future Enhancement — Clip Case Enclosure

Once the bench phase above is complete, open a follow-on planning pass covering:
- 3D-printed clip case with carabiner attachment, independent of hiking-sensor's own enclosure
- Air intake/exhaust port placement for the SEN55 fan — **re-verify Sensirion's mechanical guidelines directly** before finalizing (the current understanding is flagged low-confidence in the Phase 1 doc — sourced from a search-snippet synthesis after two failed PDF fetches, not confirmed by actually reading the primary document)
- Light-colored PETG to minimize solar gain (already decided in Phase 1)
- Micro USB charging port and external JST solar port placement (SUNYIMA panel, backpacking use)
- Screw/fastening hardware — confirm actual length needed once enclosure dimensions exist, same caution as remote-temp-sensor-01 and hiking-sensor (don't assume on-hand kit screws are long enough)

## Future Enhancement — Deferred Features (from Phase 1)

| Feature | Status |
|---|---|
| Bluetooth/real-time data share to hiking monitor display | Evaluated and deferred — added field-failure modes not justified by the data value |
| NOx threshold LED indicator | Deferred — VOC index covers field awareness adequately; NOx is more useful in post-hike Sheets analysis |
| Solar panel mount/clip design | Deferred to the enclosure design phase above |

---

## Notes for Claude Code

- Step 0 is mandatory: read `JCTsh-Build-Standards.md` in full and `components/hiking-sensor/` in full before writing any code — this build must match hiking-sensor's pattern, not re-derive it
- SEN55 uses ESPHome's native `sen5x` platform — do not write a custom component for the sensor itself
- Custom component is still needed for onboard flash logging + WiFi replay — adapt `components/hiking-sensor/hiking_logger.h`, do not rewrite from scratch
- Do not copy hiking-sensor's `wifi.ap:` fallback block without confirming it's actually needed (CARD-0045) — if included, be aware `reboot_timeout` may not function as expected
- Log format: JSON to `jctsh/components/air-quality-monitor/log`
- `lat`/`lon` are always `null` in this payload — no GPS hardware, timestamp correlation with GaiaGPS/hiking-monitor happens post-hike
- `rssi_dbm` is 0 for field-mode readings (no WiFi at time of logging) — same convention as hiking-sensor
- MQTT account: create dedicated `air-quality-monitor` Mosquitto account before first flash
- Add new account to credentials table in root `CLAUDE.md`
- Record new device IP, hostname, and MAC in `jctsh-network.md` once ready to flash
- Update `jctsh-parts-inventory.md` at the end of the bench phase — deduct all used parts, record the Step 6 measured power-gate current
- Bench-first: all bench steps must be confirmed complete before any install-phase work begins
