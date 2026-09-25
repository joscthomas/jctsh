# Salt Sensor — Component Context

ESP32-based water softener salt level monitor. Part of the JCTsh monorepo.
See `jctsh/CLAUDE.md` for monorepo-wide conventions.

## Architecture
- **ESP32 (ESPHome)** reads JSN-SR04T ultrasonic sensor, publishes sensor data and log
  messages to MQTT every 12 hours, plus a heartbeat every 30 minutes
- **Mosquitto** broker runs on Raspberry Pi (`pi1.local`)
- **Node-RED** applies threshold logic, controls HA switches via REST API
- **Home Assistant** — alert/control switches are HA-native (Template Switch helpers,
  CARD-0261, 2026-09-12), exposed to Google Assistant via HA's own native integration
  (not SmartThings — that dependency was removed, see `JCTsh-Build-Standards.md` §6.4)
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
3. `HA_TOKEN` is read from the systemd-level `/home/pi/.node-red/environment` (CARD-0280) — do
   not re-enter it as a tab-scoped Environment Variable (a manual paste corrupted it once, CARD-0261)
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

## Open Work
- CARD-0335 — boot-time heartbeat retrofit (Build Standards §4.1).
- CARD-0067 — 3D-printed enclosure (Planning).

---

Card history archived to `card-archive.md` (CARD-0290) — on-demand only, not part of routine reading.
