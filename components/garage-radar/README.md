# Garage Radar

24GHz mmWave radar presence sensor for the garage workbench area. Detects still
presence (someone sitting motionless) — a gap that PIR-based sensors cannot fill.
Feeds into the existing garage presence automation as an additive input.

## Hardware

| Component | Detail |
|---|---|
| Radar sensor | HLK-LD2412, 24GHz mmWave, UART interface |
| Microcontroller | ESP32 DevKitC-32, 38-pin, CP2102 USB-C |
| Firmware | ESPHome 2026.4.5 |
| Power | USB to ESP32 from garage outlet |

See `ESP32pins.png` for the full ESP32 DevKitC-32 pinout reference.

## Wiring

| LD2412 Pin | ESP32 Pin |
|---|---|
| 5V | VIN (5V) |
| GND | GND |
| TX | GPIO16 (RX2) |
| RX | GPIO17 (TX2) |

The LD2412 has an onboard 5V→3.3V regulator. Power from ESP32 VIN only — not 3.3V.
UART logic operates at 3.3V — no level shifter needed. See `wiring.md` for full detail.

## ESPHome Configuration

File: `garage-radar.yaml`

- Hardware UART2 (GPIO16/GPIO17), 115200 baud
- `delayed_off: 30s` filter on `has_target` — smooths momentary detection gaps
- MQTT discovery enabled — device auto-registers in HA on first boot

Credentials in `secrets.yaml` (gitignored). Copy `secrets.yaml.template` to get started.

## MQTT

Topic prefix: `jctsh/components/garage-radar`

| Topic suffix | Value |
|---|---|
| `.../binary_sensor/presence/state` | `ON` / `OFF` — primary presence signal |
| `.../binary_sensor/moving_target/state` | `ON` / `OFF` |
| `.../binary_sensor/still_target/state` | `ON` / `OFF` |
| `.../sensor/moving_distance/state` | cm |
| `.../sensor/still_distance/state` | cm |
| `.../sensor/moving_energy/state` | % |
| `.../sensor/still_energy/state` | % |
| `.../sensor/detection_distance/state` | cm |

## HA Integration

HA entity: `binary_sensor.garage_radar_presence`

Two automations feed this into the garage presence system:

- **Garage Presence - Restart timer on activity** — radar `to: "on"` trigger restarts
  the 20-minute presence timer and turns on `switch.garage_presence_vswitch`
- **Garage Presence - Radar keepalive** — fires every 10 minutes while radar detects
  presence, preventing timer expiry during extended still workbench use

See `integration.md` for setup instructions and `components/garage-presence/CLAUDE.md`
for the full garage presence architecture.

## Timeouts

| Timeout | Where | Purpose |
|---|---|---|
| 30 seconds | ESPHome `delayed_off` filter | Smooths momentary radar detection gaps |
| 10 minutes | HA keepalive automation | Resets presence timer during continuous still detection |
| 20 minutes | HA `timer.garage_presence_timer` | Actual presence decision — turns off vswitch on expiry |

## Known Behaviors

- HA displays distance sensors in inches (imperial unit conversion) — the underlying
  values from ESPHome are in cm. Presence detection is unaffected.
- PIR-based sensors in the garage (motion sensor, garage cam) may stick `on` in Arizona
  summer heat, preventing `off`→`on` transition triggers. The radar is not affected by
  ambient temperature.
- The LD2412 antenna face is the blank side of the module (no components). It must point
  toward the detection zone. Do not place metal directly in front of it.
- Detection range: 9m max, ±75° cone. Aim carefully to avoid picking up the garage door
  or driveway.

## Build Documents

| File | Purpose |
|---|---|
| `wiring.md` | Breadboard wiring reference |
| `flashing.md` | ESPHome flash instructions |
| `testing.md` | Sensor validation procedure |
| `perfboard-layout.md` | Permanent soldered build (Steps 5–7, deferred) |
| `mounting.md` | Physical installation (Steps 5–7, deferred) |
| `integration-notes.md` | HA integration investigation findings |
| `integration.md` | HA integration instructions |
| `end-to-end-test.md` | Full system validation procedure |

## Status

Prototype (breadboard) deployed and integrated. Steps 5–7 (perfboard transfer and
permanent mounting) deferred — system is fully functional on the breadboard build.
