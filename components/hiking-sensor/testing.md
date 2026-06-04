# Hiking Monitor — Full End-to-End Test (Step 12)

## Prerequisites

All of the following must be confirmed before running this test:
- Steps 5–11 complete (sensors, display, LittleFS, power system, data pipeline)
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

**Check:** Button press triggers immediate display refresh.

Press the button on GPIO32. The e-ink display should refresh within ~2 seconds (full e-ink cycle).

**Pass criteria:** Display refreshes on button press without waiting for the 2-minute interval.

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

This test confirms LittleFS logging and replay work correctly with original timestamps.

**Steps:**

1. Edit `secrets.yaml` — change `wifi_password` to a wrong value
2. Copy to `C:\esphome\hiking-sensor\` and OTA flash: `esphome run hiking-sensor.yaml`
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

**Pass criteria:** Readings logged before power-off replay after power-on + WiFi reconnect. LittleFS/SPIFFS is non-volatile — data persists across power cycles.

---

## Results

**Completed: 2026-06-04. All tests passed.**

| Test | Result | Notes |
|---|---|---|
| 1 — Sensor validation | PASS | temp_f, humidity_pct, pressure_hpa, uv_index, battery_v, rssi_dbm all present and plausible |
| 2 — Display validation | PASS | All four fields rendering correctly; refreshes every 2 minutes |
| 3 — Button validation | PASS | Button press triggers immediate display refresh |
| 4 — Log dashboard | PASS | Heartbeat, boot, and MQTT connected messages all visible |
| 5 — Heartbeat | PASS | Heartbeat appearing every 5 minutes |
| 6 — Field mode simulation | PASS | Readings replayed with original timestamps; rssi_dbm=0 in replayed rows. Bug found and fixed: SPIFFS remove() not persisting across power cuts caused duplicate replays. Fix: truncate before replay + size-based has_data() check. |
| 7 — Google Sheets validation | PASS | dew_point_f and heat_index_f populated; lat/lon blank; source=hiking-monitor |
| 8 — Battery validation | PASS | battery_v 3.85–4.08V across session; fully charged at start of Step 12 |
| 9 — Power cycle test | PASS | LiPo disconnected and reconnected; device rebooted and MQTT reconnected cleanly |

---

## Step 12 Findings

- **SPIFFS duplicate replay bug (fixed):** `remove()` on SPIFFS does not always persist to flash before a power cut. On next boot, the file reappears and replays again. Fix: `hike_log_clear()` now truncates to 0 bytes (fopen "w") instead of calling `remove()`; `hike_log_has_data()` now checks file size > 0. Replay also clears the log before the loop, not after — so a mid-replay power cut leaves an empty file, not a full one.
- **Loose BAT- wire caused power dropouts:** TP4056 BAT- was not firmly seated on breadboard during testing — caused multiple unintended power cuts and triggered the duplicate replay bug. Reseat all TP4056 wires before perfboard build.
- **Google Sheets View tab:** A "View" tab was added to the Environmental Data spreadsheet. Uses ARRAYFORMULA to mirror Environmental Data with timestamps converted from UTC to MST (UTC-7, fixed offset — no DST in Arizona). The Apps Script writes only to Environmental Data; View is display-only.

---

## Known Behaviors

- **Temperature reads ~10°F high on breadboard** — ESP32 self-heating warms the BME280. Will improve on perfboard when BME280 is positioned away from ESP32.
- **UV index 0.00 indoors** — expected. Point at direct sunlight or sunny window to confirm sensor responds.
- **Pressure trend shows `=>` (steady) on boot** — no history yet. Arrow updates after ~30 minutes of readings.
- **`rssi_dbm = 0` in field-mode rows** — correct. Used to distinguish field-mode readings from live home-mode readings in Sheets analysis.
- **405 response from Apps Script** — Google redirects the POST and the redirect destination returns 405. The row IS appended. Node-RED treats 405 as success. This is expected behavior, not an error.
