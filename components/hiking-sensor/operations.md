# Hiking Monitor — Operations Guide

## Hardware Overview

| Component | Role |
|---|---|
| ESP32 + sensors | Reads temperature, humidity, pressure, UV index every 2 minutes |
| LiPo battery + TP4056+boost | Power system — boost converter outputs 5.7V directly to ESP32 VIN |
| Slide switch (GPIO27 signal) | Signals hiking mode — switch ON pulls GPIO27 LOW; not in power path |
| Dock detect (GPIO32 divider) | Detects USB charger connected; wakes ESP32 from deep sleep for upload |

---

## Powering On (Perfboard)

### Connectors to check before connecting LiPo
- **TP4056 harness** — 4-pin female Dupont; yellow dot on housing aligns with yellow dot on perfboard header (pin 1 = IN+, green wire)
- **E-ink display harness** — 8-pin; yellow dot on header pin 1 has grey VCC wire seated in it

### Power-on sequence
1. Confirm ESP32, BME280, and LTR-390 are seated in their headers
2. Confirm both harnesses are connected with pin 1 yellow dots aligned
3. Set switch to desired position — **ON** (yellow dot) for immediate use, **OFF** for sleep
4. Connect LiPo JST to TP4056

### Expected on boot
- ESP32 power LED lights immediately
- LTR-390 power LED lights (confirms 3.3V rail)
- E-ink display refreshes within ~30 seconds showing sensor readings
- Log dashboard shows `Hiking monitor online` and `MQTT connected` within ~30 seconds

### To power off
The switch is not in the power path — the device never fully powers down. Turn switch OFF to enter deep sleep (~10μA drain). Disconnect LiPo only for storage or transport.

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

## Charging

Plug in USB — the device auto-wakes in upload mode and the TP4056 charges the LiPo simultaneously. Red LED on = charging; green LED on = charge complete.

**Expected charge time: ~1.5–2 hours** for the 1100mAh cell. This is longer than a bare TP4056 charge because the ESP32 is awake while USB is connected (dock detect GPIO32 is a level-triggered wake source — the device re-wakes immediately if USB is still connected). The boost converter draws ~150–250mA from the battery to run the ESP32, reducing effective charge current. The TP4056 still terminates normally once the battery reaches 4.2V; it just takes longer.

There is no way to charge with the ESP32 sleeping — USB connected always means the device is awake.

**This module's red LED may stay on even after the battery is full.** Do not rely solely on the LED to confirm charge completion — verify with battery voltage (see below).

### Checking battery voltage

With the switch ON (home mode or field mode), `battery_v` is published in every data reading:

- **Google Sheets** — open *JCTsh Environmental Data* → Environmental Data tab; most recent row shows `battery_v`
- **Log dashboard** — battery voltage does not appear in log messages; use Sheets instead

| Voltage | Meaning |
|---|---|
| ~4.2V (reads ~4.3V) | Fully charged |
| ~3.7V | Nominal — plenty of capacity |
| ~3.5V | Low — charge soon |
| <3.4V | Critical — charge immediately |

The ADC voltage divider reads ~0.1V high at full charge (4.2V actual reads ~4.3V in MQTT/Sheets) — this is normal.

---

## Standard Workflow

### Before a Hike
- Confirm switch is OFF (device sleeping)
- To charge before leaving: plug in USB → device auto-wakes (upload mode) and charges → red LED → green LED when done → unplug → device returns to sleep

### Starting the Hike
1. Turn switch **ON**
2. Open **GPSLogger** on the Pixel — logging starts automatically on app launch
3. Device wakes — if no home WiFi in range, enters field mode automatically
4. Sensor readings begin within 2 minutes; data written to onboard storage

### During the Hike
- No action needed — device reads and logs every 2 minutes
- Display shows current temp, humidity, pressure trend, and UV index; refreshes every 2 minutes

### Ending the Hike
1. Turn switch **OFF** — device enters deep sleep; hike data safely stored in onboard storage
2. Close **GPSLogger** on the Pixel (or leave it — it stops posting when the app is closed)

### Getting Home — Uploading Data
1. Plug in USB charger — no switch action needed
2. Device auto-wakes and connects to home WiFi
3. Accumulated hike data replays automatically to Google Sheets
4. Log dashboard shows "Hike log replay complete." when upload finishes
5. Unplug USB — device returns to deep sleep

---

## Log Dashboard Messages

| Message | Category | Meaning |
|---|---|---|
| `Hiking monitor online - ESPHome ..., IP: ...` | System | Device booted and connected to WiFi |
| `MQTT connected` | MQTT | MQTT broker connection established |
| `Replaying N hike readings...` | System | Uploading accumulated field data |
| `Hike log replay complete.` | System | All field data uploaded to Sheets |
| `Upload mode — USB connected, switch off` | System | Auto-woke via dock detect; collecting suppressed |
| `Entering deep sleep` | System | Device entering deep sleep (switch off or USB removed) |
| `Heartbeat - uptime: Xh Ym, RSSI: ...` | System | Device alive, WiFi connected |
| `MQTT disconnected` | MQTT | WiFi or broker connection lost |

---

## Google Sheets

Readings are archived in **JCTsh Environmental Data** (Google Sheets).
- **Environmental Data tab** — raw readings with UTC timestamps; one row per sensor reading
- **View tab** — MST timestamps for readability
- **GPS Track tab** — trackpoints posted by GPSLogger every 30 seconds during a hike

Each environmental data row: timestamp, component, lat, lon, temp (°F), humidity (%), pressure (hPa), UV index, battery voltage (V), RSSI (dBm). Lat/lon are populated from GPS Track on upload (Step 20).
