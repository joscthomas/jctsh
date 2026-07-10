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
ESP32 (ESPHome)
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

1. Create `secrets.yaml` in this folder — see Configuration below
2. Copy `salt-sensor.yaml` and `secrets.yaml` to `C:\esphome\salt-sensor\` (compiling from
   the repo path breaks — see Known Behaviors and Limitations)
3. Flash via USB (first time): `cd C:\esphome\salt-sensor && esphome run salt-sensor.yaml`
4. All subsequent updates: same command, over OTA once the device is on the network
5. Import `salt-sensor.flow.json` into Node-RED (import `core.flow.json` first)
6. Set `HA_TOKEN` in Node-RED: Settings → Environment Variables
7. Create HA helpers and virtual switches — see Configuration below

---

## Configuration

### Credentials (`secrets.yaml`)

Create `secrets.yaml` in this folder — gitignored, never commit:

```yaml
wifi_ssid: "JCTnet1"
wifi_password: "..."
ap_password: "..."

mqtt_broker: "raspberrypi.local"
mqtt_username: "salt-sensor"
mqtt_password: "..."

ota_password: "..."
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

After first USB flash, use OTA — same command as the initial flash:
```
cd C:\esphome\salt-sensor
esphome run salt-sensor.yaml
```
ESPHome auto-detects the device on the network and offers OTA as an upload option.
Three rapid LED flashes at boot confirm a successful reboot.

---

## MQTT Topics

| Topic | Direction | Payload |
|---|---|---|
| `jctsh/sensors/salt-sensor/data` | ESP32 → Node-RED | `{"distance_cm":25.3}` retained |
| `jctsh/sensors/salt-sensor/status` | Node-RED → ESP32 | `ok` / `warning` / `critical` / `error` |
| `jctsh/sensors/salt-sensor/log` | both → log server | Standard JSON log message |
| `jctsh/sensors/salt-sensor/heartbeat` | ESP32 → watchdog | JSON heartbeat, every 30 min |

---

## Files

| File | Purpose |
|---|---|
| `salt-sensor.yaml` | ESPHome configuration — firmware source of truth |
| `secrets.yaml` | Credentials — gitignored, never commit |
| `salt-sensor.flow.json` | Node-RED flow |
| `ESP32-project-pins.md` | Full 38-pin assignment table |
| `CLAUDE.md` | Claude Code context — constraints and gotchas |
| `archive/salt-sensor-v3-arduino/` | Previous Arduino C++ firmware (reference only — do not use) |
| `archive/water_softener_salt_sensor_v2.ino` | Older version using direct SmartThings API (reference only — do not use) |

---

## Known Behaviors and Limitations

- **GPIO2 and GPIO15 are strapping pins:** Carried over unchanged from the Arduino
  version. ESPHome logs a boot-time warning about both (and about GPIO5) but the device
  boots and runs correctly with this wiring. If a future reflash ever fails to boot, the
  fix is physical — rewire the LEDs to GPIO32/GPIO33 on the breadboard.
- **Compile from `C:\esphome\salt-sensor\`, not the repo path:** spaces in
  `JCT Documents` break the ESP-IDF compiler. Copy `salt-sensor.yaml` and `secrets.yaml`
  there after any edit.
