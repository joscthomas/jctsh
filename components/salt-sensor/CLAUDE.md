# Salt Sensor — Component Context

ESP32-based water softener salt level monitor. Part of the JCTsh monorepo.
See `jctsh/CLAUDE.md` for monorepo-wide conventions.

## Architecture
- **ESP32 (ESPHome)** reads JSN-SR04T ultrasonic sensor, publishes sensor data and log
  messages to MQTT every 12 hours, plus a heartbeat every 30 minutes
- **Mosquitto** broker runs on Raspberry Pi (`pi1.local`)
- **Node-RED** applies threshold logic, controls HA switches via REST API
- **Home Assistant** bridges to SmartThings for alerts and switch control
- **SmartThings** — primary control surface for alert switches
- **Log dashboard** — `http://pi1.local/` (Python log server on Pi)

## ESPHome Migration (CARD-0004)
Migrated from Arduino C++ to ESPHome. The old sketch is preserved for reference at
`archive/salt-sensor-v3-arduino/` (do not use — no longer flashed to the device).
Behavior is intentionally unchanged: same 12-hour 15-sample-median reading cycle, same
MQTT topics/payloads, same LED state machine, same thresholds (owned by Node-RED, not
touched by this migration). The only functional addition is a 30-minute heartbeat
(`jctsh/sensors/salt-sensor/heartbeat`), which the device didn't previously have —
CARD-0021 flagged salt-sensor as showing `?` on the status dashboard until this existed.

**MQTT birth_message gotcha:** ESPHome's default MQTT birth topic is
`<topic_prefix>/status`. Since this component's topic_prefix is `jctsh/sensors/salt-sensor`,
that default would collide with the `.../status` topic Node-RED already owns (used to push
`ok`/`warning`/`critical`/`error` to the ESP32 to drive the LEDs). `birth_message:` is
explicitly disabled in `salt-sensor.yaml`'s `mqtt:` block for this reason — do not remove
that override or re-enable the default birth message.

**Strapping pins (GPIO2, GPIO15) — resolved:** the Arduino version's original LED wiring
used GPIO2/GPIO15 (strapping pins) and booted fine on the breadboard, but for the perfboard
build (CARD-0004 follow-on) all three LEDs were moved off strapping pins entirely: Red
GPIO2→GPIO32, Yellow GPIO15→GPIO33, Green GPIO4→GPIO27. GPIO25/26 (DAC1/DAC2) were
considered for the move since they sit physically next to GPIO32/33 but were ruled out —
GPIO25 is confirmed broken for digital output in ESPHome/Arduino, GPIO26 avoided as a
precaution. GPIO5 (ultrasonic trig) still logs a startup strapping-pin warning but is
unaffected by this change.

## Why v3 Exists — Do Not Regress
v2 used direct SmartThings API calls from the ESP32 with a Personal Access Token.
SmartThings PATs expire after 24 hours, causing silent failures. v3 eliminates all
direct SmartThings API calls from the ESP32. SmartThings is now reached exclusively
through Node-RED → Home Assistant. Do not introduce any direct SmartThings API calls
or PAT-based authentication anywhere in this component.

## Web Server Removed — Do Not Re-Add
The ESP32 web monitor (`salt-sensor.local` web UI) was removed in the JCTsh restructure.
Log messages are published via MQTT to `jctsh/sensors/salt-sensor/log` and displayed in
the centralized log dashboard at `http://pi1.local/`. Do not re-add a web server
or in-memory log buffer to the firmware.

## Hardware
- **Board:** ESP32 Dev Module
- **Sensor:** JSN-SR04T Waterproof Ultrasonic

### Pin Assignments
| Pin | GPIO | Notes |
|---|---|---|
| JSN-SR04T Trig | GPIO 5 | Output. Strapping pin — logs a startup warning, unaffected by the LED pin move. |
| JSN-SR04T Echo | GPIO 18 | Input via voltage divider (1kΩ + 2kΩ to GND) |
| Red LED | GPIO 32 | Critical — 220Ω resistor. |
| Yellow LED | GPIO 33 | Warning — 220Ω resistor. |
| Green LED | GPIO 27 | Good — 220Ω resistor. |

### Calibration
| Constant | Value | Meaning |
|---|---|---|
| `FULL_DISTANCE_CM` | 20.4 cm | Sensor-to-salt at 100% full |
| `EMPTY_DISTANCE_CM` | 43.0 cm | Sensor-to-salt at 0% (empty) |

These are HA `input_number` helpers polled by Node-RED (see Calibration section below) —
not firmware constants. The ESP32 publishes raw distance only.

## Network
- DHCP assigned IP (check router for current IP)
- Hostname: `salt-sensor` (set via `esphome: name:`) — OTA password in `secrets.yaml`

## Key Files
- `salt-sensor.yaml` — ESPHome configuration (firmware source of truth)
- `secrets.yaml` — gitignored; WiFi/MQTT/OTA credentials. Never commit.
- `salt-sensor.flow.json` — Node-RED flow (sensor logic only; import after `core.flow.json`)
- `archive/salt-sensor-v3-arduino/` — previous Arduino C++ firmware (reference only, not flashed)
- `archive/water_softener_salt_sensor_v2.ino` — older direct SmartThings version (reference only)

## MQTT Topics
| Topic | Direction | Purpose |
|---|---|---|
| `jctsh/sensors/salt-sensor/data` | ESP32 → Node-RED | `{"distance_cm":25.3}` retained |
| `jctsh/sensors/salt-sensor/status` | Node-RED → ESP32 | `ok` / `warning` / `critical` / `error` (plain string, retained) |
| `jctsh/sensors/salt-sensor/log` | ESP32 → log server | `{"component":"salt-sensor","category":"...","message":"..."}` |
| `jctsh/sensors/salt-sensor/heartbeat` | ESP32 → watchdog | JSON heartbeat, every 30 min — picked up by the `jctsh/+/+/heartbeat` wildcard |

Node-RED also publishes its own operational messages to `jctsh/sensors/salt-sensor/log`
via the `Format log message` function node.

## LED Behavior
| Status | Red | Yellow | Green |
|---|---|---|---|
| `ok` | off | off | solid |
| `warning` | off | blink | off |
| `critical` | blink | off | off |
| `error` | blink | blink | blink |
| `unknown` | off | off | slow blink (alive) |

## Calibration
Calibration values are HA input_number helpers, polled by Node-RED every 60 seconds and
stored in flow context. Node-RED calculates the salt percentage — the ESP32 publishes raw
distance only.

| Helper entity ID | Default | Meaning |
|---|---|---|
| `input_number.salt_full_distance_cm` | 20.4 | Sensor-to-salt distance (cm) when tank is 100% full |
| `input_number.salt_empty_distance_cm` | 43.0 | Sensor-to-salt distance (cm) when tank is 0% empty |

To create in HA: Settings → Helpers → + Create Helper → Number. Set min/max/step
appropriate for your installation. Values take effect within 60 seconds of being saved.

## After Editing the Flow
1. In Node-RED, import `jctsh/core/node-red/core.flow.json` first (broker config) if not already present
2. Import `salt-sensor.flow.json` → Replace existing nodes
3. Re-enter `HA_TOKEN` in Node-RED environment variables (Node-RED UI → Settings → Environment)
4. Deploy

## After Editing the YAML
Compile/flash from `C:\esphome\salt-sensor\`, not the repo path — spaces in
`JCT Documents` break the ESP-IDF compiler. Copy `salt-sensor.yaml` and `secrets.yaml`
there after editing, then:
```
cd C:\esphome\salt-sensor
esphome run salt-sensor.yaml
```
First flash must be via USB (select the COM port when prompted). All subsequent updates
can go over OTA (same command, once the device is on the network). Three rapid LED
flashes at boot confirm a successful reboot (same as the old Arduino version).

## Next Steps
- Flash and field-verify this migration (USB first flash, confirm LED self-test, confirm
  MQTT data/status/log/heartbeat all work end-to-end) — see CARD-0004.
- Confirm Home Assistant role (SmartThings bridge vs. other) before deeper JCTsh integration.

## Card History

**Archived from `tos/kanban-board.md` on 2026-08-22 (CARD-0193)** — 5696B, over the 5000B size threshold.

### CARD-0049 · [enhancement] [salt-sensor] Move from breadboard to perfboard — RESOLVED 2026-07-13
**Status:** Done

**Progress (2026-07-10):** Follow-on to CARD-0004 (ESPHome migration). Moved all three LEDs off their original breadboard pins onto a perfboard-friendly layout: Red GPIO2→GPIO32, Yellow GPIO15→GPIO33, Green GPIO4→GPIO27 — gets Red/Yellow off strapping pins entirely and lines all three LEDs up on the same header row (left pins 7/8/11) for easier soldering. GPIO25/26 (DAC1/DAC2) were considered since they sit physically between GPIO32/33 and GPIO27, but ruled out — GPIO25 is confirmed broken for digital output in ESPHome/Arduino, GPIO26 avoided as a precaution for the same DAC-reinit reason. Trig (GPIO5) and Echo (GPIO18) unchanged.

Updated `salt-sensor.yaml` (wiring comment + `output:` block), `components/salt-sensor/CLAUDE.md`, and `components/salt-sensor/ESP32-project-pins.md` to match. Physical rewiring done; reflashed over OTA and field-verified — LEDs confirmed matching the `ok` status (green solid, red/yellow off) on the new pins, MQTT `/data` and `/status` reporting normally post-flash.

**Planning (2026-07-13):** wrote `components/salt-sensor/perfboard-layout.md` — modeled on hiking-monitor's perfboard-layout.md (Assembly Sequence → Pre-Power Checks → power-on/reboot verification), scaled down for salt-sensor's much simpler circuit (no I2C, no battery chain, no display). Worked through bus planning explicitly before the soldering steps: a ground bus is warranted (5 consumers: 3 LEDs, JSN-SR04T GND, Echo divider) and gets built with 2 spare tap points for future additions; a 5V/VIN bus is *not* warranted (only one consumer beyond the source — a direct point-to-point wire is equivalent and simpler); confirmed no other net (each LED drive line, Trig, Echo) has 3+ consumers, so no other bus is warranted either. 12-step assembly sequence, 18-check pre-power continuity/resistance table, and an explicit power-cycle verification section (cold USB unplug/replug, not just an OTA soft reboot — twice clean, minimum) all written into the doc.

**Build (2026-07-13):** Soldered per `perfboard-layout.md`'s Assembly Sequence — walked step by step interactively (each solder joint confirmed before proceeding to the next).

**Real issue found and fixed:** the physical ESP32 board in hand is a **SparkleIoT XH-32S** module, whose silkscreen pin *order* doesn't match `ESP32-project-pins.md`'s documented position numbering — same GPIO count, different physical layout, despite both nominally being "38-pin ESP32 DevKitC-32" boards. This wasn't caught until mid-build: the Trig wire had been soldered to the pad labeled `RX2` instead of `D5` (the two sit adjacent in a crowded cluster — `D18, D5, TX2, RX2, D4`), found only because Pre-Power Checks were done by reading the actual printed labels rather than trusting the documented table. Fixed by re-soldering Trig to the correct `D5` pad. `D18` (Echo) was double-checked at the same time and confirmed correct. Reference photo of the actual board saved to `components/salt-sensor/sparkleiot-xh-32s-pinout-photo.jpg`.

**Pre-Power Checks:** 19 checks run (not the originally-planned 18) — 2 checks from the hiking-monitor-derived template were dropped as not applicable (this board has no separate USB power-in header; power enters through the ESP32's own onboard USB port), and 3 new isolation checks were added on the spot (`D32`↔`D33`, `D5`↔`D18`, `D5`↔`RX2`, each expected open/no-beep) prompted directly by the `RX2`/`D5` mistake — confirming no solder bridge existed between visually-adjacent pins. **All 19 passed.**

**Power-on test:** LED self-test observed, `Online — ESPHome 2026.4.5, IP: 192.168.1.181, MQTT connected`, `/data` publishing `Salt: 95% (21.5 cm)` — same value as CARD-0049's original 2026-07-10 breadboard field verification, confirming the Echo divider (part of what got fixed) is producing sane readings. LED status confirmed matching (`ok` → solid green, red/yellow off).

**Resolution — reboot/power-cycle verification:** two clean cold power-cycles (physical USB unplug/replug, not just an OTA soft reboot, since this board is USB-powered not battery — a cold cycle exercises WiFi/MQTT reconnect and the LED self-test's boot path a warm reboot wouldn't). Cycle 1 (15:06 MST) and Cycle 2 (15:08 MST) both clean: LED self-test, MQTT reconnect, `Salt: 95% (21.5 cm)` both times. Both closing criteria (perfboard soldered + verified, survives power-cycle on new pins) now met.

**Reflection:** `components/salt-sensor/perfboard-layout.md` rewritten to reference pins by printed label instead of the wrong position numbers, with a prominent Board Note explaining the mismatch, all check results recorded, and the 3 new isolation checks made permanent. Harvested the generalizable lesson into `JCTsh-Build-Standards.md` §1.2 (v1.15): verify against a board's actual silkscreen labels rather than trusting a documented reference table, and add isolation checks between visually-adjacent pin labels to Pre-Power Checks as standard practice.

**Follow-up (2026-07-13):** `ESP32-project-pins.md` rewritten to match the actual SparkleIoT XH-32S board, organized by printed label with GPIO cross-reference (photo saved alongside it). `JCTsh-Perfboard-Build-Template.md` (new, repo root, Build Standards v1.16) generalizes the proven Assembly Sequence → Bus Planning → Pre-Power Checks → Reboot/Power-Cycle structure into a reusable skeleton for future perfboard builds, now that there are two real examples (hiking-monitor, salt-sensor) to draw from.

**Closed 2026-07-13 — Joseph confirmed and directed the close.**

---
