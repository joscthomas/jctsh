# Garage Radar

24GHz mmWave presence sensor for the garage workbench. Detects still presence (someone sitting motionless) — a gap that PIR-based sensors cannot fill. Feeds into the existing garage presence automation as an additive trigger.

---

## Hardware

| Component | Detail |
|---|---|
| Radar sensor | HLK-LD2412, 24GHz mmWave, UART interface |
| Microcontroller | ESP32 DevKitC-32, 38-pin, CP2102 USB-C |
| Firmware | ESPHome ≥ 2025.8.0 (first version with native ld2412 support) |
| Power | USB-C to ESP32 from garage outlet |

See `ESP32pins.png` for the full ESP32 DevKitC-32 pinout reference.

---

## Wiring

**Radar (UART2 — hardware serial):**

| LD2412 Pin | ESP32 Pin | Notes |
|---|---|---|
| TX | GPIO16 (RX2) | |
| RX | GPIO17 (TX2) | |
| VCC | VIN (5V) | LD2412 has onboard 5V→3.3V regulator — do not use 3.3V pin |
| GND | GND | |

UART logic operates at 3.3V — no level shifter needed.

**LEDs:**

| GPIO | Resistor | LED color | Meaning |
|---|---|---|---|
| GPIO33 | 330Ω | Green | Presence detected |
| GPIO32 | 330Ω | Yellow | Garage presence vswitch on (lights on) |

> **GPIO note:** GPIO25 and GPIO26 are broken for digital output — DAC post-boot initialization reconfigures them. Always use GPIO32/GPIO33 for LEDs on this board.

See `wiring.md` for the full breadboard wiring checklist.

---

## Architecture

```
HLK-LD2412 radar
  │  (UART)
ESP32 DevKitC-32
  │
  │  MQTT: jctsh/components/garage-radar/...
  ▼
Mosquitto broker (Raspberry Pi)
  │
  ├──► Home Assistant
  │      binary_sensor.garage_radar_presence
  │      │
  │      ├── Garage Presence - Restart timer on activity (off→on trigger)
  │      ├── Garage Presence - Radar keepalive (fires every 5 min while present)
  │      └── timer.garage_presence_timer (15 min)
  │               │ on expire
  │               ▼
  │      switch.garage_presence_vswitch ──► SmartThings ──► lights off
  │
  └──► Node-RED
         log router: .../log → log dashboard
         watchdog: push notification if heartbeat stops for 10 min
```

---

## How It Works

### Presence detection

The LD2412 reports `has_target` (true when any target — still or moving — is in range). ESPHome applies a `delayed_off: 30s` filter so momentary detection gaps do not flicker the state. This drives `binary_sensor.garage_radar_presence` in Home Assistant.

The LD2412 also reports `has_moving_target`, `has_still_target`, and distance/energy values — all published to MQTT and visible in HA — but only `has_target` drives the presence automations.

### Green LED

The green LED mirrors the 30-second presence holdoff using `detection_distance` (a numeric sensor) and a manual countdown global, rather than `id(presence).state`. This workaround is needed because nested ld2412 binary sensors return unreliable state values in ESPHome 2026.x.

### Yellow LED

Mirrors `switch.garage_presence_vswitch` via MQTT subscription to `jctsh/components/garage-presence-vswitch/state`. On = lights are on; Off = lights are off (or timer has expired).

### HA automations

| Automation | Trigger | Action |
|---|---|---|
| Garage Presence - Restart timer on activity | `garage_radar_presence` off→on | Start 15-min timer; turn on vswitch |
| Garage Presence - Radar keepalive | Every 5 min (while presence on) | Restart timer; confirm vswitch on |
| Garage Presence - Timer expired | `timer.garage_presence_timer` finished | Turn off vswitch → lights off |

The keepalive is needed because the `off→on` trigger fires only on state transitions. Someone sitting still at the workbench for 15+ minutes produces no transition — the timer would expire. The keepalive fires every 5 minutes (half the timer duration) to prevent this regardless of how `garage_timer_duration` is set.

### Timeouts

| Timeout | Location | Purpose |
|---|---|---|
| 30 seconds | ESPHome `delayed_off` filter | Smooths momentary radar detection gaps |
| 5 minutes | HA keepalive automation | Resets timer during continuous still presence |
| 15 minutes | HA `timer.garage_presence_timer` | Actual presence decision; turns off vswitch on expiry |

Timer duration is controlled by `input_number.garage_timer_duration` in HA.

### Heartbeat and watchdog

Every 5 minutes the ESP32 publishes to:
- `.../log` — heartbeat message (uptime, RSSI, presence state) routed by Node-RED to the log dashboard
- `.../heartbeat` — JSON payload consumed by the Node-RED watchdog

Node-RED resets a 10-minute timer on each heartbeat. If the timer fires (no heartbeat for 10 minutes), Node-RED sends a push notification to the Pixel via HA companion app.

---

## MQTT Topics

**Published (prefix: `jctsh/components/garage-radar`):**

| Topic suffix | Payload | Notes |
|---|---|---|
| `.../binary_sensor/presence/state` | `ON` / `OFF` | Primary presence signal (has_target + 30s delayed_off) |
| `.../binary_sensor/moving_target/state` | `ON` / `OFF` | |
| `.../binary_sensor/still_target/state` | `ON` / `OFF` | |
| `.../sensor/moving_distance/state` | cm | |
| `.../sensor/still_distance/state` | cm | |
| `.../sensor/moving_energy/state` | % | |
| `.../sensor/still_energy/state` | % | |
| `.../sensor/detection_distance/state` | cm | |
| `.../log` | JSON | Log messages → log dashboard |
| `.../heartbeat` | JSON | Node-RED watchdog input |

**Subscribed:**

| Topic | Purpose |
|---|---|
| `jctsh/components/garage-presence-vswitch/state` | Drives yellow LED |

---

## HA Entities

| Entity | Type |
|---|---|
| `binary_sensor.garage_radar_presence` | Primary presence signal |
| `binary_sensor.garage_radar_moving_target` | Moving target |
| `binary_sensor.garage_radar_still_target` | Still target |
| `sensor.garage_radar_moving_distance` | cm |
| `sensor.garage_radar_still_distance` | cm |
| `sensor.garage_radar_moving_energy` | % |
| `sensor.garage_radar_still_energy` | % |
| `sensor.garage_radar_detection_distance` | cm |
| `input_number.garage_timer_duration` | Timer duration in minutes (15) |
| `timer.garage_presence_timer` | Countdown timer |
| `switch.garage_presence_vswitch` | Controls lights via SmartThings |

---

## Flashing

**Windows path note:** Spaces in the repo path break PlatformIO. Run all `esphome` commands from the junction `C:\jctsh\components\garage-radar\`, not the full repo path.

**First flash (USB):**
1. Copy `secrets.yaml.template` → `secrets.yaml`, fill in credentials
2. Connect ESP32 via USB-C
3. `esphome run garage-radar.yaml`

**Subsequent flashes (OTA):**
`esphome run garage-radar.yaml` — when prompted, choose the IP address option. mDNS (`.local`) does not work reliably on Windows.

See `flashing.md` for full details and troubleshooting.

---

## Known Behaviors and Limitations

- **Garage door false positive:** Closing the garage door sweeps through the radar's detection cone, triggering a brief presence detection. With a 15-minute timer this is harmless. Adjusting the tilt angle downward to exclude the door path is a possible fix but requires a calibration method.
- **ESPHome 2026.x nested binary sensor:** `id(presence).state` returns unreliable values for binary sensors inside the `ld2412:` component. Green LED uses `detection_distance` + manual holdoff as a workaround.
- **HA distance units:** HA displays distance sensors in imperial (inches) due to system unit settings — underlying values from ESPHome are in cm. Presence detection is unaffected.
- **PIR sensors in Arizona summer heat:** PIR-based garage sensors may stick `on` in high ambient heat, blocking `off→on` transition triggers. The LD2412 is unaffected by ambient temperature.
- **Antenna orientation:** The LD2412 antenna face is the blank side of the module (no components). It must face the detection zone. Do not place metal directly in front of it.

---

## Build Documents

| File | Purpose |
|---|---|
| `wiring.md` | Breadboard wiring reference and checklist |
| `flashing.md` | Step 3: first flash and OTA procedure |
| `testing.md` | Step 4: sensor validation |
| `integration-notes.md` | HA integration investigation findings |
| `smartthings-integration.md` | SmartThings integration notes |
| `integration.md` | Step 8: HA automation setup instructions |
| `end-to-end-test.md` | Step 9: full system validation test suite |
| `perfboard-layout.md` | Step 5: permanent soldered build (deferred — waiting for parts) |

---

## Status

Prototype (breadboard) deployed and fully validated (Steps 1–9 complete). Steps 5–7 (perfboard transfer and permanent mounting) deferred pending parts arrival. System is fully functional on the breadboard build.
