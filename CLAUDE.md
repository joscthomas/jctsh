# JCTsh — Monorepo Context

Smart home automation monorepo. See `components/<name>/CLAUDE.md` for component-specific context.

## Repository Layout
```
jctsh/
├── components/
│   ├── salt-sensor/          — ESP32 water softener salt level sensor
│   ├── garage-radar/         — 24GHz mmWave workbench presence radar (ESPHome + LD2412)
│   ├── garage-presence/      — Garage presence countdown timer (HA-only)
│   └── automatic-garage-door-opener-closer/  — Automated garage door
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

## Environmental Data Architecture

JCTsh includes a multi-source environmental sensor platform. The payload schema,
Google Sheets archive design, Node-RED wildcard data handler pattern, Weather
Underground integration, and planned device family are defined in:

`JCTsh-Environmental-Data-Architecture.md` (repo root)

All environmental sensor components must conform to the standard defined there
before Phase 3 planning is considered complete.

## Infrastructure
| Service | Host | Access |
|---|---|---|
| MQTT broker (Mosquitto) | `raspberrypi.local` / `100.70.162.24` | port 1883 |
| Node-RED | `raspberrypi.local` / `100.70.162.24` | port 1880 |
| Log dashboard | `raspberrypi.local` / `100.70.162.24` | port 80 — requires Basic Auth (user: `jctsh`) |
| Home Assistant | `raspberrypi.local` / `100.70.162.24` | port 8123 |

Pi primary hostname: `raspberrypi.local` — do not change. Fixed IP: `192.168.1.117` (DHCP reservation set on router). Use the IP directly if `.local` resolution fails. Timezone: `America/Phoenix` (MST, UTC-7, no DST). Tailscale IP: `100.70.162.24` — use this for remote access from outside the home network.

## Remote Access
Tailscale is installed on the Pi. Connect any device to the same Tailscale account
to access all local services remotely — no port forwarding, no public IP exposure.

| Device | Access |
|---|---|
| Pi (server) | Tailscale IP `100.70.162.24` — always reachable when Tailscale is running |

Install Tailscale: tailscale.com/download (Windows/Mac/Linux) or app store (iOS/Android).
Sign in with the same account and all services are reachable via `100.70.162.24`.

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
Home Assistant is the bridge to SmartThings — **there is no other path.** Do not call
the SmartThings REST API (api.smartthings.com) directly. That API requires a SmartThings
Personal Access Token, which we do not use. All SmartThings interaction goes through HA:

```
Node-RED → HA REST API (port 8123) → SmartThings integration → SmartThings device
```

HA is confirmed connected with the SmartThings integration active. The salt sensor
switches (`switch.salt_critical_alert`, `switch.salt_low_alert`, `switch.salt_full_reset`,
`switch.salt_test_mode`) are HA entities that HA syncs to SmartThings. Future components
that need SmartThings alerts or control should follow the same pattern: create virtual
switches in SmartThings, expose them as HA entities, control via Node-RED → HA REST API.

To expose a sensor (not a switch) to SmartThings — e.g. a motion sensor — use the HA
SmartThings integration's entity-exposure feature (Settings → Devices & Services →
SmartThings → Configure) to push the existing HA entity to SmartThings directly. No
virtual device and no SmartThings PAT required.

## Credentials

All credentials are kept off-disk and out of source control.

### MQTT
Mosquitto requires auth (`allow_anonymous false`). Each component has its own account:

| Account | Used by |
|---|---|
| `jctsh-log-server` | Python log server |
| `nodered` | Node-RED |
| `homeassistant` | Home Assistant MQTT integration |
| `garage-radar` | garage-radar ESPHome device |
| `salt-sensor` | salt-sensor ESP32 sketch |
| `front-porch-temp-sensor` | front-porch-temp-sensor ESPHome device |

Passwords are stored in:
- **Log server** — `/etc/jctsh/log-server.env` on the Pi (injected via systemd `EnvironmentFile`)
- **ESPHome components** — `components/<name>/secrets.yaml` (gitignored)
- **Arduino components** — `components/<name>/secrets.h` (gitignored)
- **Node-RED** — broker node credentials stored encrypted by Node-RED

**Mosquitto passwd ownership gotcha:** `sudo mosquitto_passwd` resets `/etc/mosquitto/passwd` group to `root`. After any password change, run:
```bash
sudo chown root:mosquitto /etc/mosquitto/passwd
sudo systemctl restart mosquitto
```

**HA MQTT integration gotcha:** HA's MQTT broker credentials are configured through the UI only (Settings → Devices & Services → MQTT → Configure) — not in any config file. Easy to miss during password rotations. If HA MQTT credentials are wrong, all ESPHome entities go unavailable and automations that depend on them will misbehave. Always update HA alongside Node-RED and device secrets when rotating MQTT passwords.

### Log Dashboard
HTTP Basic Auth — username `jctsh`, password in `/etc/jctsh/log-server.env` as `DASHBOARD_PASS`.

### SSH
Passwordless SSH from this machine via key auth (`~/.ssh/id_ed25519`). Pi password is set but not needed for normal use — store it securely offline.

## Future Components
Use **ESPHome YAML** (not Arduino C++) for new ESP-based components:
1. Create `components/<name>/` with a `.yaml` file
2. Add entry to root `README.md`
3. Use MQTT namespace: `jctsh/<type>/<name>/<message-type>`
4. Publish logs to `jctsh/<type>/<name>/log` in standard JSON format
5. Add `<name>.flow.json` for Node-RED logic
6. Create a dedicated MQTT account: `sudo mosquitto_passwd -b /etc/mosquitto/passwd <name> <password>`, then fix ownership (see Credentials section)
7. Add credentials to `components/<name>/secrets.yaml` (gitignored)

### ESP32 GPIO pin guidance
Safe pins for digital output: **GPIO32, GPIO33**, GPIO18, GPIO19, GPIO21, GPIO22, GPIO23, GPIO27.

Pins to avoid:
| Pin(s) | Reason |
|---|---|
| GPIO25, GPIO26 | DAC1/DAC2 — GPIO25 confirmed broken for digital output in ESPHome/Arduino framework (post-boot DAC init reconfigures the pin). Avoid both as a precaution. |
| GPIO34–39 | Input-only — no output capability |
| GPIO6–11 | Connected to flash — do not use |
| GPIO0, GPIO2, GPIO12, GPIO15 | Strapping pins — affect boot mode if driven at reset |

## Backlog for Future work
For the next time we open a component for changing.
- garage-radar: closing garage door triggers a false presence detection (moving door passes through radar detection cone). Deferred until after perfboard build. Options: (a) adjust radar tilt angle to exclude the door path — need a method to determine correct angle during calibration; (b) accept it — 15-minute timer means lights go off eventually regardless.
- salt-sensor: migrate from Arduino C++ to ESPHome. Device side maps cleanly (ultrasonic platform, median filter, 12h interval, LED blink via globals). Logic side: threshold/percentage calculation + SmartThings switch control moves from Node-RED to HA automations; Node-RED flow deleted. Hard part: test mode needs redesign (Node-RED injects fake readings — ESPHome has no equivalent; replace with an HA script that triggers the threshold automation with a synthetic distance value). GPIO 2 and 15 are strapping pins but currently working — not a blocker. Do this migration before perfboard transfer: ESPHome initializes hardware differently than Arduino and if either strapping pin causes a boot issue it's much easier to rewire on breadboard than cut perfboard traces.