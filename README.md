# JCTsh — Smart Home Automation
Joseph C Thomas | Tucson, AZ

DIY smart home automation system built on Raspberry Pi, MQTT, Node-RED, and Home
Assistant — connecting ESP32 sensors, garage automation, an RV coach interface, and
environmental monitoring into a single integrated ecosystem.

---

## System Status

| Component | What it does | Status |
|---|---|---|
| [salt-sensor](components/salt-sensor/) | Water softener salt level monitor with SmartThings alerts | Production |
| [garage-radar](components/garage-radar/) | 24GHz mmWave workbench presence sensor | Production |
| [garage-presence](components/garage-presence/) | Garage presence countdown timer and lights automation | Production |
| [automatic-garage-door-opener-closer](components/automatic-garage-door-opener-closer/) | Voice and auto-close control for LiftMaster opener | Production |
| [front-porch-temp-sensor](components/front-porch-temp-sensor/) | Front porch temperature, pressure, and light with push notifications | Production |
| [p-w-firefly](components/p-w-firefly/) | Firefly Integrations RV-C coach interface for Pleasure-Way Lexor FL | Production |
| [photo-server](components/photo-server/) | Self-hosted Immich photo/video library on dedicated mini PC | Production |
| [hiking-monitor](components/hiking-monitor/) | Portable environmental sensor — logs to flash during hikes, syncs on return | In Progress |
| [weather-station](components/weather-station/) | Outdoor DIY weather station posting to Weather Underground and Google Sheets | Planned |
| [air-quality-monitor](components/air-quality-monitor/) | Portable PM/VOC/NOx sensor carried on hikes alongside the hiking monitor | Planned |
| [van-sensors](components/van-sensors/) | Indoor and outdoor environmental nodes for the Pleasure-Way ProMaster van | Planned |
| [remote-temp-sensor-01](components/remote-temp-sensor-01/) | Solar/battery-powered backyard temp, humidity, pressure, light, and UV sensor | Planned |

---

## What It Is

JCTsh is a personal smart home automation system for a single-family home in Tucson,
Arizona, built entirely from off-the-shelf hardware and open-source software. It has no
cloud dependencies except Home Assistant Cloud (Nabu Casa) and SmartThings for phone and
voice integration.

Each component is a self-contained unit with its own firmware, Node-RED flow, and
documentation. All components share a common infrastructure layer — a Raspberry Pi running
Mosquitto, Node-RED, Home Assistant, and a Python log server.

---

## Quick Start — Accessing the System

All services run on the home Raspberry Pi. On the home network:

| Service | URL | Notes |
|---|---|---|
| Log dashboard | http://raspberrypi.local/ | Basic Auth — user: `jctsh` |
| Node-RED | http://raspberrypi.local:1880 | Flow editor |
| Home Assistant | http://raspberrypi.local:8123 | |
| MQTT broker | raspberrypi.local:1883 | Requires auth — credentials in `credentials.local.md` |

Remote access via Tailscale: replace `raspberrypi.local` with `100.70.162.24`.

See [jctsh-access.md](jctsh-access.md) for the full access reference including RV and Tailscale setup.

---

## Architecture

Every component follows the same message flow:

```
ESP32 sensor
    │  MQTT publish
    ▼
Mosquitto broker  (Raspberry Pi)
    │
    ├──► Node-RED        — logic, thresholds, external HTTP calls
    │        │
    │        ├──► Google Sheets / Weather Underground
    │        └──► Home Assistant REST API
    │                  │
    │                  └──► SmartThings ──► Google Home / Pixel notifications
    │
    └──► Python log server  — http://raspberrypi.local/
```

Each component produces two parallel message streams: a **data stream**
(`jctsh/<type>/<component>/data`) driving automations, and a **log stream**
(`jctsh/<type>/<component>/log`) routed to the dashboard.

For full architecture details, MQTT topic conventions, credentials structure, and
infrastructure configuration, see [CLAUDE.md](CLAUDE.md).

---

## Repository Layout

```
jctsh/
├── components/                    Individual automation components — one subdirectory each
├── core/                          Shared infrastructure running on the Raspberry Pi
├── CLAUDE.md                      Claude Code context — architecture, conventions, infrastructure
├── kanban-board.md                Project kanban — Backlog / Planning / Design / Build / Done
├── DEVLOG.md                      Chronological record of decisions and incidents
├── ENVIRONMENT.md                 Physical device inventory for the home
├── SOFTWARE-ENVIRONMENT.md        What is installed and running on the Pi
├── jctsh-network.md               IP address and MAC table for all devices
├── jctsh-access.md                How to reach all services from any network
├── keepconnect.md                 KeepConnect router rebooter — config, schedule, rationale
├── jctsh-parts-inventory.md       On-hand electronics parts
├── JCTsh-Build-Standards.md       Standards all components must follow
├── JCTsh-Component-Planning-Pattern.md  How new components are planned and built
├── JCTsh-Perfboard-Build-Template.md    Reusable section skeleton for a component's
│                                             perfboard-layout.md (breadboard → perfboard transfer)
├── core/data-pipeline/JCTsh-Environmental-Data-Architecture.md  Payload schema and pipeline
│                                             for all environmental sensors
├── JCTsh-Property-Sensor-Pattern.md         Standard pattern for all property sensors —
│                                             invariant standard, variable dimensions,
│                                             new-sensor checklist
└── house-lot-coordinates.md               Lat/lon for property corners, house footprint
                                              corners, and named points (e.g. front porch) —
                                              use these when hardcoding coordinates in firmware
```

### components/

One subdirectory per automation component. Each contains a `README.md` — see the
Status table above for the full list.

### core/

Shared infrastructure not specific to any one component.

| Directory | Contents |
|---|---|
| `core/homeassistant/` | HA configuration snapshot (version-controlled copy — live copy is on Pi) |
| `core/logging/` | Python MQTT log server — see [core/logging/README.md](core/logging/README.md) |
| `core/mqtt/` | Mosquitto configuration (version-controlled copy) |
| `core/node-red/` | Shared Node-RED flows and settings (version-controlled copies) |
| `core/offline-logger/` | Reusable offline flash logging template (`sensor_logger.h`) — copy and rename for each intermittently-connected sensor |
| `core/maintenance/` | Scheduled-reboot systemd units, deployed to the Pi and M8 photo-server |

---

## Document Types

| Document | Purpose | Where to find it |
|---|---|---|
| `README.md` | What a component does, how to run it, doc index | Every component directory |
| `CLAUDE.md` | Context and constraints for Claude Code sessions | Repo root + component directories |
| `kanban-board.md` | Kanban board — all planned and in-progress work | Repo root |
| `DEVLOG.md` | Why decisions were made; significant incidents | Repo root |
| `*-phase1.md` / `*-planning.md` | Pre-build discovery — decisions, BOM, architecture choices | Component directory |
| `*-claude-code-instructions.md` | Step-by-step build instructions executed with Claude Code | Component directory |
| `JCTsh-*.md` | Monorepo-wide standards all components must conform to | Repo root |
| `wiring.md` | Pin assignments and breadboard wiring reference | Component directory |
| `ESP32-project-pins.md` | Full 38-pin assignment table for the component's ESP32 | Component directory |
| `perfboard-layout.md` | Permanent soldered build layout | Component directory |
| `flashing.md` | First flash and OTA update procedure | Component directory |
| `testing.md` / `end-to-end-test.md` | Test procedures and pass/fail criteria | Component directory |
| `integration.md` | How the component connects to HA, SmartThings, or other systems | Component directory |
| `operations.md` | Day-to-day use and troubleshooting | Component directory |
| `jctsh-network.md` | IP, hostname, and MAC for every device | Repo root |
| `jctsh-access.md` | How to reach every service from home, remote, or RV | Repo root |
| `credentials.local.md` | All generated passwords — gitignored, never committed | Repo root |
