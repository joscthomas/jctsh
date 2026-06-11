# Hiking Monitor — Operations Guide

## Hardware Overview

| Component | Role |
|---|---|
| ESP32 + sensors | Reads temperature, humidity, pressure, UV index every 2 minutes |
| LiPo battery + TP4056+boost | Power system — boost converter outputs 5.7V directly to ESP32 VIN |
| Slide switch (GPIO27 signal) | Signals hiking mode — switch ON pulls GPIO27 LOW; not in power path |
| Dock detect (GPIO32 divider) | Detects USB charger connected; wakes ESP32 from deep sleep for upload |

---

## Operating Modes

### Sleep Mode (switch OFF, no USB)
- ESP32 in deep sleep (~10μA) — negligible battery drain
- Wakes on: switch turned ON (GPIO27 LOW) or USB plugged in (GPIO32 HIGH)

### Field Mode (switch ON, no WiFi)
- ESP32 reads sensors every 2 minutes
- Each reading is written to onboard storage (`/hike_log.jsonl`)
- Data accumulates until the device reconnects to home WiFi
- Display refreshes every 2 minutes with current readings

### Home Mode (switch ON, WiFi + MQTT connected)
- On connect: all accumulated field readings are replayed to MQTT → Google Sheets immediately
- Live readings every 2 minutes are published directly to MQTT → Google Sheets
- Heartbeat published every 5 minutes (visible in log dashboard)

### Upload Mode (switch OFF, USB connected)
- Device auto-wakes when USB is plugged in (dock detect HIGH on GPIO32)
- Connects to home WiFi and replays all accumulated hike data to Google Sheets
- No new sensor readings collected or logged
- Battery charges simultaneously
- Returns to deep sleep when USB is unplugged

---

## Power Switch Behavior

The slide switch signals hiking mode via GPIO27. VOUT+ runs directly to ESP32 VIN — the switch is not in the power path. Deep sleep replaces the hard power cut.

| Switch | USB to TP4056 | Result |
|---|---|---|
| OFF | Unplugged | Deep sleep (~10μA); battery not charging |
| OFF | Plugged in | Auto-wake → upload mode; battery charging |
| ON | Unplugged | Active → field or home mode depending on WiFi |
| ON | Plugged in | Active → home mode; battery charging |

**Battery charges regardless of switch position when USB is connected.**

---

## Standard Workflow

### Before a Hike
- Confirm switch is OFF (device sleeping)
- To charge before leaving: plug in USB → device auto-wakes and charges → unplug when done → device returns to sleep

### Starting the Hike
1. Turn switch **ON**
2. Device wakes — if no home WiFi in range, enters field mode automatically
3. Sensor readings begin within 2 minutes; data written to onboard storage

### During the Hike
- No action needed — device reads and logs every 2 minutes
- Display shows current temp, humidity, pressure trend, and UV index; refreshes every 2 minutes

### Ending the Hike
1. Turn switch **OFF**
2. Device enters deep sleep; hike data safely stored in onboard storage

### Getting Home — Uploading Data
1. Plug in USB charger — no switch action needed
2. Device auto-wakes and connects to home WiFi
3. Accumulated hike data replays automatically to Google Sheets
4. Log dashboard shows "Hike log replay complete." when upload finishes
5. Unplug USB — device returns to deep sleep

---

## Log Dashboard Messages

| Message | Meaning |
|---|---|
| `Hiking monitor online - ESPHome ..., IP: ...` | Device booted and connected to WiFi |
| `MQTT connected` | MQTT broker connection established |
| `Replaying N hike readings...` | Uploading accumulated field data |
| `Hike log replay complete.` | All field data uploaded to Sheets |
| `Upload mode — USB connected, switch off` | Auto-woke via dock detect; collecting suppressed |
| `Heartbeat - uptime: Xh Ym, RSSI: ...` | Device alive, WiFi connected |
| `MQTT disconnected` | WiFi or broker connection lost |

---

## Google Sheets

Readings are archived in **JCTsh Environmental Data** (Google Sheets).
- **Data tab** — raw readings with UTC timestamps
- **View tab** — MST timestamps for readability

Each row: timestamp, component, temp (°F), humidity (%), pressure (hPa), UV index, battery voltage (V), RSSI (dBm).
