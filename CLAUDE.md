# JCTsh — Monorepo Context

Smart home automation monorepo. One component deployed: `salt-sensor`.
See `components/<name>/CLAUDE.md` for component-specific context.

## Repository Layout
```
jctsh/
├── components/salt-sensor/   — ESP32 water softener salt level sensor
└── core/
    ├── logging/              — Python MQTT log server (runs on Pi)
    ├── node-red/             — Node-RED settings + broker config (version control copies)
    ├── mqtt/                 — Mosquitto config (version control copy)
    └── homeassistant/        — Home Assistant config (version control copy, do not modify)
```

## Architecture

### Component Roles

| Component | Role |
|---|---|
| **ESP32 / ESPHome** | Edge sensor. Reads physical hardware (distance, temperature, contact, etc.) and publishes readings to MQTT. No logic beyond "take a reading and report it." |
| **Mosquitto MQTT broker** | Message bus. Decouples every component from every other. Nothing talks directly to anything else — everything publishes to a topic and subscribes to topics. |
| **Node-RED** | The brain. Subscribes to MQTT topics, applies logic (thresholds, timing, transformations), triggers actions, and publishes results. Also routes sensor log messages to the Python log server. |
| **Python log server** | The record keeper. Receives log messages and makes them browsable at `http://raspberrypi.local/`. Provides persistent history of what every component has reported. |
| **Home Assistant** | Integration layer only — not logic. Bridges the local JCTsh ecosystem to SmartThings → Google Home, Pixels, and voice control. |

### Message Flow

```
Physical world
      ↓
  ESP32 sensor
      ↓  (MQTT publish)
  jctsh/<type>/<component>/<message-type>
      ↓
  Mosquitto broker
      ↓  (subscribed)
  Node-RED
      ↓              ↓
  Logic/actions    Log topic
                      ↓
               Python log server
               (http://raspberrypi.local/)
      ↓
  Home Assistant
      ↓
  SmartThings
      ↓
  Google Home / Pixels / Automations
```

### Two Parallel Flows

Every component produces two message streams:
- **Data flow** — `jctsh/<type>/<component>/<message-type>` — sensor readings and state that drive automations.
- **Log flow** — `jctsh/<type>/<component>/log` — diagnostic and status messages routed by Node-RED to the Python log server for visibility and troubleshooting.

## Infrastructure
| Service | Host | Access |
|---|---|---|
| MQTT broker (Mosquitto) | `raspberrypi.local` | port 1883 |
| Node-RED | `raspberrypi.local` | `http://raspberrypi.local:1880/` |
| Log dashboard | `raspberrypi.local` | `http://raspberrypi.local/` |
| Home Assistant | `raspberrypi.local` | `http://raspberrypi.local:8123/` |

Pi primary hostname: `raspberrypi.local` — do not change.

## MQTT Topic Convention
```
jctsh/<type>/<component>/<message-type>
```
Examples:
- `jctsh/sensors/salt-sensor/data` — sensor readings
- `jctsh/sensors/salt-sensor/status` — status commands
- `jctsh/sensors/salt-sensor/log` — log messages

## Log Message Format
All components publish logs as JSON to `jctsh/<type>/<component>/log`:
```json
{ "component": "salt-sensor", "category": "MQTT", "message": "Connected." }
```
Valid categories: `MQTT`, `System`, `Sensor`, `Alert`, `Test`
Timestamps are added by the log server on receipt — do not include them in the payload.

## Watchdog Heartbeat
`core/logging/log_server.py` publishes an hourly heartbeat to `jctsh/core/log-server/log`:
```json
{ "component": "jctsh-core", "category": "System", "message": "Watchdog: alive." }
```
This confirms the log server and MQTT broker are alive. It appears in the dashboard under
component `jctsh-core`. No Node-RED involvement — core infrastructure only.

## Core Files (Pi runtime — not directly editable here)
These files under `core/` are version-controlled snapshots only. The live copies
are on the Pi. To update: edit on Pi, then copy back here.
- `core/node-red/core.flow.json` — MQTT broker node (import first when re-importing flows)
- `core/node-red/settings.js` — Node-RED settings (contains bcrypt password hash)
- `core/mqtt/mosquitto.conf` — Mosquitto configuration
- `core/homeassistant/configuration.yaml` — HA config (do not modify)
- `core/logging/log_server.py` — deployed to `/home/pi/jctsh/core/logging/`

## Log Server Deployment
After editing `core/logging/log_server.py`:
```bash
scp core/logging/log_server.py pi@raspberrypi.local:/home/pi/jctsh/core/logging/
ssh pi@raspberrypi.local "sudo systemctl restart jctsh-logging"
```

## SmartThings Integration
Home Assistant is the bridge to SmartThings — there is no other path. Any JCTsh
component that needs to reach a SmartThings device must go through HA:

```
Node-RED → HA REST API (port 8123) → SmartThings integration → SmartThings device
```

HA is confirmed connected with the SmartThings integration active. The salt sensor
switches (`switch.salt_critical_alert`, `switch.salt_low_alert`, `switch.salt_full_reset`,
`switch.salt_test_mode`) are HA entities that HA syncs to SmartThings. Future components
that need SmartThings alerts or control should follow the same pattern: create virtual
switches in SmartThings, expose them as HA entities, control via Node-RED → HA REST API.

## Future Components
Use **ESPHome YAML** (not Arduino C++) for new ESP-based components:
1. Create `components/<name>/` with a `.yaml` file
2. Add entry to root `README.md`
3. Use MQTT namespace: `jctsh/<type>/<name>/<message-type>`
4. Publish logs to `jctsh/<type>/<name>/log` in standard JSON format
5. Add `<name>.flow.json` for Node-RED logic
