# Hiking Monitor — Operations Guide

## Hardware Overview

| Component | Role |
|---|---|
| ESP32 + sensors | Reads temperature, humidity, pressure, UV index every 2 minutes |
| LiPo battery + TP4056+boost | Power system — boost converter outputs 5.7V to ESP32 |
| Slide switch (on VOUT+ line) | Powers ESP32 on/off — does not affect battery charging |
| Dock detect (GPIO32 divider) | Detects USB charger connected; suppresses data collection when docked |

---

## Operating Modes

### Field Mode (WiFi unavailable)
- ESP32 reads sensors every 2 minutes
- Each reading is written to onboard storage (`/hike_log.jsonl`)
- Data accumulates until the device reconnects to home WiFi
- Display updates every 2 minutes with current readings

### Home Mode (WiFi + MQTT connected)
- On connect: all accumulated field readings are replayed to MQTT → Google Sheets immediately
- Live readings every 2 minutes are published directly to MQTT → Google Sheets
- Heartbeat published every 5 minutes (visible in log dashboard)

### Docked Mode (USB charger connected)
- Dock detect (GPIO32) goes HIGH when USB is plugged into the TP4056
- Data collection and LittleFS writes are suppressed — no new readings logged or published
- Heartbeat still fires every 5 minutes if WiFi is connected
- Battery charges independently of the switch position

---

## Power Switch Behavior

The slide switch interrupts VOUT+ between the TP4056 boost output and ESP32 VIN.

| Switch | USB to TP4056 | Result |
|---|---|---|
| OFF | Unplugged | ESP32 off, battery not charging |
| OFF | Plugged in | ESP32 off, **battery charging** |
| ON | Unplugged | ESP32 running from battery |
| ON | Plugged in | ESP32 running, battery charging |

**Battery charges regardless of switch position when USB is connected.**

---

## Standard Workflow

### Before a Hike
1. Turn switch **OFF**
2. Unplug USB charger (undock)
3. Take the device

### Starting the Hike
1. Turn switch **ON**
2. Device boots — if no home WiFi in range, enters field mode automatically
3. Sensor readings begin within 2 minutes; data written to onboard storage

### During the Hike
- No action needed — device reads and logs every 2 minutes
- Display shows current temp, humidity, pressure trend, and UV index

### Ending the Hike
1. Turn switch **OFF**
2. Hike data is safely stored in onboard storage until next upload

### Getting Home — Uploading Data
1. Plug in USB charger (dock)
2. Turn switch **ON**
3. Device boots and connects to home WiFi
4. Accumulated hike data replays automatically to Google Sheets
5. Log dashboard shows "Hike log replay complete." when upload finishes
6. Dock detect suppresses any further new readings
7. Turn switch **OFF** when done, or leave ON while battery finishes charging

---

## Log Dashboard Messages

| Message | Meaning |
|---|---|
| `Hiking monitor online - ESPHome ..., IP: ...` | Device booted and connected to WiFi |
| `MQTT connected` | MQTT broker connection established |
| `Replaying N hike readings...` | Uploading accumulated field data |
| `Hike log replay complete.` | All field data uploaded to Sheets — safe to turn off |
| `Docked — data suppressed while charging` | USB charger detected; collection paused |
| `Undocked — field mode active` | USB charger removed; collection active |
| `Heartbeat - uptime: Xh Ym, RSSI: ...` | Device alive, WiFi connected |
| `MQTT disconnected` | WiFi or broker connection lost |

---

## Google Sheets

Readings are archived in **JCTsh Environmental Data** (Google Sheets).
- **Data tab** — raw readings with UTC timestamps
- **View tab** — MST timestamps for readability

Each row: timestamp, component, temp (°F), humidity (%), pressure (hPa), UV index, battery voltage (V), RSSI (dBm).
