# [Component Name]

[One sentence: what it is and what it does.]

**Status:** [Production | In Progress | Planned]
**Hardware:** [e.g., ESP32 + BME280 | Raspberry Pi 3B+ | HA-only | No custom hardware]

---

## What It Solves

[2–4 sentences: what problem this addresses, what gap it fills, what would be missing
without it.]

---

## Hardware

<!-- Omit section if no custom hardware (e.g., HA-only or SmartThings-only components) -->

| Component | Details |
|---|---|
| Microcontroller | |
| Sensor(s) | |
| Indicators | |
| Power | |

---

## Architecture

[Data-flow diagram. Inputs on top, outputs at bottom. Include MQTT topics, HA entities,
and SmartThings devices as appropriate.]

```
[sensor hardware]
      │
[ESP32 / ESPHome]
      │  MQTT: jctsh/<type>/<name>/...
      ▼
[Mosquitto broker]
      │
      ├──► Node-RED       — [what logic lives here]
      │         └──► Home Assistant
      │                   └──► SmartThings
      └──► Log dashboard
```

---

## Quick Start

[Minimum steps to go from nothing to a working component. Reference dedicated docs
files — never repeat their content here.]

1. Copy `secrets.yaml.template` → `secrets.yaml` and fill in credentials from
   `credentials.local.md`
2. See [flashing.md](flashing.md) for first flash procedure
3. See [integration.md](integration.md) for HA and Node-RED setup
4. See [testing.md](testing.md) to verify end-to-end operation

---

## Configuration

<!-- Only items requiring active decisions. Credentials go in secrets.yaml.
     List only what to set and where. -->

| Setting | Where | Notes |
|---|---|---|
| WiFi / MQTT credentials | `secrets.yaml` | Template: `secrets.yaml.template` |
| [calibration or threshold] | [HA Helper / Node-RED env var / config constant] | |

---

## How It Works

[Explain the runtime behavior a user would observe — what triggers what, timing, what
the LEDs mean, what notifications fire and when. Reference other docs for setup
procedures; this section covers runtime behavior only.]

---

## Files

| File | Purpose |
|---|---|
| `[component-name].yaml` | ESPHome firmware config |
| `secrets.yaml` | Credentials — gitignored, never commit |
| `secrets.yaml.template` | Credential template |
| `[component-name].flow.json` | Node-RED flow |
| `wiring.md` | Pin assignments and wiring reference |
| `ESP32-project-pins.md` | Full 38-pin assignment table |
| `flashing.md` | First flash and OTA procedure |
| `integration.md` | HA and Node-RED setup |
| `testing.md` | End-to-end test procedure |
| `perfboard-layout.md` | Permanent soldered build layout |
| `CLAUDE.md` | Claude Code context — constraints and gotchas |
| `[component-name]-claude-code-instructions.md` | Step-by-step build instructions |

---

## Known Behaviors and Limitations

<!-- Non-obvious behaviors a user might encounter and misread as a bug.
     Omit section if there are none. -->

- **[behavior]:** [why it happens and whether it matters]
