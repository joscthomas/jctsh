# Salt Sensor

ESP32-based ultrasonic salt level monitor for a residential water softener — measures
salt percentage and raises low/critical alerts through Home Assistant (alert switches
voice-exposed to Google Assistant).

**Status:** Production
**Hardware:** ESP32 + JSN-SR04T waterproof ultrasonic sensor + three status LEDs

---

## What It Solves

A water softener runs out of salt silently — there's no indicator until the water stops
being softened. This sensor measures the salt level every 12 hours and raises alerts
before the tank runs out, giving time to refill without service interruption.
Calibration is done in Home Assistant with no reflash required.

---

## Hardware

| Component | Details |
|---|---|
| Microcontroller | ESP32 Dev Module |
| Sensor | JSN-SR04T waterproof ultrasonic — mounts at top of salt tank facing down |
| Red LED | GPIO32, 220Ω — critical level |
| Yellow LED | GPIO33, 220Ω — low level |
| Green LED | GPIO27, 220Ω — good level |
| Power | 5V USB wall charger |

### Wiring

| Connection | Notes |
|---|---|
| JSN-SR04T VCC → ESP32 VIN (5V) | Sensor requires 5V |
| JSN-SR04T Trig → GPIO5 | |
| JSN-SR04T Echo → 1kΩ → GPIO18 → 2kΩ → GND | Voltage divider required — sensor outputs 5V, ESP32 GPIO is 3.3V only |
| LEDs → GPIO32/33/27 (red/yellow/green) via 220Ω → GND | |

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
      │      ├── Controls HA-native alert switches → Google Assistant
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
6. Make sure `HA_TOKEN` is set in `/home/pi/.node-red/environment` on the Pi (systemd-level, CARD-0280) —
   not as a tab-scoped Node-RED Environment Variable
7. Create HA helpers and virtual switches — see Configuration below

---

## Configuration

### Credentials (`secrets.yaml`)

Create `secrets.yaml` in this folder — gitignored, never commit:

```yaml
wifi_ssid: "JCTnet1"
wifi_password: "..."
ap_password: "..."

mqtt_broker: "pi1.local"
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

### HA-Native Switches (CARD-0261, 2026-09-12 — replaced SmartThings-synced virtual switches)

Four HA-native Template Switch helpers (backed by hidden `input_boolean` helpers for
persistence), each exposed to Google Assistant via HA's own native integration except
`salt_test_mode` (deliberately HA-only — a diagnostic action, not something Robin needs;
see `JCTsh-Build-Standards.md` §6.5's exposure test).

| Entity | Purpose | Exposed to Google Home? |
|---|---|---|
| `switch.salt_low_alert` | ON at warning level (< 33%) | Yes |
| `switch.salt_critical_alert` | ON at critical level (< 15%) | Yes |
| `switch.salt_test_mode` | Turn ON in HA to run test sequence | No — HA-only |
| `switch.salt_full_reset` | Turn ON after refilling to clear alerts | Yes |

### Live Salt Level (percent), added 2026-09-12

Two entities, since Google Assistant can't voice-expose an arbitrary numeric percent:

| Entity | Purpose |
|---|---|
| `input_number.salt_level_percent` | Written by Node-RED every reading — the real value, HA-only, not exposed |
| `sensor.softener_salt_level` | Template Sensor mirroring the above, `device_class: humidity` set deliberately (the closest Google-supported class) purely to make it voice-exposable — genuinely mislabeled, not a real humidity reading |

Google's Smart Home API only supports voice-query for a fixed list of sensor `device_class`es
(temperature, humidity, CO2, AQI, PM2.5, VOCs) — a generic percent has no supported class,
so this mislabel is the only way to get the live value voice-accessible at all. Ask
"what's the humidity of Softener Salt Level" to hear it.

**A single combined voice answer ("salt is 26%, no alert") is not achievable** — Google
Home's automation builder cannot insert a live sensor value into a spoken "Assistant says"
response (confirmed 2026-09-12, current platform limitation), and there's no supported way
to route a Google Home speaker's voice query into HA's own Assist pipeline (which *can* do
this natively via a templated custom-sentence response, but only through the HA Companion
app/voice hardware, not a Google Home speaker). Practical options: ask the humidity-labeled
sensor for the percent and a separate custom Google Home automation for alert status
(static text per branch), or use HA Assist for the full combined sentence via the phone app.

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

Turn ON `switch.salt_test_mode` in Home Assistant. Node-RED simulates two readings:
- Step 1: ~27% — yellow LED, `switch.salt_low_alert` on
- Step 2: 0% — red LED, `switch.salt_critical_alert` on

Turn OFF the switch to clear all alerts and return to `ok`.

### Reset After Refilling

Turn ON `switch.salt_full_reset` (HA, or by voice via Google Home). Node-RED clears both alert switches, publishes
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
| `ESP32-project-pins.md` | Full pin assignment table for the actual board in hand (SparkleIoT XH-32S), organized by printed label — corrected 2026-07-13, see file header |
| `sparkleiot-xh-32s-pinout-photo.jpg` | Reference photo of the actual board's silkscreen (SparkleIoT XH-32S) — ground truth for pin labels, since `ESP32-project-pins.md`'s position numbering doesn't match this board |
| `perfboard-layout.md` | Permanent build layout, bus planning, assembly sequence, pre-power checks, power-cycle verification (CARD-0049) |
| `CLAUDE.md` | Claude Code context — constraints and gotchas |
| `archive/salt-sensor-v3-arduino/` | Previous Arduino C++ firmware (reference only — do not use) |
| `archive/water_softener_salt_sensor_v2.ino` | Older version using direct SmartThings API (reference only — do not use) |

---

## Known Behaviors and Limitations

- **GPIO5 (ultrasonic Trig) is a strapping pin:** ESPHome logs a boot-time warning about
  it, but the device boots and runs correctly. The LEDs were moved off the GPIO2/GPIO15
  strapping pins onto GPIO32/33/27 for the perfboard build (CARD-0049).
- **Compile from `C:\esphome\salt-sensor\`, not the repo path:** spaces in
  `JCT Documents` break the ESP-IDF compiler. Copy `salt-sensor.yaml` and `secrets.yaml`
  there after any edit.
