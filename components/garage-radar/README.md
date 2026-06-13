# Garage Radar

24GHz mmWave presence sensor for the garage workbench — detects still presence that
PIR-based sensors cannot, feeding into the garage presence automation to prevent the
door closing on someone sitting motionless at the workbench.

**Status:** Production — mounted in garage, running in production (June 2026)
**Hardware:** ESP32 + HLK-LD2412 mmWave radar

---

## What It Solves

PIR sensors detect heat movement — they miss someone sitting still. Arizona summer heat
also causes PIR sensors to stick `on`, making them unreliable as a primary presence
signal. The LD2412 mmWave radar detects both moving and still targets regardless of
ambient temperature, making it the primary input to the garage presence timer and the
safety interlock that prevents the auto-close routine from closing the door with someone
inside.

---

## Hardware

| Component | Details |
|---|---|
| Radar sensor | HLK-LD2412, 24GHz mmWave, UART interface |
| Microcontroller | ESP32 DevKitC-32, 38-pin, CP2102 USB-C |
| Green LED | GPIO33, 330Ω — presence detected |
| Yellow LED | GPIO32, 330Ω — garage lights on (mirrors vswitch) |
| Power | USB-C from garage outlet |
| Firmware | ESPHome ≥ 2025.8.0 (first version with native `ld2412` support) |

See [wiring.md](wiring.md) for full wiring checklist and
[ESP32-project-pins.md](ESP32-project-pins.md) for the complete pin table.

---

## Architecture

```
HLK-LD2412 radar
      │  UART (GPIO16 RX2 / GPIO17 TX2)
      ▼
ESP32 / ESPHome
      │  MQTT: jctsh/components/garage-radar/...
      ▼
Mosquitto broker (Raspberry Pi)
      │
      ├──► Home Assistant
      │      binary_sensor.garage_radar_presence
      │      ├── Garage Presence - Restart timer on activity
      │      ├── Garage Presence - Radar keepalive (every 5 min while present)
      │      └── timer.garage_presence_timer
      │               │ on expire
      │               ▼
      │      switch.garage_presence_vswitch ──► SmartThings ──► lights off / door close
      │
      └──► Log dashboard
```

---

## Quick Start

1. Copy `secrets.yaml.template` → `secrets.yaml` and fill in credentials from
   `credentials.local.md`
2. See [flashing.md](flashing.md) for first flash — note the Windows path requirement
3. See [integration.md](integration.md) for HA automation setup
4. See [end-to-end-test.md](end-to-end-test.md) for full system validation

---

## Configuration

| Setting | Where | Notes |
|---|---|---|
| WiFi / MQTT credentials | `secrets.yaml` | Template: `secrets.yaml.template` |
| Presence timer duration | `input_number.garage_timer_duration` | Default 20 min — set in HA Helpers |

---

## How It Works

### Presence Detection

The LD2412 reports `has_target` (true when any target — still or moving — is in range).
ESPHome applies a `delayed_off: 30s` filter so momentary detection gaps don't flicker
the state. This drives `binary_sensor.garage_radar_presence` in HA.

### LEDs

The **green LED** mirrors the presence state using a 30-second manual holdoff driven by
`detection_distance` rather than `id(presence).state` — necessary because nested ld2412
binary sensors return unreliable state values in ESPHome 2026.x.

The **yellow LED** mirrors `switch.garage_presence_vswitch` via MQTT subscription to
`jctsh/components/garage-presence-vswitch/state`. On = garage lights on.

### HA Automations

| Automation | Trigger | Action |
|---|---|---|
| Restart timer on activity | `garage_radar_presence` off→on | Start 15-min timer; turn on vswitch |
| Radar keepalive | Every 5 min while presence on | Restart timer; confirm vswitch on |
| Timer expired | `timer.garage_presence_timer` finished | Turn off vswitch → lights off |

The keepalive prevents timer expiry during extended still presence — the `off→on`
trigger won't re-fire if someone stays motionless for longer than the timer duration.

### Timeouts

| Timeout | Location | Purpose |
|---|---|---|
| 30 seconds | ESPHome `delayed_off` | Smooths momentary detection gaps |
| 5 minutes | HA keepalive | Resets timer during continuous still presence |
| 20 minutes | HA timer (default) | Presence decision; turns off vswitch on expiry |

### Heartbeat

Every 5 minutes the device publishes to `.../log` (uptime, RSSI, presence state) and
`.../heartbeat` (JSON). The Node-RED watchdog alerts via push notification if silent for
more than 35 minutes.

---

## MQTT Topics

**Published** (prefix: `jctsh/components/garage-radar`):

| Topic suffix | Payload |
|---|---|
| `.../binary_sensor/presence/state` | `ON` / `OFF` — primary presence signal |
| `.../binary_sensor/moving_target/state` | `ON` / `OFF` |
| `.../binary_sensor/still_target/state` | `ON` / `OFF` |
| `.../sensor/detection_distance/state` | cm |
| `.../log` | JSON log messages |
| `.../heartbeat` | JSON heartbeat |

**Subscribed:** `jctsh/components/garage-presence-vswitch/state` — drives yellow LED.

---

## HA Entities

| Entity | Type | Purpose |
|---|---|---|
| `binary_sensor.garage_radar_presence` | Binary sensor | Primary presence signal |
| `sensor.garage_radar_detection_distance` | Sensor | Detection distance in cm |
| `input_number.garage_timer_duration` | Helper | Timer duration in minutes |
| `timer.garage_presence_timer` | Timer | Countdown timer |
| `switch.garage_presence_vswitch` | Switch | Controls lights via SmartThings |

---

## Known Behaviors and Limitations

- **Door false positive:** Closing the garage door sweeps through the radar cone,
  triggering a brief presence detection. Harmless with a 15-minute timer.
- **ESPHome 2026.x nested binary sensor:** `id(presence).state` returns unreliable
  values for binary sensors inside the `ld2412:` component. Green LED uses
  `detection_distance` + manual holdoff as a workaround.
- **HA distance display:** HA shows distance in imperial (inches) due to system unit
  settings — values from ESPHome are in cm. Presence detection is unaffected.
- **Antenna orientation:** The LD2412 antenna face is the blank side (no components).
  It must face the detection zone.

---

## Files

| File | Purpose |
|---|---|
| `garage-radar.yaml` | ESPHome firmware config |
| `secrets.yaml` | Credentials — gitignored, never commit |
| `secrets.yaml.template` | Credential template |
| `wiring.md` | Breadboard wiring checklist |
| `ESP32-project-pins.md` | Full 38-pin assignment table |
| `perfboard-layout.md` | Permanent soldered build layout |
| `flashing.md` | First flash and OTA procedure |
| `integration.md` | HA automation setup |
| `integration-notes.md` | HA integration investigation findings |
| `smartthings-integration.md` | SmartThings integration notes |
| `testing.md` | Sensor validation procedure |
| `end-to-end-test.md` | Full system validation test suite |
| `CLAUDE.md` | Claude Code context — constraints and gotchas |
| `jctsh-garage-radar-claude-code-instructions.md` | Full build instructions |
