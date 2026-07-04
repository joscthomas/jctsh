# Hiking Sensor

Portable ESP32 environmental sensor carried on hikes — measures temperature, humidity,
pressure, and UV index, displays live readings on an e-ink screen, logs to onboard flash
storage, and syncs the full hike dataset to Google Sheets automatically on return home.

**Status:** Complete and field-tested — perfboard, deep sleep, Pixel hotspot sync (Step 21),
GPS correlation (Steps 19-20), and hiking observations pipeline (Steps 23-26) all done.
Step 15 (permanent enclosure) remains; a temporary standoff enclosure is in use.
As of 2026-07-03: original LiPo failed in the field and was replaced from spare stock;
a firmware low-battery cutoff was added as a result (see Power System below).
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
| Battery | EEMB LiPo pouch 603449 (1100mAh) — built-in PCM protection (overcharge/over-discharge/overcurrent/short-circuit), UN 38.3 compliant |
| Power module | TP4056 + boost combined module (charges LiPo, boosts to 5V) |
| Mode switch | Slide switch, GPIO27 — ON = hiking mode (awake), OFF = sleep/upload mode |
| Dock detect | Voltage divider off TP4056 USB VBUS sense, GPIO32 — wakes device on USB connect |
| Firmware | ESPHome with custom C++ component for onboard flash logging and WiFi replay |

See [ESP32-project-pins.md](ESP32-project-pins.md) for the full pin assignment table.

---

## Architecture

The device operates in four modes, controlled by the slide switch (GPIO27) and dock
detect (GPIO32):

| Mode | Switch | USB | Behavior |
|---|---|---|---|
| Field | ON | No | Read sensors every 2 min, log to SPIFFS, no WiFi |
| Home | ON | No (WiFi in range) | Read sensors every 2 min, publish live to MQTT, replay SPIFFS log |
| Upload | OFF | Yes | Auto-wakes via dock detect, replays SPIFFS log, stays awake while docked |
| Sleep | OFF | No | Deep sleep, ~10µA (ESP32 only — see Power System note on boost quiescent draw) |

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

Pressure is shown as a trend arrow (↑ rising / → steady / ↓ falling). There is no manual
refresh button — the display redraws on every 2-minute sensor cycle. E-ink retains its
last frame with zero power, so the display remains readable while the device is asleep.

### Onboard Logging

Each reading is timestamped using the NTP-synced system clock (the device stays in its
charging cradle between hikes, so the clock remains accurate across any hike duration).
Readings are stored in SPIFFS flash and replayed in order on next home WiFi connection.

### Heartbeat

Every 5 minutes in home mode, the device publishes a heartbeat to
`jctsh/components/hiking-monitor/heartbeat`. The Node-RED watchdog monitors this and
sends a push notification to the Pixel if silent for more than 35 minutes.

### Power System and Low-Battery Cutoff

The LiPo's own PCM handles hard overcharge/over-discharge/overcurrent/short-circuit
protection, but the TP4056+boost module has no concept of refusing to draw from a
nearly-dead cell — as the battery nears depletion, the boost converter draws *more*
current to hold its output steady, which can crater the cell faster than its PCM can
react (a "voltage cliff"). This is what caused the original battery to fail in the
field on 2026-07-03 with no advance warning, including two spurious MQTT reconnects
from boost-converter glitching on the GPIO32 dock-detect line as the cell died.

As of that date, firmware includes a `low_battery_shutdown` script: below 3.4V (checked
at boot and during the 2-minute sensor interval, only while running on battery, not
docked), the device forces deep sleep and shows a persistent "LOW BATTERY / Recharge
now" message on the e-ink display — visible with zero power, since e-ink holds its last
frame. It also publishes an MQTT `Alert`-category log message when connected. This acts
*before* the cell's own PCM has to trip, trading a silent hard stop for an early, visible
warning.

Note the always-on boost converter (VOUT+ runs directly to ESP32 VIN, not gated by the
switch) means actual sleep-mode battery drain is dominated by the boost module's own
quiescent current draw, not the ESP32's ~10µA deep sleep figure — the boost module's
quiescent current isn't documented by the manufacturer, so real standby runtime is
unmeasured; put a multimeter in series (mA range) between the battery and the TP4056
BAT+ pad during sleep for an actual figure if needed.

See `JCTsh-Build-Standards.md` §2.14 (Battery-Powered Component Safety Standards) for
the full set of battery safety practices this build follows, which now apply to all
JCTsh battery-powered components.

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
