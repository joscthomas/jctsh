# Salt Sensor

ESP32-based ultrasonic salt level monitor for a residential water softener — measures
salt percentage and sends low/critical alerts to SmartThings.

**Status:** Production
**Hardware:** ESP32 + JSN-SR04T waterproof ultrasonic sensor + three status LEDs

---

## What It Solves

A water softener runs out of salt silently — there's no indicator until the water stops
being softened. This sensor measures the salt level every 12 hours and sends SmartThings
alerts before the tank runs out, giving time to refill without service interruption.
Calibration is done in Home Assistant with no reflash required.

---

## Hardware

| Component | Details |
|---|---|
| Microcontroller | ESP32 Dev Module |
| Sensor | JSN-SR04T waterproof ultrasonic — mounts at top of salt tank facing down |
| Red LED | GPIO2, 220Ω — critical level |
| Yellow LED | GPIO15, 220Ω — low level |
| Green LED | GPIO4, 220Ω — good level |
| Power | 5V USB wall charger |

### Wiring

| Connection | Notes |
|---|---|
| JSN-SR04T VCC → ESP32 VIN (5V) | Sensor requires 5V |
| JSN-SR04T Trig → GPIO5 | |
| JSN-SR04T Echo → 1kΩ → GPIO18 → 2kΩ → GND | Voltage divider required — sensor outputs 5V, ESP32 GPIO is 3.3V only |
| LEDs → GPIO2/15/4 via 220Ω → GND | |

See [ESP32-project-pins.md](ESP32-project-pins.md) for the full pin table.

---

## Architecture

```
JSN-SR04T ultrasonic sensor
      │  (GPIO5 trig / GPIO18 echo)
      ▼
ESP32 Arduino sketch
      │  MQTT: jctsh/sensors/salt-sensor/...
      ▼
Mosquitto broker (Raspberry Pi)
      │
      ├──► Node-RED
      │      ├── Reads calibration from HA input_number helpers
      │      ├── Calculates salt percentage
      │      ├── Applies alert thresholds
      │      ├── Controls HA virtual switches → SmartThings alerts
      │      └── Publishes status back to ESP32 → drives LEDs
      │
      └──► Log dashboard
```

---

## Quick Start

1. Create `secrets.h` in the sketch folder — see Configuration below
2. Install PubSubClient via Arduino Library Manager
3. Set Board: **ESP32 Dev Module**, Upload Speed: **921600**,
   Partition Scheme: **Default 4MB with spiffs**
4. Flash via USB (first time), then OTA for subsequent updates
5. Import `salt-sensor.flow.json` into Node-RED (import `core.flow.json` first)
6. Set `HA_TOKEN` in Node-RED: Settings → Environment Variables
7. Create HA helpers and virtual switches — see Configuration below

---

## Configuration

### Credentials (`secrets.h`)

Create `secrets.h` in the sketch folder — gitignored, never commit:

```cpp
#ifndef SECRETS_H
#define SECRETS_H
#define WIFI_SSID      "JCTnet1"
#define WIFI_PASSWORD  "..."
#define MQTT_HOST      "raspberrypi.local"
#define MQTT_PORT      1883
#define MQTT_USER      "salt-sensor"
#define MQTT_PASS      "..."
#define OTA_PASSWORD   "..."
#endif
```

All values are in `credentials.local.md`.

### Calibration (HA Helpers)

Create via Settings → Helpers → + Create Helper → Number:

| Helper entity | Default | Meaning |
|---|---|---|
| `input_number.salt_full_distance_cm` | 20.4 | Sensor-to-salt distance when tank is 100% full |
| `input_number.salt_empty_distance_cm` | 43.0 | Sensor-to-salt distance when tank is 0% empty |

Changes take effect within 60 seconds — no reflash needed.

To calibrate: mount the sensor at the top of the tank facing down. Fill to normal maximum
and note the distance in the log dashboard. Measure from sensor face to tank floor for
the empty value.

### HA Virtual Switches (synced to SmartThings)

| Entity | Purpose |
|---|---|
| `switch.salt_low_alert` | ON at warning level (< 33%) |
| `switch.salt_critical_alert` | ON at critical level (< 15%) |
| `switch.salt_test_mode` | Turn ON in SmartThings to run test sequence |
| `switch.salt_full_reset` | Turn ON in SmartThings after refilling to clear alerts |

### Alert Thresholds

Set in the Node-RED `fn_threshold` function node:

```js
const WARNING_PERCENT  = 33.0;
const CRITICAL_PERCENT = 15.0;
```

---

## How It Works

### LED States

| LED state | Meaning |
|---|---|
| Green solid | Salt level good (> 33%) |
| Yellow blinking | Low (15–33%) — warning alert active |
| Red blinking | Critical (< 15%) — critical alert active |
| All three × 3 rapid flashes | Normal boot |
| All three blinking together | Sensor hardware error |

### Test Mode

Turn ON `Salt Test Mode` in SmartThings. Node-RED simulates two readings:
- Step 1: ~27% — yellow LED, warning alert to SmartThings
- Step 2: 0% — red LED, critical alert to SmartThings

Turn OFF the switch to clear all alerts and return to `ok`.

### Reset After Refilling

Turn ON `Salt Full Reset` in SmartThings. Node-RED clears both alert switches, publishes
`ok` to the ESP32 (green LED goes solid), and turns the reset switch back OFF
automatically.

### OTA Updates

After first USB flash, use OTA. Arduino IDE 2 has a port substitution bug on Windows —
use `espota.exe` directly:

1. Arduino IDE: Sketch → Export Compiled Binary → produces `salt-sensor.ino.bin`
2. Power-cycle the ESP32
3. Run:
```
"C:\...\Arduino15\packages\esp32\hardware\esp32\3.3.8\tools\espota.exe" -i <ip> -p 3232 -a <OTA_PASSWORD> -f salt-sensor.ino.bin
```

Three rapid LED flashes at boot confirm a successful OTA reboot.

---

## MQTT Topics

| Topic | Direction | Payload |
|---|---|---|
| `jctsh/sensors/salt-sensor/data` | ESP32 → Node-RED | `{"distance_cm":25.3}` retained |
| `jctsh/sensors/salt-sensor/status` | Node-RED → ESP32 | `ok` / `warning` / `critical` / `error` |
| `jctsh/sensors/salt-sensor/log` | both → log server | Standard JSON log message |

---

## Files

| File | Purpose |
|---|---|
| `salt-sensor/salt-sensor.ino` | ESP32 Arduino sketch |
| `salt-sensor/secrets.h` | Credentials — gitignored, never commit |
| `salt-sensor.flow.json` | Node-RED flow |
| `ESP32-project-pins.md` | Full 38-pin assignment table |
| `CLAUDE.md` | Claude Code context — constraints and gotchas |
| `archive/water_softener_salt_sensor_v2.ino` | Previous version using direct SmartThings API (reference only — do not use) |

---

## Known Behaviors and Limitations

- **Arduino C++ (not ESPHome):** This component predates the JCTsh ESPHome standard.
  Migration to ESPHome is in the backlog (CARD-0004) and should be done before any
  perfboard transfer.
- **GPIO2 and GPIO15 are strapping pins:** Currently working but risky — these affect
  boot mode if driven at reset. No issues observed in production, but monitor after any
  reflash.
