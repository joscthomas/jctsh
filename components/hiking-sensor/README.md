# Hiking Sensor

Portable ESP32 environmental sensor carried on hikes — measures temperature, humidity,
pressure, and UV index, displays live readings on an e-ink screen, logs to onboard flash
storage, and syncs the full hike dataset to Google Sheets automatically on return home.

**Status:** In Progress — perfboard complete; Step 21 (Pixel hotspot sync) and
Step 15 (enclosure) remaining
**Hardware:** ESP32 + BME280 + LTR-390 + Waveshare 2.13" e-ink display + LiPo

---

## What It Solves

Trail conditions in Tucson — heat, UV exposure, pressure trends — are not captured by
home or office sensors. This device provides a personal environmental record for every
hike, timestamped and correlated to the GPS track from GaiaGPS, and archived in Google
Sheets alongside data from all other JCTsh environmental sensors. No WiFi is needed on
the trail; the device logs to flash and syncs the full dataset when it reconnects at home.

---

## Hardware

| Component | Details |
|---|---|
| Microcontroller | ESP32 DevKitC-32, 38-pin, CP2102, USB-C |
| Temp / humidity / pressure | BME280 (genuine GY-BME280), I2C |
| UV index | Adafruit LTR-390, I2C — must face open sky |
| Display | Waveshare 2.13" e-ink, 250×122, SSD1680, partial refresh |
| Battery | EEMB LiPo pouch 603449 (1100mAh) |
| Power module | TP4056 + boost combined module (charges LiPo, boosts to 5V) |
| Firmware | ESPHome with custom C++ component for onboard flash logging and WiFi replay |

See [ESP32-project-pins.md](ESP32-project-pins.md) for the full pin assignment table.

---

## Architecture

The device operates in two modes depending on WiFi availability.

**Field mode** — during a hike, no WiFi:

```
BME280 + LTR-390
      │  I2C
      ▼
ESP32 / ESPHome
      ├── Display update every 2 minutes
      └── Log reading to SPIFFS flash (timestamp + sensor values)
```

**Home mode** — in charging cradle, on JCTnet1:

```
ESP32 / ESPHome
      │  MQTT: jctsh/components/hiking-monitor/...
      ▼
Mosquitto broker (Raspberry Pi)
      │
      ├──► Node-RED
      │       ├── Routes data to Google Sheets via Apps Script
      │       └── Populates lat/lon from GPSLogger trackpoints by timestamp
      │
      └──► Log dashboard
```

SPIFFS replay publishes stored hike readings in sequence using original hike timestamps.
Node-RED's wildcard data handler catches the data automatically — no new flow needed.

**Pixel hotspot sync** (Step 21 — in progress): when the Pixel hotspot is active while
traveling, the device connects and replays stored readings to the home broker over
cellular via DuckDNS. See [wifi-config.md](wifi-config.md) for the full hotspot workflow.

**GPS correlation** (Steps 19–20 — complete): GPSLogger runs on the Pixel during hikes
and posts coordinates to a Node-RED HTTP-in endpoint. Node-RED matches GPS trackpoints
to sensor readings by timestamp and populates `lat`/`lon` in the Google Sheets archive.

---

## Quick Start

1. Copy `secrets.yaml.template` → `secrets.yaml` and fill in credentials from
   `credentials.local.md`
2. See [JCTsh-hiking-sensor-phase1.md](JCTsh-hiking-sensor-phase1.md) for the full
   build plan and step sequence
3. See [flashing instructions in build doc] for first flash via USB
4. See [testing.md](testing.md) to verify field and home mode operation

---

## How It Works

### Display

Updates every 2 minutes with four fields:

```
Temp:      87°F    Humidity: 32%
UV Index:  9.2     Pressure: ↓
```

Pressure is shown as a trend arrow (↑ rising / → steady / ↓ falling). A button press
wakes the display on demand between scheduled updates.

### Onboard Logging

Each reading is timestamped using the NTP-synced system clock (the device stays in its
charging cradle between hikes, so the clock remains accurate across any hike duration).
Readings are stored in SPIFFS flash and replayed in order on next home WiFi connection.

### Heartbeat

Every 5 minutes in home mode, the device publishes a heartbeat to
`jctsh/components/hiking-monitor/heartbeat`. The Node-RED watchdog monitors this and
sends a push notification to the Pixel if silent for more than 35 minutes.

---

## Files

| File | Purpose |
|---|---|
| `hiking-sensor.yaml` | ESPHome firmware config |
| `secrets.yaml` | Credentials — gitignored, never commit |
| `secrets.yaml.template` | Credential template |
| `wiring.md` | Breadboard wiring reference and checklist |
| `voltage-divider.md` | Voltage divider calculations for LiPo monitoring |
| `ESP32-project-pins.md` | Full 38-pin assignment table |
| `perfboard-layout.md` | Permanent soldered build layout |
| `power-system.md` | Power system design and measurements |
| `enclosure-prototype.md` | Field prototype enclosure (two-board sandwich) |
| `wifi-config.md` | Pixel hotspot setup and sync workflow (Step 21) |
| `gps-pipeline.md` | GPSLogger → Node-RED GPS correlation pipeline (Steps 19–20) |
| `data-pipeline.md` | Full data pipeline from device to Google Sheets |
| `testing.md` | End-to-end test procedure |
| `mqtt-account-setup.md` | Mosquitto account creation |
| `CLAUDE.md` | Claude Code context — constraints and gotchas |
| `JCTsh-hiking-sensor-phase1.md` | Full planning document and build step sequence |
