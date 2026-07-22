# JCTsh — Monorepo Context

Smart home automation monorepo. See `components/<name>/CLAUDE.md` for component-specific context. For what's installed and running on the Pi, see `SOFTWARE-ENVIRONMENT.md`.

## Session Start

At the start of every Claude Code session in this repo, read the Build column of `kanban-board.md` for context on what's actively in progress before doing anything else.

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
    ├── data-pipeline/        — Environmental data pipeline: Apps Script, architecture doc, Node-RED handler flow
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

`core/data-pipeline/JCTsh-Environmental-Data-Architecture.md`

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

### Home Assistant Docker Setup
HA runs in a Docker container (`ghcr.io/home-assistant/home-assistant:stable`) managed by Docker's `unless-stopped` restart policy. The authoritative configuration is in `core/homeassistant/docker-compose.yml`.

Config volume: `/home/pi/homeassistant:/config` (this is what the repo's `core/homeassistant/` snapshots).

To manage the container:
```bash
# Restart HA (e.g. after config change)
docker restart homeassistant

# Recreate from compose file (e.g. after image update or docker-compose.yml change)
cd /home/pi && docker compose up -d

# View live logs
docker logs -f homeassistant
```

DNS is explicitly pinned to `8.8.8.8` / `8.8.4.4` in both `docker-compose.yml` and `/etc/docker/daemon.json`. This prevents a recurrence of the June 2026 outage where HA lost all cloud connectivity because the container had a stale DHCP-assigned DNS server (`192.168.1.222`) baked in at creation time.

## Remote Access
Tailscale is installed on the Pi. Connect any device to the same Tailscale account
to access all local services remotely — no port forwarding, no public IP exposure.

| Device | Access |
|---|---|
| Home Pi (server) | Tailscale IP `100.70.162.24` — always reachable when Tailscale is running |
| RV Pi (coachproxyos) | Tailscale IP `100.90.246.43` — eRVin dashboard at `http://100.90.246.43` |

Install Tailscale: tailscale.com/download (Windows/Mac/Linux) or app store (iOS/Android).
Sign in with the same account and all services are reachable via `100.70.162.24`.

### Nabu Casa (Home Assistant Cloud)
Nabu Casa is active on this HA instance (account: `joscthomas@gmail.com`). It provides an external HTTPS URL for HA and is **required** for the SmartThings integration — SmartThings uses OAuth during setup, and OAuth needs an externally reachable callback URL that only Nabu Casa (or a manual tunnel) can provide.

If HA ever needs to be re-set-up from scratch, confirm Nabu Casa is signed in (Settings → Home Assistant Cloud) before attempting to re-add SmartThings, or the integration setup will fail with "No OAuth services available."

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
Timestamps are added by the log server on receipt — do not include them in the payload.

**Category guide** — each category maps to a distinct layer of the stack:

| Category | What it covers | Examples |
|---|---|---|
| `System` | Device health and operational state | Online/boot, WiFi reconnect, heartbeat |
| `MQTT` | Transport layer — the broker connection itself | Connected, disconnected, LWT |
| `Sensor` | Physical-world data and state transitions | Presence detected/cleared, distance, salt % |
| `Alert` | Threshold crossings requiring human attention | Salt warning/critical, API failures |
| `Test` | Messages generated during test mode | Simulated readings, test mode on/off |

The dividing line between `System` and `MQTT`: if the message is about the *device* (booted, alive, WiFi), use `System`. If it's specifically about the *broker connection* (connected, disconnected, subscribed), use `MQTT`.

**Collapsing convention:** Any repeating status message that should be collapsed into a single dashboard row (count + time range) must start with `"Heartbeat - "`. The log server groups consecutive same-state messages with this prefix per component. Messages without this prefix only collapse when consecutive identical runs are uninterrupted — unreliable for high-frequency or long-lived repeats.

## Watchdog Heartbeat
`core/logging/log_server.py` publishes an hourly heartbeat to `jctsh/core/log-server/log`:
```json
{ "component": "jctsh-core", "category": "System", "message": "Watchdog: alive." }
```
This confirms the log server and MQTT broker are alive. It appears in the dashboard under
component `jctsh-core`. No Node-RED involvement — core infrastructure only.

## Core Files (Pi runtime)
The repo is the source of truth. Edit files here, then deploy to the Pi — do not edit on the Pi directly or the repo will fall out of sync. The HA config directory (`/home/pi/homeassistant/`) is owned by `pi` so plain `scp` works in both directions.

- `core/node-red/core.flow.json` — MQTT broker node (import first when re-importing flows)
- `core/node-red/watchdog.flow.json` — component heartbeat watchdog; wildcard `jctsh/+/+/heartbeat`; push notification via HA companion app if silent for 10 min. See `core/node-red/watchdog-README.md`.
- `core/data-pipeline/environmental-data.flow.json` — Node-RED wildcard data handler (`jctsh/components/+/data`) → GPS lookup → Google Sheets
- `core/data-pipeline/environmental-data.gs` — Google Apps Script source (paste into Apps Script editor; redeploy after any change)
- `core/data-pipeline/JCTsh-Environmental-Data-Architecture.md` — payload schema, Sheets archive design, Node-RED handler pattern
- `core/node-red/settings.js` — Node-RED settings (contains bcrypt password hash)
- `core/mqtt/mosquitto.conf` — Mosquitto configuration
- `core/homeassistant/configuration.yaml` — HA config (do not modify)
- `core/homeassistant/automations.yaml` — HA automations. Deploy and reload:
  ```bash
  scp core/homeassistant/automations.yaml pi@raspberrypi.local:/home/pi/homeassistant/automations.yaml
  curl -s -X POST http://raspberrypi.local:8123/api/services/automation/reload \
    -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json"
  ```
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

## Internet Exposure and Security Posture

### MQTT broker internet exposure (as of 2026-06-12)

Port 1883 is forwarded from the internet to the Pi (192.168.1.117) via DuckDNS dynamic DNS + router port forward. The hiking-monitor ESP32 uses this to reach the broker from the Pixel cellular hotspot when away from home.

**Mitigations in place:**
- All Mosquitto accounts use strong random passwords (20+ chars, alphanumeric)
- fail2ban watches `/var/log/mosquitto/mosquitto.log` — bans any IP making more than 10 connections in 60 seconds for 1 hour. Stops port scanners before they can attempt brute force.
- Each MQTT account is scoped to its component; no anonymous access.

**Risks accepted:**
- MQTT 3.1.1 sends credentials and all sensor data in cleartext. Your ISP can see the username, password, and every reading in transit. A man-in-the-middle on the internet path could also see and modify traffic.
- Metadata (connection timing, frequency) is always visible regardless of encryption — reveals home occupancy patterns.
- Brute force: with 20-char random passwords the keyspace is not practically exhaustable. fail2ban makes even low-rate attacks impractical.
- If credentials were stolen: an attacker could publish fake sensor readings or (without ACLs) subscribe to all component topics, including garage presence data.

**Not yet mitigated — in backlog:**
- TLS (port 8883): would encrypt credentials and data in transit, eliminating the cleartext risk. See backlog entry.
- Mosquitto ACLs: would limit each account to its own component topics, reducing the blast radius of a compromised credential.

### LAN security

Mosquitto on the LAN (port 1883 at 192.168.1.117) is also cleartext. Any device on JCTnet1 can passively capture MQTT traffic. Acceptable for a home network; no mitigation planned.

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
| `hiking-monitor` | hiking-monitor ESPHome device |
| `photo-server` | photo-server heartbeat script (Docker/Immich health check) |

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

**Hostname convention:** Every ESP32 component must set its network hostname to match its component name so it is discoverable as `<name>.local`. ESPHome does this automatically via `esphome: name:`. For any Arduino sketch, call `WiFi.setHostname("<name>");` before `WiFi.begin()`. Reserve the DHCP IP on the router and record the IP, hostname, and MAC in `jctsh-network.md`.

### ESP32 GPIO pin guidance
Safe pins for digital output: **GPIO32, GPIO33**, GPIO18, GPIO19, GPIO21, GPIO22, GPIO23, GPIO27.

Pins to avoid:
| Pin(s) | Reason |
|---|---|
| GPIO25, GPIO26 | DAC1/DAC2 — GPIO25 confirmed broken for digital output in ESPHome/Arduino framework (post-boot DAC init reconfigures the pin). Avoid both as a precaution. |
| GPIO34–39 | Input-only — no output capability |
| GPIO6–11 | Connected to flash — do not use |
| GPIO0, GPIO2, GPIO12, GPIO15 | Strapping pins — affect boot mode if driven at reset |

## Concurrent Sessions

Multiple Claude Code sessions (or the user directly) may edit files in this repo at the same time. Git has no file-locking or checkout-exclusivity model (unlike SVN/Perforce) — two sessions sharing this working directory get no automatic protection against clobbering each other.

The real risk is **staleness between reading a file and writing it back**, not how long a file stays "open" (tool calls never hold a file open across turns). Practices:

- **Re-read shared files fresh immediately before editing them**, especially `kanban-board.md` — don't rely on a mental model of its content from earlier in the conversation. A second session may have added, closed, or moved cards since you last looked.
- **Never `git add -A` or `git add .`** — always stage specific files/paths. A blanket add is what sweeps up another session's unrelated, held-back edits and creates real collisions.
- **Prefer Edit over Write for shared files.** Edit's exact-string match fails safely if the content changed underneath you; Write blindly overwrites whatever is on disk.
- **Commit `kanban-board.md` as a whole at natural checkpoints** (a card closing, a card added, meaningful progress) rather than surgically splitting commits per card.
- **Reserve `git worktree` / branch isolation for the narrow case of two sessions actively rewriting the *same* file at the same time** — it's not a default. Isolating a session onto its own branch means its work is invisible to anything reading `main` directly (e.g. the live kanban page pulled from `main` on GitHub) until an explicit merge, which is unnecessary overhead when sessions are touching disjoint files.

## Backlog

See `kanban-board.md` (repo root) — lightweight kanban with all cards (Backlog → Planning → Design → Build → Done).