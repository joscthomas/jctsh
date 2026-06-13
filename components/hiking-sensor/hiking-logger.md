# Hiking Monitor — Hike Logger (`hiking_logger.h`)

## Technology Decision

The original design called for LittleFS (Arduino `LittleFS.h`) for onboard flash
logging. During implementation, ESP-IDF's native SPIFFS VFS (`esp_spiffs.h`) was used
instead. This choice is now a JCTsh build standard — see §2.10 of
`JCTsh-Build-Standards.md` for the rationale and guidance for future components.

In brief: SPIFFS is bundled with the ESP-IDF (no external library needed) and is fully
sufficient for this use case — sequential append and read of a single file. LittleFS
offers better wear-leveling and directory support, neither of which applies here.

The component is named `hiking_logger.h` after its function, not after either
filesystem library.

---

## Overview

`hiking_logger.h` is a custom C++ header included by ESPHome that handles all onboard
flash logging. When the hiking monitor has no WiFi connection (field mode), sensor
readings are written to flash storage instead of MQTT. On returning home and
reconnecting, all stored readings are replayed to MQTT with their original timestamps.

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
lambda when WiFi is not connected (field mode). Checks `fprintf()` return value and
logs an error if the write fails (SPIFFS full). No-op if SPIFFS is not mounted.

### `hike_log_has_data()`
Returns `true` if the log file exists and is non-empty. Used to guard the replay block
in `on_connect` — avoids logging "Replaying 0 readings" noise when the log is empty.

### `hike_log_count()`
Counts stored lines without loading any data into RAM. Opens the file, scans
line-by-line using a 512-byte stack buffer, and returns the count. Used to build the
"Replaying N hike readings..." log message before streaming begins.

### `hike_log_replay_stream(callback)`
Streams stored lines one at a time via a `std::function<void(const std::string&)>`
callback. Opens the file, reads one line per iteration into a 512-byte stack buffer,
strips trailing newlines, and calls the callback with each non-empty line. Uses
constant stack space regardless of log size — no RAM limit on replay length.

### `hike_log_clear()`
Truncates `/spiffs/hike_log.jsonl` to zero bytes by opening it in write mode and
immediately closing it. Truncate rather than delete — more durable across power loss.
Called **after** replay completes. If power is cut during replay, the log is intact on
next boot and replays again (producing duplicates, which is preferable to data loss).
Logs "Log file cleared" to serial.

---

## Operating Modes

Field mode and home mode are not explicit states — they are determined at runtime by
checking `id(mqtt_client).is_connected()` in the 2-minute interval lambda:

```
WiFi disconnected → MQTT not connected → hike_log_write() → readings go to flash
WiFi connected   → MQTT connected     → mqtt.publish()   → readings go to MQTT directly
```

The heartbeat interval has the same guard: heartbeats are suppressed in field mode
entirely.

---

## Replay Flow

Replay is triggered automatically in `on_connect` (after the 500ms settle delay and
the online/connected log messages). The replay runs inside a raw lambda — this is the
documented exception to the "no `id(mqtt_client).publish()` in raw lambdas" rule (see
§2.7 of `JCTsh-Build-Standards.md`), because native `mqtt.publish` actions cannot be
called from inside a streaming callback.

1. `hike_log_has_data()` — skip entirely if log is empty
2. `hike_log_count()` — get line count without loading data into RAM
3. Publish "Replaying N hike readings..." to log topic
4. `hike_log_replay_stream(callback)` — for each line: publish to data topic, delay 50ms
5. Publish "Hike log replay complete." to log topic
6. `hike_log_clear()` — truncate the log file

The 50ms inter-publish delay prevents the MQTT broker from being flooded on reconnect.
At 50ms per reading, a 180-reading (6-hour) hike replays in ~9 seconds.

The replayed payloads contain the original NTP-synced timestamps from when they were
logged in the field — not the current time. `rssi_dbm` is `0` in all field-mode
readings (no WiFi at logging time), which distinguishes them from live home-mode
readings in Sheets analysis.

---

## Confirmed Behavior

| Date | Context | Result |
|---|---|---|
| 2026-06-03 | Step 5 testing — 5 readings logged during OTA flash cycles | Replayed correctly on reconnect; all five functions confirmed working |
| 2026-06-12 | Streaming refactor — replaced vector-based `hike_log_get_all()` with `hike_log_count()` + `hike_log_replay_stream()` | Confirmed via flash log: `[I][HikeLog:096]: Log file cleared` at line 96 of new implementation |

Log dashboard output on successful replay:
```
Hiking monitor online — ESPHome 2026.4.5, IP: 192.168.1.161
MQTT connected
Replaying 5 hike readings...
Hike log replay complete.
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| "SPIFFS mount failed" in serial log | Corrupt partition | `format_if_mount_failed: true` should auto-format; if not, erase flash manually via USB |
| Replay shows 0 readings after disconnect | SPIFFS mounted but write failed silently | Check serial for "Write failed — SPIFFS may be full" or "Cannot open log file for writing" |
| Readings replay but timestamps are current time | NTP not synced at logging time | Serial log shows "NTP not synced — skipping reading"; device must have NTP sync before field logging begins |
| Duplicate readings in Sheets after power-cut replay | Power was cut during a previous replay before `hike_log_clear()` ran | Expected behavior — duplicates are preferable to data loss; filter duplicates in Sheets by timestamp if needed |
