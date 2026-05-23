# Water Softener Salt Level Sensor — v3

An ESP32-based ultrasonic salt level monitor for residential water softeners. The ESP32 publishes readings over MQTT; Node-RED applies threshold logic and bridges to SmartThings via Home Assistant.

---

## Architecture

```
ESP32 (JSN-SR04T sensor)
  │
  │  MQTT (saltlevel/reading)
  ▼
Mosquitto broker (Raspberry Pi)
  │
  ├──► Node-RED
  │      │  applies threshold logic
  │      │  controls HA virtual switches
  │      │  publishes status + notify back to ESP32
  │      ▼
  │    Home Assistant ──► SmartThings
  │                         (alerts, test mode, reset switches)
  │
  └──► ESP32 subscribes
         saltlevel/status  → drives LEDs
         saltlevel/notify  → writes to web monitor log
```

---

## Features

- **Ultrasonic distance sensing** — JSN-SR04T waterproof sensor, 15-sample median filtering
- **Three-LED status display** — Green (good), Yellow blinking (warning), Red blinking (critical)
- **MQTT integration** — publishes readings every 12 hours; status driven by Node-RED
- **Web monitor** — live log at `http://salt-sensor.local`, auto-refreshes every 5 seconds
- **OTA firmware updates** — password-protected, no USB required after initial flash
- **Test mode** — triggered via SmartThings switch, simulates warning and critical readings
- **Reset switch** — triggered via SmartThings after refilling, clears active alerts
- **Node-RED notify log** — key events (alerts sent/cleared, test mode, errors) pushed directly to the web monitor
- **WiFi auto-reconnect** — recovers from dropped connections automatically
- **mDNS** — `salt-sensor.local` resolves regardless of dynamic IP

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
| WebServer | Built-in (ESP32 core) |
| ESPmDNS | Built-in (ESP32 core) |
| PubSubClient | Library Manager — search "PubSubClient" by Nick O'Leary |

### Arduino IDE Board Settings

- Board: **ESP32 Dev Module**
- Upload Speed: **921600**
- Flash Frequency: **80MHz**
- Partition Scheme: **Default 4MB with spiffs**

---

## Configuration

### ESP32 — secrets.h

Create `secrets.h` in the sketch folder (excluded from version control via `.gitignore`):

```cpp
#ifndef SECRETS_H
#define SECRETS_H

#define WIFI_SSID      "your_wifi_ssid"
#define WIFI_PASSWORD  "your_wifi_password"

#define MQTT_HOST      "raspberrypi.local"
#define MQTT_PORT      1883
#define MQTT_USER      "your_mqtt_user"
#define MQTT_PASS      "your_mqtt_password"

#define OTA_PASSWORD   "your_ota_password"

#endif
```

### Calibration

Update these constants in the sketch before flashing:

```cpp
const float FULL_DISTANCE_CM  = 20.4;  // sensor-to-salt when tank is full
const float EMPTY_DISTANCE_CM = 43.0;  // sensor-to-salt when tank is empty
```

1. Mount the sensor at the top of the salt tank facing down
2. Fill the tank to its normal maximum level
3. Note the distance in the web monitor → set as `FULL_DISTANCE_CM`
4. Measure from the sensor face to the tank floor → set as `EMPTY_DISTANCE_CM`
5. Flash via OTA

---

## MQTT Topics

| Topic | Direction | Payload |
|---|---|---|
| `saltlevel/reading` | ESP32 → Node-RED | `{"distance_cm":25.3,"percent":78}` |
| `saltlevel/status` | Node-RED → ESP32 | `ok` \| `warning` \| `critical` \| `error` |
| `saltlevel/notify` | Node-RED → ESP32 | Plain text log messages |

---

## Node-RED Setup

### Import the flow

1. Open Node-RED at `http://raspberrypi.local:1880`
2. **≡ menu → Import** → select `nodered_saltlevel_flow.json` → **Replace existing nodes**
3. Open the **Mosquitto (Pi)** broker node, go to the **Security** tab, enter MQTT username and password, click **Update**
4. Click **Deploy**

### HA token

The flow reads the Home Assistant long-lived access token from the `HA_TOKEN` environment variable. Set it in the Node-RED systemd service:

```bash
sudo systemctl edit nodered
```

Add:
```
[Service]
Environment="HA_TOKEN=your_ha_long_lived_token"
```

Then:
```bash
sudo systemctl daemon-reload && sudo systemctl restart nodered
```

---

## Home Assistant Setup

Create four virtual switches in Home Assistant (synced from/to SmartThings):

| Entity ID | Purpose |
|---|---|
| `switch.salt_low_alert` | Turned ON by Node-RED when salt reaches warning level |
| `switch.salt_critical_alert` | Turned ON by Node-RED when salt reaches critical level |
| `switch.salt_test_mode` | Turn ON in SmartThings to activate test mode |
| `switch.salt_full_reset` | Turn ON in SmartThings after refilling to clear alerts |

---

## Alert Thresholds

Thresholds are set in the Node-RED `fn_threshold` function node:

```js
const WARNING_PERCENT  = 33.0;   // yellow LED / warning alert
const CRITICAL_PERCENT = 15.0;   // red LED / critical alert
```

---

## Web Monitor

Open a browser on any device on the same network:

```
http://salt-sensor.local       <- recommended, always works
http://<esp32-ip-address>      <- direct IP fallback
```

The monitor page:
- Auto-refreshes every 5 seconds
- Shows the last 100 log lines, color-coded:
  - **Red** — Critical alerts
  - **Orange** — Warning alerts
  - **Cyan** — MQTT events and Node-RED notify messages (test mode, alerts sent, errors)
  - **Grey** — Boot messages
  - **Red bold** — Errors
- Displays current status, distance, and salt percentage at the top

### Operational log messages from Node-RED

Key events are pushed to the web monitor via `saltlevel/notify` so it remains the single place to check for problems:

| Message | Meaning |
|---|---|
| `WARNING — salt at X%. Alert sent to SmartThings.` | Warning alert fired |
| `CRITICAL — salt at X%. Alert sent to SmartThings.` | Critical alert fired |
| `Warning/Critical alert cleared — salt level OK.` | Alert cleared after refill |
| `Reset acknowledged — all alerts cleared.` | Reset switch was triggered |
| `HA API error 5xx — alerts may not have reached SmartThings.` | Node-RED → HA call failed |

---

## OTA Updates

After the initial USB flash:

1. Power the ESP32
2. In Arduino IDE → **Tools → Port** → select `salt-sensor at <ip-address>`
3. Click **Upload**
4. Enter OTA password when prompted

> The 3 rapid LED flashes at boot confirm a successful OTA reboot.

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
3. Node-RED alternates between two simulated readings every second:
   - **Step 1:** ~37cm → ~27% → warning zone (yellow LED, warning alert to SmartThings)
   - **Step 2:** 43cm → 0% → critical zone (red LED, critical alert to SmartThings)
4. Progress appears in the web monitor log in real time
5. Turn OFF the switch — Node-RED clears all alerts and publishes `ok` to the ESP32

---

## Reset Switch Behavior

When salt is refilled and **Salt Full Reset** is turned ON in SmartThings:

1. Node-RED turns off `switch.salt_critical_alert` and `switch.salt_low_alert` in HA
2. Publishes `ok` status to the ESP32 — green LED goes solid
3. Turns the reset switch back OFF automatically
4. Logs `Reset acknowledged — all alerts cleared.` in the web monitor

The reset switch is only acted on when a warning or critical alert is active.

---

## Project Structure

```
Salt Sensor/
├── salt-sensor.ino                      # ESP32 sketch
├── water_softener_salt_sensor_v2.ino   # Previous version (direct SmartThings API)
├── nodered_saltlevel_flow.json         # Node-RED flow
├── secrets.h                           # Credentials — gitignored, never commit
└── README.md
```

---

## Future Plans

- [ ] Node-RED watchdog heartbeat — periodic publish to `saltlevel/notify` (e.g. every hour) so a Node-RED outage becomes visible in the web monitor without needing to check the Pi
- [ ] MQTT broker authentication hardening — move from plaintext credentials to TLS client certificates

---

## License

MIT License — free to use, modify, and distribute with attribution.

---

## Author

Built for a residential water softener installation in Tucson, Arizona.
Developed iteratively with hardware testing at each stage.
