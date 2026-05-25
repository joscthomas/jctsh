# Front Porch Temp Sensor

Environmental sensor for the front porch. Monitors temperature, pressure, and illuminance. Sends push notifications to both household phones when temperature crosses a configurable threshold — between 6am and 10pm only.

---

## Hardware

| Component | Detail |
|---|---|
| Microcontroller | ESP32 DevKitC-32, 38-pin, CP2102 USB-C |
| Temp/pressure sensor | BME280 — currently deployed as BMP280 (counterfeit module); genuine BME280 ordered |
| Light sensor | BH1750 (GY-302), I2C |
| Firmware | ESPHome |
| Power | USB-C from porch outlet |

See `ESP32pins.png` for the full ESP32 DevKitC-32 pinout reference.

> **BME280 note:** All three Podazz BME280 modules in the initial batch are counterfeit BMP280s (no humidity support). The ESPHome config uses `bmp280_i2c` platform and omits the humidity sensor until genuine BME280s arrive. Humidity shows Unknown in HA — expected. When genuine BME280s arrive: swap module, change `bmp280_i2c` → `bme280_i2c` in `front-porch-temp-sensor.yaml`, uncomment the humidity sensor, and re-enable the Humidity favorite in the HA Overview page.

---

## Wiring

Both sensors share a single I2C bus.

| Sensor | Pin | ESP32 Pin | Notes |
|---|---|---|---|
| BME280 (temp/pressure sensor) | VCC | 3.3V | |
| BME280 (temp/pressure sensor) | GND | GND | |
| BME280 (temp/pressure sensor) | SDA | GPIO21 | Shared I2C bus |
| BME280 (temp/pressure sensor) | SCL | GPIO22 | Shared I2C bus |
| BH1750 (light sensor) | VCC | 3.3V | |
| BH1750 (light sensor) | GND | GND | |
| BH1750 (light sensor) | SDA | GPIO21 | Shared I2C bus |
| BH1750 (light sensor) | SCL | GPIO22 | Shared I2C bus |
| BH1750 (light sensor) | ADDR | GND | Sets I2C address to 0x23 |

Wire color convention: red = 3.3V, black = GND, blue = SDA, yellow = SCL.

See `wiring.md` for the full breadboard wiring checklist.

---

## Architecture

```
BME280 (temp/pressure sensor)  BH1750 (light sensor)
           │                          │
           └──────── I2C bus ─────────┘
                         │
               ESP32 DevKitC-32
                         │
         MQTT: jctsh/components/front-porch-temp-sensor/...
                         ▼
               Mosquitto broker (Raspberry Pi)
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
        Home Assistant          Node-RED
     Temperature sensor      log router:
     Pressure sensor         .../log → log dashboard
     Illuminance sensor      watchdog: heartbeat monitor
          │
          ├── Front Porch Temp Alert + Reminder automation
          └── Front Porch Temp Dropping automation
                    │
                    ▼
           notify.mobile_app_pixel_10_pro_xl
           notify.mobile_app_pixel_7_pro
```

---

## How It Works

### Sensors

Temperature, pressure, and illuminance are published to MQTT every 60 seconds. Home Assistant auto-discovers all entities via MQTT discovery. Temperature is converted to °F in the ESPHome firmware.

### Heartbeat

Every 5 minutes, the firmware publishes a heartbeat to `jctsh/components/front-porch-temp-sensor/heartbeat` (JSON with uptime, RSSI, and temperature) and a log message to `jctsh/components/front-porch-temp-sensor/log`. The Node-RED watchdog and the Python log server pick up both automatically via wildcard subscriptions.

### Notifications

Two HA automations use template triggers for precise threshold crossing detection:

| Automation | Condition | Action |
|---|---|---|
| Front Porch Temp Alert + Reminder | temp ≥ threshold AND 6am–10pm | Alert both phones immediately; reminder both phones 15 min later (once) |
| Front Porch Temp Dropping | temp < threshold AND 6am–10pm | Notify both phones |

Threshold is configurable via `input_number.front_porch_temp_threshold` (default 80°F). Adjust in HA: Settings → Devices & Services → Helpers.

No door sensor dependency — notifications fire based on temperature and time window only.

---

## Files

| File | Purpose |
|---|---|
| `front-porch-temp-sensor.yaml` | ESPHome firmware config |
| `secrets.yaml` | Credentials (gitignored) |
| `secrets.yaml.template` | Credential template (committed) |
| `wiring.md` | Breadboard wiring checklist |
| `flashing.md` | Flash procedure (Steps 3–5) |
| `integration.md` | HA setup steps (Steps 6–10) |
| `testing.md` | End-to-end test procedure (Step 11) |
| `perfboard-layout.md` | Perfboard transfer instructions (Step 12) |
| `mounting.md` | Physical mounting instructions (Step 13) |
| `automation-temp-alert.yaml` | HA automation YAML — alert + reminder |
| `automation-temp-dropping.yaml` | HA automation YAML — temp dropping |
| `dashboard-card.yaml` | Reference entity list for HA Overview |
| `ESP32pins.png` | ESP32 DevKitC-32 pinout reference |
