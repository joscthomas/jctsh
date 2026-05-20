# JCTsh Garage Radar — Claude Code Instructions
**Author:** Joseph C Thomas (JCT)  
**Purpose:** Claude Code instruction set for building and integrating the garage workbench presence radar component  
**Version:** 1.1  
**Version description:** Added LD2412 antenna orientation, vertical perfboard mounting, pinout PNG reference, breadboard pin label workaround, and end-to-end test procedure improvements from Phase 5 build session.  
**Project:** JCTsh — Smart Home Automation
**Status:** In progress — Step 3 complete  
**Related files:** README.md, JCTsh-Component-Planning-Pattern.md

---

## Overview

This component adds a 24GHz mmWave radar sensor (HLK-LD2412) to the garage workbench area. It solves a specific gap in the existing garage presence detection system: the ability to detect someone sitting still at the workbench for extended periods without triggering any motion-based sensor. The radar feeds into the existing garage presence automation as an additive input — nothing in the current system is removed or replaced.

---

## Working Pattern

Claude Code creates documentation and configuration files. Joseph follows those documents to perform physical assembly, wiring, flashing, and testing outside of Claude Code. Joseph reports results back, and Claude Code updates documentation to reflect actual findings, deviations, and lessons learned. Do not proceed to the next step until Joseph confirms the current step is complete.

---

## Hardware Context

| Component | Detail |
|---|---|
| Radar sensor | HLK-LD2412, 24GHz mmWave, UART interface |
| Microcontroller | ESP32 DevKitC-32, 38-pin, CP2102 USB-C |
| Firmware | ESPHome (2025.8.0 or later — first version with native LD2412 support) |
| Perfboard | Chanzon FR4 double-sided, 5×7cm (fits 38-pin ESP32 DevKit comfortably) |
| Female headers | Glarks 2.54mm single row — two 19-pin strips for ESP32, one 4-pin strip for LD2412 UART |
| Standoffs | Hilitchi M3 brass, male-female, 10mm length for board mounting |
| Power | USB-A or USB-C to the ESP32 from a nearby garage outlet |
| Mounting location | Pegboard or shelf above workbench, wall-mounted vertically, LD2412 antenna face pointing horizontally toward workbench |

**Key hardware constraints:**
- The LD2412 requires hardware UART — do not use software UART (SoftwareSerial). The ESP32 DevKitC-32 has three hardware UART ports; UART2 (GPIO16 RX, GPIO17 TX) is recommended as UART0 is used for USB and UART1 may conflict with flash.
- LD2412 UART settings: 115200 baud, 8 data bits, no parity, 1 stop bit.
- LD2412 operates at 3.3V or 5V. Power from the ESP32 3.3V pin is sufficient.
- The LD2412 TX connects to ESP32 RX (GPIO16), and LD2412 RX connects to ESP32 TX (GPIO17). TX/RX are from the perspective of each device.
- The LD2412 antenna face is the blank side of the module (no components). This face must point toward the detection zone — horizontally toward the workbench when mounted.
- Detection range: 9 meters maximum. Detection angle: ±75° cone (150° total). Aim carefully to avoid picking up the garage door or driveway through an open door.

---

## Network / Integration Architecture

```
LD2412 radar sensor
    ↓ UART (115200 baud, hardware UART2: GPIO16/GPIO17)
ESP32 DevKitC-32 running ESPHome
    ↓ 30-second smoothing timeout (ESPHome native LD2412 timeout parameter)
    ↓ WiFi → Mosquitto MQTT broker (jctsh-core, raspberrypi.local)
MQTT topic: jctsh/components/garage-radar
    ↓
Home Assistant
    ↓ 20-minute presence timeout (existing garage presence automation)
SmartThings virtual switch (existing garage presence switch)
    ↓
Garage lights + garage door automation (existing, unchanged)
```

**Integration notes:**
- The radar is additive. Existing inputs (Ring camera motion, back door open/close sensor) continue to feed the garage presence automation unchanged.
- ESPHome publishes `has_target` (true/false) — the logical OR of `has_still_target` and `has_moving_target`. This is the primary published value.
- The 30-second ESPHome timeout smooths over momentary radar detection gaps. It is a sensor-level parameter, not a presence decision.
- The 20-minute timeout is the actual presence decision and lives in Home Assistant (or Node-RED — see Step 8 investigation note).
- Log dashboard: http://JCTsh.local
- Pi access: raspberrypi.local

---

## Step 1 — ESPHome YAML Configuration
✅ Complete

**Claude Code does:**
Create `components/garage-radar/garage-radar.yaml` — the complete ESPHome configuration file including:
- Device name, WiFi credentials (use `!secret` references), MQTT broker address
- UART configuration: hardware UART2, GPIO16 (RX), GPIO17 (TX), 115200 baud, no parity, 1 stop bit
- LD2412 component with 30-second timeout
- Binary sensor for `has_target` — this is the primary published sensor
- Binary sensors for `has_still_target` and `has_moving_target` — published but not used in automation yet (available for future use)
- Numeric sensors for moving distance, still distance, moving energy, still energy, detection distance
- OTA update configuration
- Logger at INFO level

**Joseph does:**
Review the YAML for accuracy. Confirm WiFi SSID, MQTT broker address (raspberrypi.local or IP), and GPIO pin assignments look correct before flashing.

**Joseph confirms:**
YAML review complete and approved, or flags any corrections needed.

**Claude Code does (if needed):**
Update YAML based on Joseph's corrections before proceeding to Step 2.

---

## Step 2 — Wiring Diagram and Breadboard Assembly Guide
✅ Complete

**Claude Code does:**
Create `components/garage-radar/wiring.md` — a clear wiring reference including:
- Pin-by-pin connection table (LD2412 pin → ESP32 GPIO)
- Breadboard layout description (which rows/columns each component occupies)
- Notes on TX/RX orientation (common source of wiring errors)
- Notes on power: LD2412 VCC to ESP32 3.3V pin, shared GND
- Reference to the ESP32 DevKitC-32 pinout PNG in the component directory for GPIO16 and GPIO17 location
- Note: ESP32 DevKit pin labels face down when board is inserted in breadboard — mark GPIO16 and GPIO17 rows on the breadboard with masking tape before inserting the board to avoid repeated pin counting

Connection table (for reference — include in the document):

| LD2412 Pin | ESP32 Pin | Notes |
|---|---|---|
| VCC | 3.3V | Do not use 5V pin |
| GND | GND | Any GND pin |
| TX | GPIO16 (RX2) | LD2412 transmits → ESP32 receives |
| RX | GPIO17 (TX2) | ESP32 transmits → LD2412 receives |

**Joseph does:**
Assemble the circuit on the breadboard following wiring.md. Do not flash yet.

**Joseph confirms:**
Breadboard assembly complete. Visually verify TX/RX orientation before powering on.

---

## Step 3 — Flash ESPHome and Confirm MQTT
✅ Complete

**Claude Code does:**
Create `components/garage-radar/flashing.md` — step-by-step ESPHome flash instructions including:
- First-time flash via USB (subsequent updates via OTA)
- ESPHome CLI commands to compile and upload
- How to monitor serial output to confirm successful boot, WiFi connection, and MQTT connection
- Expected log output on successful startup
- OTA update command for all subsequent flashes

**Joseph does:**
Flash the ESP32 via USB following flashing.md. Monitor serial output. Confirm WiFi connects and MQTT broker connection is established.

**Joseph confirms:**
Report back: Did it boot cleanly? Did WiFi connect? Did MQTT connect? Paste any error output if not.

**Claude Code does (if needed):**
Diagnose errors from Joseph's report and update flashing.md or garage-radar.yaml as needed.

---

## Step 4 — Sensor Validation

**Claude Code does:**
Create `components/garage-radar/testing.md` — sensor validation procedure including:
- How to monitor MQTT topic `jctsh/components/garage-radar` using mosquitto_sub or MQTT Explorer
- Test cases: walk in front of sensor (has_moving_target), sit still at workbench for 2+ minutes (has_still_target), leave the area (all targets clear after 30-second timeout)
- Expected MQTT payloads for each state
- How to simulate nobody present: step behind or to the side of the sensor beyond the ±75° detection cone — presence clears after the 30-second ESPHome timeout. Alternatively, cover the LD2412 antenna face with cardboard to immediately block detection.
- How to use the LD2412 ESPHome configuration tool to adjust detection range and sensitivity if needed

**Joseph does:**
Run the validation procedure from testing.md. Test all three cases. Note any detection gaps, false positives, or range/sensitivity issues.

**Joseph confirms:**
Report results: Does has_still_target fire reliably while sitting at the workbench? Does has_target clear correctly after leaving? Any tuning needed?

**Claude Code does (if needed):**
Update garage-radar.yaml with sensitivity or range adjustments based on Joseph's findings. Document any tuning changes and rationale.

---

## Step 5 — Perfboard Transfer

**Claude Code does:**
Create `components/garage-radar/perfboard-layout.md` — permanent build instructions including:
- Perfboard layout diagram (text-based grid showing component placement)
- Sequence for soldering: headers first, then wire bridges, then verify continuity before inserting components
- Notes on soldering the two 19-pin female header strips for the ESP32 (critical: keep strips parallel and aligned)
- Notes on the 4-pin female header strip for the LD2412 UART connection
- Standoff mounting hole locations on the 5×7cm perfboard
- Continuity check procedure before powering the soldered board
- Antenna orientation note: the LD2412 antenna face (blank side, no components) must point outward toward the detection zone. Mount the LD2412 at one end of the perfboard with its antenna face pointing off the edge. The ESP32 sits alongside it — never directly in front of the antenna face (the ESP32 WiFi shield is metal and will obstruct detection).
- Mounting orientation note: the perfboard will be mounted vertically (perpendicular to the pegboard surface). Orient all components during layout with this final vertical mounting position in mind — LD2412 antenna face pointing horizontally outward, USB connector accessible from the back or bottom edge.

**Joseph does:**
Transfer the validated breadboard circuit to perfboard following perfboard-layout.md. Perform continuity checks before inserting the ESP32 and LD2412.

**Joseph confirms:**
Perfboard build complete and continuity checks passed.

---

## Step 6 — Soldered Board Validation

**Claude Code does:**
Nothing new to create — Joseph re-runs the testing.md procedure from Step 4 against the soldered board.

**Joseph does:**
Power up the soldered board. Re-run the full sensor validation from testing.md. Confirm behavior is identical to the breadboard build.

**Joseph confirms:**
Soldered board validated. Report any differences from breadboard behavior.

**Claude Code does (if needed):**
Document any differences or fixes required.

---

## Step 7 — Physical Mount

**Claude Code does:**
Create `components/garage-radar/mounting.md` — physical installation guide including:
- Recommended mounting height and angle for workbench coverage
- Mount the perfboard vertically — standing perpendicular to the pegboard surface — so the LD2412 antenna face points horizontally toward the workbench area
- Standoff assembly sequence: M3 male-female standoffs through perfboard corner holes, secured to a backing piece or directly to pegboard. Standoffs serve double duty — spacing the perfboard away from the pegboard surface for USB cable clearance, and acting as the mounting attachment points.
- USB cable routing notes
- Notes on LD2412 detection angle (±75°, 150° total cone) and how mounting position affects coverage — aim to avoid picking up the garage door or driveway through an open door

**Joseph does:**
Mount the assembly on the pegboard above the workbench following mounting.md. Route and secure the USB cable to the nearby outlet.

**Joseph confirms:**
Unit mounted. Confirm MQTT is still publishing correctly after physical installation (cable flex during mounting can dislodge connections on soldered boards).

---

## Step 8 — Home Assistant / Node-RED Integration

**Claude Code does:**
Before writing any automation code, investigate the existing garage presence automation:
- Examine the current Node-RED flows to determine if the 20-minute presence timeout lives there
- Examine Home Assistant automations for any garage presence timeout logic
- Identify exactly where and how the existing Ring camera and back door sensor inputs are wired into the presence virtual switch
- Document findings in `components/garage-radar/integration-notes.md`

Then, based on findings, create `components/garage-radar/integration.md` — integration instructions to add the radar as an additive input including:
- Where to add the `jctsh/components/garage-radar` MQTT topic as a new presence input
- How to wire it in parallel with existing inputs (Ring camera, back door sensor)
- Confirmation that the 20-minute timeout applies to all inputs equally
- Any Node-RED flow changes or HA automation changes required

**Joseph does:**
Implement the integration following integration.md. Do not remove or modify any existing presence inputs.

**Joseph confirms:**
Integration complete. The garage-radar MQTT topic is wired in as an additive presence input.

---

## Step 9 — End-to-End Validation

**Claude Code does:**
Create `components/garage-radar/end-to-end-test.md` — full system validation procedure including:
- Test case 1: Enter garage, sit still at workbench for 25 minutes — garage door should remain open, lights should remain on
- Test case 2: Leave garage, confirm presence clears after 20 minutes and automation triggers correctly
- Test case 3: Robin enters while Joseph is at workbench — confirm lights do not toggle off
- How to monitor the SmartThings virtual switch state during testing
- What to check if any test case fails
- Note: Temporarily reduce the HA presence timeout to 1–2 minutes during end-to-end testing to avoid waiting 20 minutes per test cycle — restore to 20 minutes after validation is complete
- Note: To simulate nobody present quickly, step behind or to the side of the sensor beyond the ±75° detection cone — presence clears after the 30-second ESPHome timeout. Alternatively, cover the LD2412 antenna face with cardboard to immediately block detection.

**Joseph does:**
Run all three test cases from end-to-end-test.md.

**Joseph confirms:**
Report results for each test case.

**Claude Code does (if needed):**
Diagnose any failures and update integration.md or automation configuration.

---

## Step 10 — Final Documentation

**Claude Code does:**
- Create `components/garage-radar/README.md` — the permanent component reference including: what the component does, hardware summary, wiring summary, ESPHome configuration notes, MQTT topic, integration point, known behaviors, tuning notes, and a reference to the ESP32 DevKitC-32 pinout PNG in the component directory
- Update the top-level `README.md` to add the garage-radar component to the Components list
- Archive any deviations from the plan captured during Steps 1–9 into the README

---

## Future Enhancement — Split Still vs. Moving Targets as Separate Inputs

Currently `has_target` (the OR of still and moving) is the single published presence signal. In the future, `has_still_target` and `has_moving_target` are already being published as separate MQTT sensors and could be used independently for finer-grained automation — for example, only closing the garage door if no moving target is detected (someone leaving) regardless of still target state. Defer until the basic presence detection is proven stable.

## Future Enhancement — Enclosure Lid

The current open standoff mount has no dust cover. If dust accumulation on the ESP32 or LD2412 becomes an issue in the garage environment, a simple acrylic top panel held by the same standoffs can be added. Requires cutting a piece of acrylic to the perfboard footprint and drilling four corner holes. Defer until there is evidence of a dust problem.

## Future Enhancement — Detection Zone Tuning via LD2412 Configuration Tool

The LD2412 ESPHome component supports per-zone sensitivity configuration. If the sensor picks up the garage door opening/closing as a false positive, the detection range can be narrowed to focus on the workbench area only. The ESPHome YAML `ld2412` component exposes these parameters. Defer until there is evidence of false positives from the garage door or other sources.

---

## Notes for Claude Code

- **ESPHome version requirement:** The native `ld2412` component was added in ESPHome 2025.8.0. Verify ESPHome version before flashing. If the version is older, update ESPHome first.
- **UART pin assignment:** Use hardware UART2 (GPIO16 RX, GPIO17 TX). Do not use UART0 (USB) or UART1 (may conflict with flash on some ESP32 boards).
- **TX/RX orientation:** This is the most common wiring error. LD2412 TX → ESP32 RX (GPIO16). LD2412 RX → ESP32 TX (GPIO17). Label the wires before assembly.
- **3.3V power only:** The LD2412 accepts 3.3V or 5V but power from the ESP32 3.3V pin is sufficient and avoids any level-shifting concerns.
- **LD2412 antenna orientation:** The blank face of the LD2412 module (no components) is the antenna face. It must point toward the detection zone — horizontally toward the workbench when mounted. Do not place the ESP32 or any metal directly in front of this face.
- **Perfboard mounting orientation:** The perfboard mounts vertically, perpendicular to the pegboard surface. LD2412 antenna face points horizontally outward. USB connector must be accessible from the back or bottom edge.
- **Detection range and angle:** 9 meters maximum, ±75° cone (150° total). In a garage workbench application, aim carefully to avoid picking up the garage door or driveway activity through an open door. Range and zone sensitivity can be tuned via ESPHome YAML parameters if false positives occur.
- **ESP32 pin labels:** The ESP32 DevKitC-32 pin labels face down when inserted in a breadboard. A pinout PNG has been placed in the component directory for reference. Mark GPIO16 and GPIO17 rows on the breadboard with masking tape before inserting the board.
- **MQTT topic convention:** `jctsh/components/garage-radar` — follows the JCTsh pattern `jctsh/<type>/<component>`.
- **ESPHome secrets:** WiFi credentials and MQTT broker address must use `!secret` references. Do not hardcode credentials in the YAML.
- **30-second vs. 20-minute timeouts:** These serve different purposes. The 30-second ESPHome timeout smooths over momentary radar detection gaps at the sensor level. The 20-minute HA/Node-RED timeout is the actual presence decision. Document both clearly in the README so they are not confused.
- **Step 8 investigation:** The location of the 20-minute presence timeout (Node-RED vs. Home Assistant) was not confirmed during planning. Claude Code must investigate the existing flows before writing any integration code. Do not assume.
- **Additive integration:** The radar is a new input alongside existing Ring camera and back door sensor inputs. Nothing existing is removed or modified.
- **OTA updates:** After first USB flash, all subsequent ESPHome updates can be delivered OTA. Document the OTA update command in flashing.md.
- **Testing shortcut:** For end-to-end testing, temporarily reduce the HA presence timeout to 1–2 minutes to avoid waiting 20 minutes per test cycle. Restore to 20 minutes after validation is complete.