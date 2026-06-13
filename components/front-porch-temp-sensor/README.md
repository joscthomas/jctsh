# Front Porch Temp Sensor

ESP32 environmental sensor for the front porch — monitors temperature, pressure, and
light level, and sends push notifications to household phones when the temperature
crosses a configurable threshold.

**Status:** Production — on perfboard, deployed at front porch
**Hardware:** ESP32 + BME280 + BH1750 light sensor

---

## What It Solves

Tucson summers are dangerously hot. This sensor monitors the front porch temperature
and notifies when it's warm enough to close the door (≥ threshold) or cool enough to
open windows (< threshold, morning hours only), so you don't have to remember to check.
A configurable threshold and time window prevent false alerts.

---

## Hardware

| Component | Details |
|---|---|
| Microcontroller | ESP32 DevKitC-32, 38-pin, CP2102, USB-C |
| Temp / humidity / pressure | BME280 (genuine GY-BME280), I2C at GPIO21/22 |
| Light | BH1750 (GY-302), I2C at GPIO21/22, ADDR pin → GND (address 0x23) |
| Power | USB-C from porch outlet |
| Firmware | ESPHome |

Both sensors share the I2C bus. See [wiring.md](wiring.md) for full wiring checklist
and [ESP32-project-pins.md](ESP32-project-pins.md) for the complete pin table.

---

## Architecture

```
BME280 (temp/humidity/pressure)  +  BH1750 (light)
                  │  I2C
                  ▼
        ESP32 / ESPHome
                  │  MQTT: jctsh/components/front-porch-temp-sensor/...
                  ▼
        Mosquitto broker (Raspberry Pi)
                  │
          ┌───────┴───────┐
          ▼               ▼
   Home Assistant      Node-RED
   sensor entities     log router + watchdog
          │
   HA automations
   ├── Front Porch Warm - Close Door
   └── Front Porch Cool - Open Door
          │
          ▼
   notify.mobile_app_pixel_10_pro_xl
   notify.mobile_app_pixel_7_pro
```

---

## Quick Start

1. Copy `secrets.yaml.template` → `secrets.yaml` and fill in credentials from
   `credentials.local.md`
2. See [flashing.md](flashing.md) for flash procedure
3. See [integration.md](integration.md) for HA entity and automation setup
4. See [testing.md](testing.md) to verify end-to-end operation

---

## Configuration

| Setting | Where | Notes |
|---|---|---|
| WiFi / MQTT credentials | `secrets.yaml` | Template: `secrets.yaml.template` |
| Alert temperature threshold | `input_number.front_porch_temp_threshold` | Default 80°F — set in HA Helpers |

Threshold changes take effect immediately — no reflash needed.

---

## How It Works

Temperature, pressure, and illuminance are published to MQTT every 60 seconds.
HA auto-discovers all entities via MQTT discovery.

Two HA automations fire once per threshold crossing — no reminders:

| Automation | Trigger | Time window |
|---|---|---|
| Front Porch Warm - Close Door | Temp stays ≥ threshold for 10 min | 6am–10pm |
| Front Porch Cool - Open Door | Temp stays < threshold for 10 min | 6am–1pm |

The 10-minute stability buffer prevents spurious alerts from brief temperature spikes.

Every 5 minutes the device publishes a heartbeat to
`jctsh/components/front-porch-temp-sensor/heartbeat`. The Node-RED watchdog monitors
this and sends a push notification if silent for more than 35 minutes.

---

## Files

| File | Purpose |
|---|---|
| `front-porch-temp-sensor.yaml` | ESPHome firmware config |
| `secrets.yaml` | Credentials — gitignored, never commit |
| `secrets.yaml.template` | Credential template |
| `wiring.md` | Breadboard wiring checklist |
| `ESP32-project-pins.md` | Full 38-pin assignment table |
| `perfboard-layout.md` | Perfboard build layout |
| `flashing.md` | Flash procedure |
| `integration.md` | HA entity and automation setup |
| `testing.md` | End-to-end test procedure |
| `mounting.md` | Physical mounting instructions |
| `automation-front-porch-warm-close-door.yaml` | HA automation YAML |
| `automation-front-porch-cool-open-door.yaml` | HA automation YAML |
| `CLAUDE.md` | Claude Code context — constraints and gotchas |
| `front-porch-temp-sensor-claude-code-instructions.md` | Full build instructions |
