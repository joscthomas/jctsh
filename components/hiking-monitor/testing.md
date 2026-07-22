# Hiking Monitor — Full End-to-End Test (Step 12)

## Prerequisites

All of the following must be confirmed before running this test:
- Steps 5–11 complete (sensors, display, onboard flash, power system, data pipeline)
- Device running from LiPo, connected to JCTnet1 WiFi
- Google Sheets "JCTsh Environmental Data" receiving rows
- Log dashboard at `http://raspberrypi.local/` showing `hiking-monitor` entries

---

## Test Items

### 1 — Sensor Validation

**Check:** All four sensor values updating every 2 minutes in the MQTT data topic.

```
mosquitto_sub -h raspberrypi.local -u hiking-monitor -P <password> -t "jctsh/components/hiking-monitor/data"
```

| Sensor | Expected (Tucson indoors) |
|---|---|
| `temp_f` | 70–115°F (note: ESP32 self-heating on breadboard; will improve on perfboard) |
| `humidity_pct` | 5–60% |
| `pressure_hpa` | 910–940 hPa (Tucson ~750m elevation) |
| `uv_index` | 0.00–1.00 indoors; rises toward window/sunlight |
| `battery_v` | 3.7–4.2V |
| `rssi_dbm` | negative value (e.g. -35 to -70 dBm) |

**Pass criteria:** All six fields present and plausible. No NaN values.

---

### 2 — Display Validation

**Check:** E-ink display shows all four fields in correct layout.

Expected display content:
```
[temp °F]        [humidity %]
P [=>|^|v]       UVI [value]
```

**Pass criteria:** Temp, humidity, pressure trend arrow, and UV index all visible. Display refreshes approximately every 2 minutes.

---

### 3 — Button Validation

**Superseded (2026-06-05):** Button removed. GPIO32 repurposed for dock detect. See test 10.

---

### 4 — Log Dashboard

**Check:** Log messages visible at `http://raspberrypi.local/` under `hiking-monitor`.

Expected entries (most recent first):
- `Heartbeat - uptime: Xh Xm, RSSI: -XXdBm, temp: XX.X°F` — every 5 minutes
- `Hiking monitor online - ESPHome X.X.X, IP: 192.168.1.XXX` — on last boot
- `MQTT connected` — on last boot

**Pass criteria:** All three message types present. Heartbeat collapsing into single row with count.

---

### 5 — Heartbeat

**Check:** Heartbeat appearing every 5 minutes in log dashboard and on heartbeat topic.

```
mosquitto_sub -h raspberrypi.local -u hiking-monitor -P <password> -t "jctsh/components/hiking-monitor/heartbeat"
```

**Pass criteria:** Heartbeat JSON appears within 5 minutes. Contains `uptime`, `rssi`, `temp` fields.

---

### 6 — Field Mode Simulation

This test confirms onboard flash logging and replay work correctly with original timestamps.

**Steps:**

1. Edit `secrets.yaml` — change `wifi_password` to a wrong value
2. Copy to `C:\esphome\hiking-monitor\` and OTA flash: `esphome run hiking-monitor.yaml`
3. Device will disconnect from WiFi (confirm: no new heartbeats in log dashboard)
4. Wait 10+ minutes (5+ readings logged at 2-minute intervals)
5. Restore correct `wifi_password` in `secrets.yaml`, copy and OTA flash again
6. On reconnect, confirm log dashboard shows:
   - `Replaying N hike readings...`
   - `Hike log replay complete.`
7. In Google Sheets, confirm replayed rows have:
   - `timestamp` = original logging time (not current time)
   - `rssi_dbm` = 0 (field-mode indicator)
   - `source` = `hiking-monitor`
   - `dew_point_f` and `heat_index_f` populated (computed by Node-RED on replay)

**Pass criteria:** At least 5 readings replayed. Timestamps match logging time, not replay time. `rssi_dbm = 0` in replayed rows.

---

### 7 — Google Sheets Validation

**Check:** Environmental Data sheet accumulating correct rows.

Open the [JCTsh Environmental Data spreadsheet](https://docs.google.com/spreadsheets/d/1aEgW3NDlu43uUM4Wtx1Hq3LjKm6hz2Lpc82LQZRO8L8/edit).

Confirm for recent rows:

| Column | Expected value |
|---|---|
| `source` | `hiking-monitor` |
| `lat` | (blank / null) |
| `lon` | (blank / null) |
| `temp_f` | plausible (70–115°F) |
| `humidity_pct` | plausible |
| `pressure_hpa` | ~910–940 |
| `dew_point_f` | populated (not blank) |
| `heat_index_f` | populated (not blank) |
| `battery_v` | 3.7–4.2V |
| `rssi_dbm` | negative for live readings; 0 for field-mode readings |

**Pass criteria:** All required columns populated. `dew_point_f` and `heat_index_f` not blank. `lat`/`lon` blank.

---

### 8 — Battery Validation

**Check:** `battery_v` in Sheets shows plausible value.

Already confirmed in Step 8 (3.85V). Re-confirm current value is still in range.

**Pass criteria:** `battery_v` between 3.5V and 4.2V.

---

### 9 — Power Cycle Test

**Check:** Device survives power cycle and resumes normal operation.

1. Log 2–3 readings in field mode (disconnect WiFi using wrong password OTA flash)
2. Disconnect LiPo — device powers off
3. Reconnect LiPo — device powers on
4. Restore WiFi credentials, OTA flash
5. Confirm on reconnect: SPIFFS log survived power cycle and readings replay

**Pass criteria:** Readings logged before power-off replay after power-on + WiFi reconnect. onboard flash/SPIFFS is non-volatile — data persists across power cycles.

---

### 10 — Power Switch and Upload Mode

**Check:** Switch OFF → deep sleep. USB connect (switch OFF) → auto-wake → upload mode, no data collection. USB remove → returns to sleep. Switch ON → wakes into hiking mode.

**Prerequisites:** LiPo charged. No USB connected to TP4056 at test start. Home WiFi in range.

**Part A — Switch OFF enters deep sleep**

1. Turn switch ON → confirm device boots, heartbeats appear in log dashboard every 5 minutes
2. Turn switch OFF → wait 6+ minutes
3. Confirm **no** heartbeats appear after switch-off (device is sleeping)

**Part B — USB auto-wake → upload mode**

4. Plug USB charger into TP4056 micro USB → wait up to 30 seconds
5. Confirm log dashboard shows: `Upload mode — USB connected, switch off`
6. If hike data is stored, confirm: `Replaying N hike readings...` then `Hike log replay complete.`
7. Wait one full 2-minute cycle — confirm **no** new data rows appear in Sheets (switch is OFF; no collection)
8. Confirm heartbeats appear while USB is connected and WiFi active

**Part C — USB remove → returns to sleep**

9. Unplug USB → wait 6+ minutes
10. Confirm **no** heartbeats appear after unplug (device returned to sleep)
11. Plug USB again → device wakes again (confirms it returned to sleep, not just WiFi dropout)
12. Unplug USB

**Part D — Switch ON → hiking mode**

13. Turn switch ON → confirm device wakes and connects to WiFi
14. Wait one full 2-minute cycle — confirm new data row appears in Sheets with `rssi_dbm ≠ 0`
15. Turn switch OFF → device enters deep sleep

**Pass criteria:**
- Switch OFF → no heartbeats within 6 minutes
- USB connect (switch OFF) → `Upload mode` log message; no new Sheets rows
- USB remove → no heartbeats within 6 minutes; re-plug wakes device again
- Switch ON → data rows resume in Sheets

---

### 11 — Field Session Start / End Event Detection

**Check:** Node-RED field session events flow fires correct log messages when rssi_dbm transitions between 0 and non-zero. Works for any sensor; tested here with hiking-monitor.

**Prerequisites:** `hiking-hike-events.flow.json` imported and deployed in Node-RED with broker selected. Test inject nodes visible in Node-RED editor.

**Steps (use inject nodes in Node-RED — run in order):**

1. Click `Test: home reading (rssi=-45)` → no event expected (initialises state)
2. Click `Test: field reading 1 — session start (rssi=0)` → log dashboard should show: `Field session started at 2026-06-07T15:00:00Z`
3. Click `Test: field reading 2 — mid-session (rssi=0)` → no event expected
4. Click `Test: home reading — session end (rssi=-31)` → log dashboard should show: `Field session ended at 2026-06-07T15:02:00Z`

**After test:** Reset function node context in Node-RED: hamburger menu → Context Data → select `hike-events-detect` node → delete `lastRssi_hiking-monitor` and `lastTs_hiking-monitor`.

**Pass criteria:** Session started fires once (on inject 2). No event on inject 3. Session ended fires with timestamp of last field reading (inject 3's ts, not inject 4's).

---

## Results

**Completed: 2026-06-12. All tests passed.**

| Test | Result | Notes |
|---|---|---|
| 1 — Sensor validation | PASS | temp_f, humidity_pct, pressure_hpa, uv_index, battery_v, rssi_dbm all present and plausible |
| 2 — Display validation | PASS | All four fields rendering correctly; refreshes every 2 minutes |
| 3 — Button validation | N/A | Button removed 2026-06-05; GPIO32 repurposed for dock detect (see test 10) |
| 4 — Log dashboard | PASS | Heartbeat, boot, and MQTT connected messages all visible |
| 5 — Heartbeat | PASS | Heartbeat appearing every 5 minutes |
| 6 — Field mode simulation | PASS | Readings replayed with original timestamps; rssi_dbm=0 in replayed rows. Bug found and fixed: SPIFFS remove() not persisting across power cuts caused duplicate replays. Fix: truncate before replay + size-based has_data() check. |
| 7 — Google Sheets validation | PASS | dew_point_f and heat_index_f populated; lat/lon blank; source=hiking-monitor |
| 8 — Battery validation | PASS | battery_v 3.85–4.08V across session; fully charged at start of Step 12 |
| 9 — Power cycle test | PASS | LiPo disconnected and reconnected; device rebooted and MQTT reconnected cleanly |
| 10 — Power switch and upload mode | PASS | Deep sleep working; upload mode auto-wake confirmed; switch ON/OFF controls all modes correctly. Bugs fixed: captive_portal was preventing deep sleep; on_connect sleep path incorrectly looped when USB connected. |
| 11 — Hike start/end event detection | PASS | Field session started/ended events fire correctly on rssi transitions; timestamps from sensor data not upload time. Flow in components/hiking-monitor/hiking-hike-events.flow.json. |

---

## Step 12 Findings

- **SPIFFS duplicate replay bug (fixed):** `remove()` on SPIFFS does not always persist to flash before a power cut. On next boot, the file reappears and replays again. Fix: `hike_log_clear()` now truncates to 0 bytes (fopen "w") instead of calling `remove()`; `hike_log_has_data()` now checks file size > 0. Replay also clears the log before the loop, not after — so a mid-replay power cut leaves an empty file, not a full one.
- **Loose BAT- wire caused power dropouts:** TP4056 BAT- (LiPo black wire) was not firmly seated on breadboard during testing — caused multiple unintended power cuts and triggered the duplicate replay bug. Reseat all TP4056 wires before perfboard build.
- **Google Sheets View tab:** A "View" tab was added to the Environmental Data spreadsheet. Uses ARRAYFORMULA to mirror Environmental Data with timestamps converted from UTC to MST (UTC-7, fixed offset — no DST in Arizona). The Apps Script writes only to Environmental Data; View is display-only.

---

## Known Behaviors

- **Temperature reads ~10°F high on breadboard** — ESP32 self-heating warms the BME280. Will improve on perfboard when BME280 is positioned away from ESP32.
- **UV index 0.00 indoors** — expected. Point at direct sunlight or sunny window to confirm sensor responds.
- **Pressure trend shows `=>` (steady) on boot** — no history yet. Arrow updates after ~30 minutes of readings.
- **`rssi_dbm = 0` in field-mode rows** — correct. Used to distinguish field-mode readings from live home-mode readings in Sheets analysis.
- **405 response from Apps Script** — Google redirects the POST and the redirect destination returns 405. The row IS appended. Node-RED treats 405 as success. This is expected behavior, not an error.
