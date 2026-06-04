# Hiking Monitor — Hike Logger (`hiking_logger.h`)

## Original Plan vs. Actual Implementation

The original design called for LittleFS (Arduino `LittleFS.h`) for onboard flash
logging. During implementation, ESP-IDF's native SPIFFS VFS (`esp_spiffs.h`) was used
instead. SPIFFS is bundled with the ESP-IDF — no external library needed — and is
fully sufficient for this use case (sequential append and read of a single file).
LittleFS offers better wear-leveling and directory support, neither of which matters
here. The component is named `hiking_logger.h` after its function, not after either
filesystem library.

---

## Overview

`hiking_logger.h` is a custom C++ header included by ESPHome that handles all onboard
flash logging. When the hiking monitor has no WiFi connection (field mode), sensor
readings are written to flash storage instead of MQTT. On returning home and reconnecting,
all stored readings are replayed to MQTT with their original timestamps.

---

## Storage

| Property | Value |
|---|---|
| Filesystem | SPIFFS (ESP-IDF native VFS) |
| Mount point | `/spiffs` |
| Log file | `/spiffs/hike_log.jsonl` |
| Partition label | first SPIFFS partition (default ESPHome ESP32 layout) |
| Partition size | ~1.47 MB |
| Max file size per hike | ~36 KB (180 readings × 2-min interval × 6-hour hike) |
| Available headroom | ~40× — no capacity concern in practice |

Log format is JSON Lines: one complete JSON payload object per line, matching the
standard MQTT data payload defined in `JCTsh-Environmental-Data-Architecture.md`.

---

## API

### `hike_log_begin()`
Called once at boot via `esphome: on_boot: priority: 600.0`. Mounts the SPIFFS
partition. If the partition is unformatted or corrupt, `format_if_mount_failed: true`
formats it automatically. Sets the internal `hike_spiffs_mounted` flag on success.
Logs total/used/free bytes to serial.

### `hike_log_write(payload)`
Appends one JSON line to `/spiffs/hike_log.jsonl`. Called from the 2-minute interval
lambda when WiFi is not connected (field mode). No-op if SPIFFS is not mounted.

### `hike_log_has_data()`
Returns `true` if the log file exists and is openable. Used to guard the replay block
in `on_connect` — avoids logging "Replaying 0 readings" noise when the log is empty.

### `hike_log_get_all()`
Opens the log file, reads all lines, strips trailing newlines, and returns them as a
`std::vector<std::string>`. Called in `on_connect` before replay. Logs the count to
serial. Returns an empty vector if SPIFFS is not mounted or the file doesn't exist.

### `hike_log_clear()`
Deletes `/spiffs/hike_log.jsonl` via `remove()`. Called after all readings have been
published during replay. Logs "Log file cleared" to serial.

---

## Operating Modes

Field mode and home mode are not explicit states — they are determined at runtime by
checking `id(mqtt_client).is_connected()` in the 2-minute interval lambda:

```
WiFi disconnected → MQTT not connected → hike_log_write() → readings go to flash
WiFi connected   → MQTT connected     → mqtt.publish()   → readings go to MQTT directly
```

The heartbeat interval has the same guard: `if (!id(mqtt_client).is_connected()) return;`
— heartbeats are suppressed in field mode entirely.

---

## Replay Flow

Replay is triggered automatically in `on_connect` (after the 500ms settle delay and
the online/connected log messages):

1. `hike_log_has_data()` — skip if log is empty
2. `hike_log_get_all()` — load all lines into memory
3. Publish "Replaying N hike readings..." to log topic
4. For each reading: `mqtt.publish` to data topic, `delay(50ms)` between publishes
5. `hike_log_clear()` — delete the log file
6. Publish "Hike log replay complete." to log topic

The 50ms inter-publish delay prevents the MQTT broker from being flooded on reconnect.
At 50ms per reading, a 180-reading (6-hour) hike replays in ~9 seconds.

The replayed payloads contain the original NTP-synced timestamps from when they were
logged in the field — not the current time. `rssi_dbm` is `0` in all field-mode
readings (no WiFi at logging time), which distinguishes them from live home-mode
readings in Sheets analysis.

---

## Confirmed Behavior (2026-06-03)

During Step 5 testing, 5 readings were logged to SPIFFS during WiFi disconnections
(OTA flash cycles). On reconnect, the log dashboard showed:

```
Hiking monitor online — ESPHome 2026.4.5, IP: 192.168.1.162
MQTT connected
Replaying 5 hike readings...
Hike log replay complete.
```

All five functions confirmed working. Full timestamp accuracy verification (longer
disconnection periods) deferred to Step 12 end-to-end field mode simulation.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| "SPIFFS mount failed" in serial log | Corrupt partition | `format_if_mount_failed: true` should auto-format; if not, erase flash manually |
| Replay shows 0 readings after disconnect | SPIFFS mounted but write failed silently | Check serial for "Cannot open log file for writing" |
| Readings replay but timestamps are current time | NTP not synced at logging time | Serial log shows "NTP not synced — skipping reading"; device must have NTP sync before logging begins |
| Log not cleared after replay | `hike_log_clear()` not called | Only clears if `readings` vector is non-empty — check `hike_log_has_data()` guard |
