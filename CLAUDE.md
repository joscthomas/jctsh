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

## Open Question — Do Not Implement Until Resolved
Home Assistant is running in Docker on the Pi with minimal configuration. Its role
as a SmartThings bridge has not been confirmed. Before implementing any JCTsh ↔ HA
integration beyond what salt-sensor already uses, confirm:
- Is HA the active SmartThings bridge, or is SmartThings accessed another way?
- Should future components route through HA or communicate independently via MQTT?

## Future Components
Use **ESPHome YAML** (not Arduino C++) for new ESP-based components:
1. Create `components/<name>/` with a `.yaml` file
2. Add entry to root `README.md`
3. Use MQTT namespace: `jctsh/<type>/<name>/<message-type>`
4. Publish logs to `jctsh/<type>/<name>/log` in standard JSON format
5. Add `<name>.flow.json` for Node-RED logic
