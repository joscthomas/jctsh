# JCTsh Garage Radar — Claude Code Instructions
**Author:** Joseph C Thomas (JCT)
**Purpose:** Claude Code instruction set for building and integrating the garage workbench presence radar component
**Version:** 1.3
**Version description:** Corrected logging, watchdog, and SmartThings integration based on CLAUDE.md. Log format is JSON to /log topic. Watchdog is a new Node-RED flow built as part of this project. SmartThings path is Node-RED → HA REST API → virtual switch. Added MQTT account creation step. Added Node-RED watchdog flow build to Step 4.5. Added HA companion app phone notification as watchdog alert.
**Project:** JCTsh — Smart Home Automation
**Status:** In progress — Step 4 complete, Step 4.5 ready to begin
**Related files:** README.md, CLAUDE.md, JCTsh-Component-Planning-Pattern.md, JCTsh-Parts-Inventory.md, JCTsh-Build-Standards.md

---

## Overview

This component adds a 24GHz mmWave radar sensor (HLK-LD2412) to the garage workbench area. It solves a specific gap in the existing garage presence detection system: the ability to detect someone sitting still at the workbench for extended periods without triggering any motion-based sensor. The radar feeds into the existing garage presence automation as an additive input — nothing in the current system is removed or replaced.

This project also builds the JCTsh Node-RED watchdog flow — a new infrastructure component that monitors all ESP32 component heartbeats and alerts via the HA companion app on Joseph's Pixel 10 Pro if any component goes silent.

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
| Green LED | 5mm green, GPIO25, 330Ω resistor — presence detected indicator |
| Yellow LED | 5mm yellow, GPIO26, 330Ω resistor — garage presence virtual switch status indicator |
| Enclosure | None — open standoff mount. See JCTsh-Build-Standards.md Section 1.1. |
| Parts reference | See JCTsh-Parts-Inventory.md for on-hand parts before adding to BOM |

**Key hardware constraints:**
- The LD2412 requires hardware UART — do not use software UART (SoftwareSerial). Use UART2 (GPIO16 RX, GPIO17 TX).
- LD2412 UART settings: 115200 baud, 8 data bits, no parity, 1 stop bit.
- LD2412 operates at 3.3V or 5V. Power from the ESP32 3.3V pin is sufficient.
- The LD2412 TX connects to ESP32 RX (GPIO16), and LD2412 RX connects to ESP32 TX (GPIO17).
- The LD2412 antenna face is the blank side of the module (no components). It must point horizontally toward the workbench when mounted.
- Detection range: 9 meters maximum. Detection angle: ±75° cone (150° total).
- GPIO25 and GPIO26 are clean output GPIOs with no boot conflicts — reserved for green and yellow LEDs.
- Use 330Ω current-limiting resistors for both LEDs at 3.3V.

---

## Network / Integration Architecture

```
LD2412 radar sensor
    ↓ UART (115200 baud, hardware UART2: GPIO16/GPIO17)
ESP32 DevKitC-32 running ESPHome
    ↓ 30-second smoothing timeout (ESPHome native LD2412 timeout parameter)
    ↓ WiFi → Mosquitto MQTT broker (raspberrypi.local, port 1883)
MQTT topics published:
    jctsh/components/garage-radar/state        (has_target: ON/OFF)
    jctsh/components/garage-radar/still        (has_still_target: ON/OFF)
    jctsh/components/garage-radar/moving       (has_moving_target: ON/OFF)
    jctsh/components/garage-radar/log          (JSON log messages → Python log server)
    jctsh/components/garage-radar/heartbeat    (5-minute heartbeat → Node-RED watchdog)
MQTT topic subscribed:
    jctsh/components/garage-presence-vswitch/state  (drives yellow LED)
    ↓
Node-RED
    ↓ /log → Python log server (http://raspberrypi.local/)
    ↓ /heartbeat → Node-RED watchdog flow → HA REST API → Pixel 10 Pro (if silent)
    ↓ /state → garage presence automation (additive input)
    ↓ HA REST API (port 8123) → SmartThings motion sensor
Home Assistant
    ↓ 20-minute presence timeout (existing garage presence automation)
SmartThings virtual switch (existing garage presence switch)
    ↓
Garage lights + garage door automation (existing, unchanged)
```

**Two parallel message flows (per CLAUDE.md architecture):**
- **Data flow:** `jctsh/components/garage-radar/state` — drives automations
- **Log flow:** `jctsh/components/garage-radar/log` — routed by Node-RED to Python log server

**Integration notes:**
- The radar is additive. Existing inputs (Ring camera motion, back door open/close sensor) unchanged.
- The 30-second ESPHome timeout smooths sensor gaps — it is not a presence decision.
- The 20-minute timeout is the actual presence decision (Node-RED or HA — investigate in Step 8).
- The yellow LED subscribes to the garage presence virtual switch MQTT topic via ESPHome mqtt_subscribe.
- SmartThings integration path: Node-RED → HA REST API → HA entity → SmartThings. No other path.
- Log dashboard: http://raspberrypi.local/ (Basic Auth, user: jctsh)
- Node-RED: http://raspberrypi.local:1880/
- Home Assistant: http://raspberrypi.local:8123/
- Pi fixed IP: 192.168.1.117 (use if .local resolution fails)
- Pi Tailscale IP: 100.70.162.24 (use for remote access — same ports apply)

---

## Step 1 — ESPHome YAML Configuration
✅ Complete

---

## Step 2 — Wiring Diagram and Breadboard Assembly Guide
✅ Complete

---

## Step 3 — Flash ESPHome and Confirm MQTT
✅ Complete

---

## Step 4 — Sensor Validation
✅ Complete

---

## Step 4.5 — Enhancements: LEDs, Logging, Heartbeat, Watchdog, SmartThings

**Claude Code does:**

**1. Confirm MQTT account exists**
The `garage-radar` MQTT account is listed in the CLAUDE.md credentials table, indicating it was created during Steps 1–4. Verify the account exists and is working (confirmed by the fact that Steps 1–4 are complete). Document the account name in integration-notes.md. If for any reason it needs to be created:
```bash
sudo mosquitto_passwd -b /etc/mosquitto/passwd garage-radar <password>
sudo chown root:mosquitto /etc/mosquitto/passwd
sudo systemctl restart mosquitto
```

**2. Update `components/garage-radar/garage-radar.yaml`** to add:

LED outputs:
- Green LED on GPIO25 — on when `has_target` is ON, off when OFF
- Yellow LED on GPIO26 — driven by MQTT subscription to `jctsh/components/garage-presence-vswitch/state`
- Both LEDs use 330Ω current-limiting resistors at 3.3V

Log messages (JSON format, published to `jctsh/components/garage-radar/log`):
```json
{ "component": "garage-radar", "category": "System", "message": "Garage radar online — ESPHome vX.X.X, IP: x.x.x.x" }
{ "component": "garage-radar", "category": "MQTT", "message": "MQTT broker connected — publishing to jctsh/components/garage-radar/state" }
{ "component": "garage-radar", "category": "MQTT", "message": "MQTT disconnected" }
{ "component": "garage-radar", "category": "MQTT", "message": "MQTT reconnected" }
{ "component": "garage-radar", "category": "Sensor", "message": "Presence detected — has_target: ON (still: ON/OFF, moving: ON/OFF, distance: Xm)" }
{ "component": "garage-radar", "category": "Sensor", "message": "Presence cleared — has_target: OFF, timeout elapsed" }
{ "component": "garage-radar", "category": "System", "message": "Heartbeat — uptime: Xh Xm, RSSI: -XXdBm, presence: ON/OFF" }
```

Heartbeat (every 5 minutes, published to two topics):
- `jctsh/components/garage-radar/log` — heartbeat as standard log JSON (visible in dashboard)
- `jctsh/components/garage-radar/heartbeat` — heartbeat as JSON for Node-RED watchdog:
  ```json
  { "component": "garage-radar", "uptime": "Xh Xm", "rssi": -XX, "presence": "ON/OFF" }
  ```

**3. Update `components/garage-radar/wiring.md`** to add:
- Green LED wiring: GPIO25 → 330Ω resistor → LED anode → LED cathode → GND
- Yellow LED wiring: GPIO26 → 330Ω resistor → LED anode → LED cathode → GND
- Updated breadboard layout diagram showing LED positions
- Note: mark GPIO25 and GPIO26 rows on breadboard with masking tape before wiring

**4. Build the Node-RED watchdog flow**

This is a new JCTsh infrastructure component. Create `core/node-red/watchdog.flow.json` and document the build in `components/garage-radar/watchdog-build.md`.

The watchdog flow:
- Subscribes to `jctsh/+/+/heartbeat` (MQTT wildcard — catches all component heartbeats automatically)
- On receipt of any heartbeat message, extracts the component name from the topic and resets a per-component timer node (10-minute timeout — 2× the 5-minute heartbeat interval)
- If a timer expires without receiving a new heartbeat, publishes an alert
- Alert path: Node-RED function node → HA REST API POST to `http://raspberrypi.local:8123/api/services/notify/mobile_app_pixel_10_pro` → HA companion app → Joseph's Pixel 10 Pro
- Alert message: `JCTsh alert: <component-name> has not reported in 10 minutes`
- Also logs the alert: publish to `jctsh/core/watchdog/log` as `{ "component": "watchdog", "category": "Alert", "message": "Component <name> silent for 10 minutes" }`

Before building: examine existing Node-RED flows in `core/node-red/` to understand the established flow structure, MQTT broker node configuration, and HA REST API call pattern. Match the existing style.

The HA long-lived access token for the REST API call is stored in Node-RED credentials — do not hardcode it. Use the existing credential pattern from the salt sensor Node-RED flow.

**5. Build SmartThings motion sensor integration**

Before writing: examine `components/salt-sensor/` Node-RED flow and integration files to understand the established Node-RED → HA REST API → SmartThings pattern.

Create `components/garage-radar/smartthings-integration.md` documenting:
- Create a virtual motion sensor device in SmartThings named "Garage Radar"
- Expose it as an HA entity (HA syncs to SmartThings automatically via the existing SmartThings integration)
- Add a Node-RED flow node that subscribes to `jctsh/components/garage-radar/state` and calls the HA REST API to set the motion sensor Active (ON) or Inactive (OFF)
- Motion Active = has_target ON; Motion Inactive = has_target OFF

**6. Create `components/garage-radar/integration-notes.md`** documenting:
- MQTT account confirmation
- Log routing: Node-RED wildcard `jctsh/+/+/log` subscription routes to Python log server — no per-component changes needed
- Watchdog: new flow built, wildcard `jctsh/+/+/heartbeat` catches garage-radar automatically
- SmartThings: pattern examined from salt sensor, followed for garage radar
- HA REST API endpoint and notification service name confirmed

**Joseph does:**
Review the updated YAML. Add the two LEDs and resistors to the existing breadboard. Import and activate the watchdog flow in Node-RED. Implement the SmartThings motion sensor integration.

**Joseph confirms:**
Updated breadboard assembly complete. Watchdog flow active. SmartThings motion sensor created and integration implemented.

---

## Step 4.6 — Enhancement Validation on Breadboard

**Claude Code does:**
Update `components/garage-radar/testing.md` to add enhancement validation:
- Green LED: confirm it lights when presence detected, extinguishes after 30-second timeout
- Yellow LED: confirm it reflects the garage presence virtual switch state
- Log messages: confirm each message appears at `http://raspberrypi.local/` under component `garage-radar`
- Heartbeat: confirm heartbeat appears in log dashboard every 5 minutes
- Watchdog: confirm heartbeat topic is being received by the Node-RED watchdog flow — monitor in Node-RED debug panel. Simulate a missed heartbeat by temporarily disabling the ESP32 and confirm a phone notification arrives within 10 minutes.
- SmartThings: confirm "Garage Radar" motion sensor appears in SmartThings and state changes correctly when presence is detected and cleared

**Joseph does:**
Run the enhancement validation procedure. Test all items above. Report any failures.

**Joseph confirms:**
All enhancements validated on breadboard, including phone notification received for watchdog test.

**Claude Code does (if needed):**
Diagnose any failures and update YAML, Node-RED flows, or integration configuration as needed.

---

## Step 5 — Perfboard Transfer

**Claude Code does:**
Create `components/garage-radar/perfboard-layout.md` — permanent build instructions including:
- Perfboard layout diagram (text-based grid showing component placement)
- Sequence for soldering: headers first, then wire bridges, then verify continuity before inserting components
- Notes on soldering the two 19-pin female header strips for the ESP32 (critical: keep strips parallel and aligned)
- Notes on the 4-pin female header strip for the LD2412 UART connection
- LED and resistor placement — both LEDs and 330Ω resistors included in layout
- Standoff mounting hole locations on the 5×7cm perfboard
- Continuity check procedure before powering the soldered board
- Antenna orientation: LD2412 blank face (antenna) points off the edge toward the workbench. ESP32 alongside — never in front of the antenna face.
- Mounting orientation: perfboard mounts vertically (perpendicular to pegboard). LD2412 antenna face points horizontally outward. USB connector accessible from back or bottom edge. LEDs visible from front.

**Joseph does:**
Transfer the validated breadboard circuit to perfboard following perfboard-layout.md. Perform continuity checks before inserting components.

**Joseph confirms:**
Perfboard build complete and continuity checks passed.

---

## Step 6 — Soldered Board Validation

**Claude Code does:**
Nothing new — Joseph re-runs the full testing.md procedure (Steps 4 and 4.6) against the soldered board.

**Joseph does:**
Power up the soldered board. Re-run full sensor and enhancement validation. Confirm behavior identical to breadboard.

**Joseph confirms:**
Soldered board validated. Report any differences.

**Claude Code does (if needed):**
Document any differences or fixes.

---

## Step 7 — Physical Mount

**Claude Code does:**
Create `components/garage-radar/mounting.md` — physical installation guide including:
- Recommended mounting height and angle for workbench coverage
- Mount the perfboard vertically — perpendicular to the pegboard surface — LD2412 antenna face pointing horizontally toward workbench
- LEDs visible from the workbench — confirm orientation during layout
- Standoff assembly: M3 male-female standoffs through perfboard corner holes to pegboard. Standoffs space the board away from surface for USB cable clearance and serve as mounting attachment points.
- USB cable routing notes
- Detection angle: ±75° (150° total) — aim to avoid picking up garage door or driveway

**Joseph does:**
Mount on pegboard following mounting.md. Route and secure USB cable.

**Joseph confirms:**
Unit mounted. MQTT still publishing correctly after installation.

---

## Step 8 — Home Assistant / Node-RED Integration

**Claude Code does:**
Before writing any automation code, investigate:
- Examine Node-RED flows for the 20-minute presence timeout
- Examine HA automations for any garage presence timeout logic
- Identify how Ring camera and back door sensor inputs feed the presence virtual switch
- Document findings in `components/garage-radar/integration-notes.md` (append to existing)

Then create `components/garage-radar/integration.md`:
- Where to add `jctsh/components/garage-radar/state` as a new additive presence input
- How to wire in parallel with existing inputs
- Confirmation that the 20-minute timeout applies equally to all inputs
- Any Node-RED flow or HA automation changes required

**Joseph does:**
Implement integration following integration.md. Do not remove or modify existing inputs.

**Joseph confirms:**
Integration complete. Garage-radar wired in as additive presence input.

---

## Step 9 — End-to-End Validation

**Claude Code does:**
Create `components/garage-radar/end-to-end-test.md` — full system validation including:
- Test case 1: Sit still at workbench for 25 minutes — garage door stays open, lights stay on
- Test case 2: Leave garage, confirm presence clears after 20 minutes, automation triggers
- Test case 3: Robin enters while Joseph is at workbench — lights do not toggle off
- How to monitor SmartThings virtual switch state during testing
- What to check if any test case fails
- Note: Temporarily reduce HA presence timeout to 1–2 minutes during testing — restore to 20 minutes after
- Note: Simulate nobody present by stepping outside ±75° detection cone or covering LD2412 antenna face with cardboard

**Joseph does:**
Run all three test cases.

**Joseph confirms:**
Report results for each test case.

**Claude Code does (if needed):**
Diagnose failures and update integration.md or automation configuration.

---

## Step 10 — Final Documentation

**Claude Code does:**
- Create `components/garage-radar/README.md` — permanent component reference: what it does, hardware, wiring, GPIO assignments, MQTT topics (data and log flows), LED indicators, integration points, watchdog, SmartThings device, known behaviors, tuning notes, pinout PNG reference
- Create `core/node-red/watchdog-README.md` — permanent reference for the watchdog flow: what it monitors, how it works, how to add new components (automatic via wildcard — no action needed), alert path, how to test
- Update root `README.md` — add garage-radar to Components list
- Update root `CLAUDE.md` — confirm garage-radar account is in credentials table; add watchdog flow to the repo layout and architecture sections
- Update `JCTsh-Parts-Inventory.md` — add inventory update log entry for this project

---

## Future Enhancement — Split Still vs. Moving Targets as Separate Inputs

`has_still_target` and `has_moving_target` are already published as separate MQTT topics. Could be used independently for finer-grained automation (e.g. only close door if no moving target regardless of still target). Defer until basic presence detection is proven stable.

## Future Enhancement — Enclosure Lid

Add acrylic top panel if dust accumulation becomes a problem. Cut to perfboard footprint, held by same standoffs. Defer until evidence of dust problem.

## Future Enhancement — Detection Zone Tuning

ESPHome LD2412 component supports per-zone sensitivity. Tune if false positives from garage door or driveway occur. Defer until evidence of false positives.

## Future Enhancement — Salt Sensor Watchdog Retrofit

The salt sensor (Arduino C++) does not currently publish a heartbeat. Add a heartbeat to its sketch so it benefits from the Node-RED watchdog flow. Separate project — do not block garage radar on it.

---

## Notes for Claude Code

- **Read first:** JCTsh-Build-Standards.md and CLAUDE.md before beginning any step
- **ESPHome version:** Native LD2412 component requires 2025.8.0 or later. Verify before flashing.
- **UART:** Hardware UART2 only. GPIO16 RX, GPIO17 TX. TX/RX orientation is the most common wiring error — LD2412 TX → ESP32 RX (GPIO16), LD2412 RX → ESP32 TX (GPIO17).
- **3.3V power:** LD2412 from ESP32 3.3V pin only — no level shifting needed.
- **LD2412 antenna:** Blank face (no components) is the antenna. Points horizontally toward workbench. Nothing metal in front of it.
- **Perfboard orientation:** Vertical mount, perpendicular to pegboard. Antenna faces outward. USB accessible from back/bottom. LEDs visible from front.
- **Detection:** 9m max, ±75° cone. Aim to avoid garage door and driveway.
- **ESP32 pin labels:** Face down in breadboard. Pinout PNG in component directory. Mark GPIO16, GPIO17, GPIO25, GPIO26 with masking tape.
- **LED GPIOs:** GPIO25 = green (presence). GPIO26 = yellow (virtual switch status). 330Ω resistors. Clean output GPIOs, no boot conflicts.
- **Yellow LED source:** ESPHome mqtt_subscribe to `jctsh/components/garage-presence-vswitch/state`.
- **Log format:** JSON to `jctsh/components/garage-radar/log` — `{ "component": "garage-radar", "category": "<cat>", "message": "<text>" }`. Do NOT include timestamps. Valid categories: MQTT, System, Sensor, Alert, Test. Node-RED wildcard handles routing automatically — no per-component Node-RED changes needed for logging.
- **Heartbeat:** Publish every 5 minutes to both `/log` (as System log entry) and `/heartbeat` (as JSON for watchdog). Node-RED watchdog wildcard `jctsh/+/+/heartbeat` catches it automatically.
- **Watchdog flow:** New infrastructure — does not yet exist. Build it as part of Step 4.5. Lives at `core/node-red/watchdog.flow.json`. Uses wildcard heartbeat subscription. Alerts via HA REST API → HA companion app → Pixel 10 Pro. Examine existing Node-RED flows before building to match established style.
- **HA REST API notification endpoint:** `POST http://raspberrypi.local:8123/api/services/notify/mobile_app_pixel_10_pro`. HA long-lived access token stored in Node-RED credentials — do not hardcode.
- **SmartThings path:** Node-RED → HA REST API (port 8123) → HA entity → SmartThings. No other path. Examine salt sensor implementation as reference before writing.
- **MQTT account:** `garage-radar` account listed in CLAUDE.md credentials table — confirmed created during Steps 1–4. If recreation needed: `sudo mosquitto_passwd -b /etc/mosquitto/passwd garage-radar <password>` then `sudo chown root:mosquitto /etc/mosquitto/passwd` then `sudo systemctl restart mosquitto`.
- **MQTT topics:** Primary `jctsh/components/garage-radar/state`. Sub-topics: `/still`, `/moving`, `/log`, `/heartbeat`.
- **ESPHome secrets:** Use `!secret` references. Stored in `components/garage-radar/secrets.yaml` (gitignored).
- **Timeouts:** 30-second ESPHome timeout = sensor smoothing only. 20-minute HA/Node-RED timeout = presence decision. Document both distinctly — do not confuse them.
- **Step 8 investigation:** Where the 20-minute timer lives (Node-RED vs HA) was not confirmed during planning. Investigate before writing integration code.
- **Additive integration:** Radar is new input alongside Ring camera and back door sensor. Nothing existing removed or modified.
- **OTA:** After first USB flash, all subsequent updates via OTA. Document OTA command in flashing.md.
- **Testing shortcut:** Temporarily reduce HA presence timeout to 1–2 minutes for end-to-end testing. Restore to 20 minutes after.
- **Parts inventory:** Green/yellow LEDs confirmed on hand. 330Ω resistors confirmed on hand. M3 standoffs selection on hand. Female headers selection on hand. Consult JCTsh-Parts-Inventory.md before adding to BOM.
- **Step 10:** Update JCTsh-Parts-Inventory.md log, root README.md, and root CLAUDE.md (credentials table + architecture sections for watchdog flow).