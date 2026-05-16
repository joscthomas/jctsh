# Salt Sensor — Component Context

ESP32-based water softener salt level monitor. Part of the JCTsh monorepo.
See `jctsh/CLAUDE.md` for monorepo-wide conventions.

## Architecture
- **ESP32** reads JSN-SR04T ultrasonic sensor, publishes sensor data and log messages to MQTT every 12 hours
- **Mosquitto** broker runs on Raspberry Pi (`raspberrypi.local`)
- **Node-RED** applies threshold logic, controls HA switches via REST API
- **Home Assistant** bridges to SmartThings for alerts and switch control
- **SmartThings** — primary control surface for alert switches
- **Log dashboard** — `http://raspberrypi.local/` (Python log server on Pi)

## Why v3 Exists — Do Not Regress
v2 used direct SmartThings API calls from the ESP32 with a Personal Access Token.
SmartThings PATs expire after 24 hours, causing silent failures. v3 eliminates all
direct SmartThings API calls from the ESP32. SmartThings is now reached exclusively
through Node-RED → Home Assistant. Do not introduce any direct SmartThings API calls
or PAT-based authentication anywhere in the ESP32 sketch.

## Web Server Removed — Do Not Re-Add
The ESP32 web monitor (`salt-sensor.local`) was removed in the JCTsh restructure.
Log messages are now published via MQTT to `jctsh/sensors/salt-sensor/log` and
displayed in the centralized log dashboard at `http://raspberrypi.local/`.
Do not re-add `WebServer.h`, `ESPmDNS.h`, or any in-memory log buffer to the sketch.

## Hardware
- **Board:** ESP32 Dev Module
- **Sensor:** JSN-SR04T Waterproof Ultrasonic

### Pin Assignments
| Pin | GPIO | Notes |
|---|---|---|
| JSN-SR04T Trig | GPIO 5 | Output |
| JSN-SR04T Echo | GPIO 18 | Input via voltage divider (1kΩ + 2kΩ to GND) |
| Red LED | GPIO 2 | Critical — 220Ω resistor |
| Yellow LED | GPIO 15 | Warning — 220Ω resistor |
| Green LED | GPIO 4 | Good — 220Ω resistor |

### Calibration
| Constant | Value | Meaning |
|---|---|---|
| `FULL_DISTANCE_CM` | 20.4 cm | Sensor-to-salt at 100% full |
| `EMPTY_DISTANCE_CM` | 43.0 cm | Sensor-to-salt at 0% (empty) |

These values are physically measured for this specific installation. Do not change
without re-measuring.

## Network
- DHCP assigned IP (check router for current IP)
- OTA hostname: `salt-sensor` — password in `secrets.h`

## Key Files
- `water_softener_salt_sensor_v3.ino` — ESP32 sketch
- `salt-sensor.flow.json` — Node-RED flow (sensor logic only; import after `core.flow.json`)
- `secrets.h` — gitignored; WiFi/MQTT/OTA credentials. Never commit.
- `archive/water_softener_salt_sensor_v2.ino` — old direct SmartThings version (reference only)

## MQTT Topics
| Topic | Direction | Purpose |
|---|---|---|
| `jctsh/sensors/salt-sensor/data` | ESP32 → Node-RED | `{"distance_cm":25.3,"percent":78}` retained |
| `jctsh/sensors/salt-sensor/status` | Node-RED → ESP32 | `ok` / `warning` / `critical` / `error` |
| `jctsh/sensors/salt-sensor/log` | ESP32 → log server | `{"component":"salt-sensor","category":"...","message":"..."}` |

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

## After Editing the Flow
1. In Node-RED, import `jctsh/core/node-red/core.flow.json` first (broker config) if not already present
2. Import `salt-sensor.flow.json` → Replace existing nodes
3. Re-enter `HA_TOKEN` in Node-RED environment variables (Node-RED UI → Settings → Environment)
4. Deploy

## After Editing the Sketch
Flash via OTA: Arduino IDE → Tools → Port → `salt-sensor at <ip>` → Upload
Three rapid LED flashes confirm successful OTA reboot.

## Next Steps
- MQTT TLS hardening
- Node-RED watchdog heartbeat (hourly publish to `jctsh/sensors/salt-sensor/log`)
- Confirm Home Assistant role (SmartThings bridge vs. other) before deeper JCTsh integration
