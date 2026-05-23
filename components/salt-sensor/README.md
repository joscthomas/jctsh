# Water Softener Salt Level Sensor

An ESP32-based ultrasonic salt level monitor for residential water softeners. Part of the [jctsh monorepo](../../README.md).

---

## Architecture

```
ESP32 (JSN-SR04T sensor)
  │
  │  MQTT  jctsh/sensors/salt-sensor/data  {"distance_cm":25.3}
  ▼
Mosquitto broker (Raspberry Pi)
  │
  ├──► Node-RED
  │      │  reads calibration from HA input_number helpers
  │      │  calculates salt percent
  │      │  applies alert thresholds
  │      │  controls HA virtual switches → SmartThings
  │      │  publishes status back to ESP32
  │      ▼
  │    Home Assistant ──► SmartThings
  │                         (alerts, test mode, reset switches)
  │
  └──► ESP32 subscribes
         jctsh/sensors/salt-sensor/status  → drives LEDs
```

Log dashboard: `http://raspberrypi.local/` — primary diagnostic tool.

---

## Features

- **Ultrasonic distance sensing** — JSN-SR04T waterproof sensor, 15-sample median filtering
- **Three-LED status display** — Green solid (good), Yellow blinking (warning), Red blinking (critical)
- **MQTT integration** — publishes raw distance every 12 hours; percent and status driven by Node-RED
- **Calibration via HA** — full/empty distances set as HA input_number helpers; no reflash needed
- **OTA firmware updates** — password-protected, no USB required after initial flash
- **Test mode** — triggered via SmartThings switch, simulates warning and critical readings
- **Reset switch** — triggered via SmartThings after refilling, clears active alerts
- **WiFi auto-reconnect** — recovers from dropped connections automatically

---

## Hardware

| Component | Details |
|---|---|
| Microcontroller | ESP32 Dev Module |
| Sensor | JSN-SR04T Waterproof Ultrasonic |
| Status LEDs | Red, Yellow, Green with 220Ω resistors |
| Enclosure | IP65 ABS plastic box (115×90×55mm) |
| Power | 5V USB wall charger into ESP32 USB port |

### Wiring

| Component | Pin/Wire | Connects To |
|---|---|---|
| JSN-SR04T Red | VCC | ESP32 5V / VIN |
| JSN-SR04T Black | GND | ESP32 GND |
| JSN-SR04T Yellow/Blue | Trig | ESP32 GPIO 5 |
| JSN-SR04T Green/White | Echo | 1kΩ → ESP32 GPIO 18 → 2kΩ → GND |
| Red LED Anode (+) | — | GPIO 2 via 220Ω |
| Yellow LED Anode (+) | — | GPIO 15 via 220Ω |
| Green LED Anode (+) | — | GPIO 4 via 220Ω |
| All LED Cathodes (−) | — | GND |

> **Note:** The 1kΩ/2kΩ voltage divider on the Echo pin is required — the JSN-SR04T outputs 5V logic; the ESP32 GPIO is 3.3V only.

### Schematic

```
JSN-SR04T
   Red   ─────► ESP32 5V / VIN
   Black ─────► ESP32 GND
   Trig  ─────► GPIO 5
   Echo  ──1kΩ──► GPIO 18 ──2kΩ──► GND

LEDs:
   GPIO 2  ──220Ω──► Red LED    (+) ──(-)──► GND
   GPIO 15 ──220Ω──► Yellow LED (+) ──(-)──► GND
   GPIO 4  ──220Ω──► Green LED  (+) ──(-)──► GND
```

---

## Software

### Arduino Libraries Required

| Library | Install via |
|---|---|
| WiFi | Built-in (ESP32 core) |
| ArduinoOTA | Built-in (ESP32 core) |
| PubSubClient | Library Manager — search "PubSubClient" by Nick O'Leary |

### Arduino IDE Board Settings

- Board: **ESP32 Dev Module**
- Upload Speed: **921600**
- Flash Frequency: **80MHz**
- Partition Scheme: **Default 4MB with spiffs**

---

## Configuration

### ESP32 — secrets.h

Create `secrets.h` in the sketch folder (gitignored — never commit):

```cpp
#ifndef SECRETS_H
#define SECRETS_H

#define WIFI_SSID      "your_wifi_ssid"
#define WIFI_PASSWORD  "your_wifi_password"

#define MQTT_HOST      "raspberrypi.local"
#define MQTT_PORT      1883
#define MQTT_USER      "salt-sensor"
#define MQTT_PASS      "your_mqtt_password"

#define OTA_PASSWORD   "your_ota_password"

#endif
```

### Calibration

Calibration is set in Home Assistant — no reflash required.

1. Mount the sensor at the top of the salt tank facing down
2. Fill the tank to its normal maximum level and note the distance in the log dashboard
3. Measure from the sensor face to the tank floor
4. In HA: **Settings → Helpers** and set:
   - `input_number.salt_full_distance_cm` — sensor-to-salt distance when full
   - `input_number.salt_empty_distance_cm` — sensor-to-salt distance when empty
5. Changes take effect within 60 seconds (next Node-RED poll)

---

## MQTT Topics

| Topic | Direction | Payload |
|---|---|---|
| `jctsh/sensors/salt-sensor/data` | ESP32 → Node-RED | `{"distance_cm":25.3}` retained |
| `jctsh/sensors/salt-sensor/status` | Node-RED → ESP32 | `ok` \| `warning` \| `critical` \| `error` |
| `jctsh/sensors/salt-sensor/log` | both → log server | `{"component":"salt-sensor","category":"...","message":"..."}` |

---

## Node-RED Setup

### Import the flow

1. Open Node-RED at `http://raspberrypi.local:1880`
2. Import `core/node-red/core.flow.json` first if the MQTT broker node is not already present
3. **≡ menu → Import** → select `salt-sensor.flow.json` → **Replace existing nodes**
4. Click **Deploy**

### HA token

The flow reads the Home Assistant long-lived access token from the `HA_TOKEN` environment variable. Set it in Node-RED UI: **Settings → Environment Variables → HA_TOKEN**.

---

## Home Assistant Setup

### Virtual switches (synced to SmartThings)

| Entity ID | Purpose |
|---|---|
| `switch.salt_low_alert` | Turned ON by Node-RED at warning level |
| `switch.salt_critical_alert` | Turned ON by Node-RED at critical level |
| `switch.salt_test_mode` | Turn ON in SmartThings to activate test mode |
| `switch.salt_full_reset` | Turn ON in SmartThings after refilling to clear alerts |

### Calibration helpers

| Entity ID | Default | Purpose |
|---|---|---|
| `input_number.salt_full_distance_cm` | 20.4 | Sensor-to-salt distance (cm) at 100% full |
| `input_number.salt_empty_distance_cm` | 43.0 | Sensor-to-salt distance (cm) at 0% empty |

Create via: Settings → Helpers → + Create Helper → Number.

---

## Alert Thresholds

Set in the Node-RED `fn_threshold` function node:

```js
const WARNING_PERCENT  = 33.0;   // yellow LED / warning alert
const CRITICAL_PERCENT = 15.0;   // red LED / critical alert
```

---

## Log Dashboard

Open `http://raspberrypi.local/` on any device on the network. Each reading produces two log entries:

| Category | Message | Source |
|---|---|---|
| Sensor | `Distance: 20.3 cm` | ESP32 |
| Sensor | `Salt: 100% (20.3 cm)` | Node-RED |

---

## OTA Updates

After the initial USB flash, update via OTA. Arduino IDE 2 has a port substitution bug on Windows — use espota directly instead:

1. In Arduino IDE: **Sketch → Export Compiled Binary** to produce `salt-sensor.ino.bin`
2. Power-cycle the ESP32
3. Immediately run:

```
"C:\Users\...\Arduino15\packages\esp32\hardware\esp32\3.3.8\tools\espota.exe" -i <esp32-ip> -p 3232 -a <OTA_PASSWORD> -f salt-sensor.ino.bin
```

> Three rapid LED flashes at boot confirm a successful OTA reboot.

---

## LED Status Reference

| LED State | Meaning |
|---|---|
| Green solid | Salt level good (> 33%) |
| Yellow blinking | Salt level low (15–33%) — warning alert sent |
| Red blinking | Salt level critical (< 15%) — critical alert sent |
| All three rapid flash × 3 | Normal boot sequence |
| All three blinking together | Sensor hardware error — check wiring |

---

## Test Mode

1. Turn ON **Salt Test Mode** switch in SmartThings
2. Wait up to 60 seconds for Node-RED to detect it
3. Node-RED simulates two readings at 1-second intervals:
   - **Step 1:** warning zone (~27%) — yellow LED, warning alert to SmartThings
   - **Step 2:** critical zone (0%) — red LED, critical alert to SmartThings
4. Progress appears in the log dashboard in real time
5. Turn OFF the switch — Node-RED clears all alerts and publishes `ok` to the ESP32

---

## Reset Switch Behavior

When salt is refilled and **Salt Full Reset** is turned ON in SmartThings:

1. Node-RED turns off `switch.salt_critical_alert` and `switch.salt_low_alert` in HA
2. Publishes `ok` status to the ESP32 — green LED goes solid
3. Turns the reset switch back OFF automatically
4. Logs `Reset acknowledged — all alerts cleared.`

The reset switch is only acted on when a warning or critical alert is active.

---

## Project Structure

```
salt-sensor/
├── salt-sensor/
│   ├── salt-sensor.ino     # ESP32 sketch
│   └── secrets.h           # Credentials — gitignored, never commit
├── salt-sensor.flow.json   # Node-RED flow
├── archive/
│   └── water_softener_salt_sensor_v2.ino  # Previous version (reference only)
├── CLAUDE.md
└── README.md
```

---

## Future Plans

- [ ] MQTT broker authentication hardening — TLS client certificates

---

## License

MIT License — free to use, modify, and distribute with attribution.

---

## Author

Built for a residential water softener installation in Tucson, Arizona.
Developed iteratively with hardware testing at each stage.
