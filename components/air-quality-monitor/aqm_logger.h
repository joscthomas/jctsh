// aqm_logger.h — Onboard flash logging component for air-quality-monitor
// Adapted from components/hiking-monitor/hiking_logger.h (Step 8, CARD-0012) — same
// SPIFFS-backed append mechanism, renamed prefix so both devices' logic can be
// read side by side without confusing which log file/functions belong to which device.
//
// Responsibilities:
//   aqm_log_begin()            — mount SPIFFS VFS on boot
//   aqm_log_write()            — append one JSON line when not connected (field mode)
//   aqm_log_count()            — count stored lines without loading into RAM
//   aqm_log_build_bulk_body()  — CARD-0377 Phase 2: build the whole log into one
//                                 JSON body for a single bulk HTTP POST (replaces
//                                 the old per-line MQTT streaming replay)
//   aqm_log_clear()            — truncate log file after a confirmed-successful upload
//   aqm_log_has_data()         — check whether any stored data exists
//   aqm_boot_log_write()       — CARD-0377 Phase 3: record one boot event, in a
//                                 SEPARATE file from aqm_log.jsonl -- mixing status
//                                 markers into the readings log was the exact bug
//                                 Phase 2's upload script had to fix live
//                                 (2026-10-01/02), so boot events get their own file
//                                 rather than repeating that mistake.
//   aqm_boot_log_build_array() — build the boot-events file into one JSON array
//                                 (spliced into the upload body alongside "readings")
//   aqm_boot_log_clear()       — truncate boot-events file after a confirmed upload
//   aqm_reset_reason_string()  — CARD-0377 Phase 3 bug found live (2026-10-02):
//                                 the debug: component's reset_reason text_sensor
//                                 only gets its value in dump_config(), which runs
//                                 AFTER every on_boot trigger -- so reading
//                                 id(reset_reason_text).state during on_boot (as
//                                 this file's own brownout-detection LED logic has
//                                 always done) reads an empty string, every boot,
//                                 always falling through to the "not a brownout"
//                                 branch. This calls esp_reset_reason() directly
//                                 instead -- a synchronous ESP-IDF call with no
//                                 component-lifecycle dependency.
//
// Log files: /spiffs/aqm_log.jsonl (readings), /spiffs/aqm_boot_log.jsonl (boot
// events) — both JSON Lines, one JSON object per line.
// Partition: "spiffs" label — 1.47MB in ESPHome default ESP32 partition table

#pragma once
#include <esp_spiffs.h>
#include <esp_system.h>
#include <stdio.h>
#include <string>

static const char* AQM_MOUNT         = "/spiffs";
static const char* AQM_LOG_FILE      = "/spiffs/aqm_log.jsonl";
static const char* AQM_BOOT_LOG_FILE = "/spiffs/aqm_boot_log.jsonl";
static bool aqm_spiffs_mounted  = false;

// Mirrors esp-idf's esp_reset_reason_t ordering (same table the debug:
// component's own get_reset_reason_() uses) -- duplicated here rather than
// reused because that table is private to ESPHome's debug component source,
// not exposed for other code to call.
static const char* const AQM_RESET_REASONS[] = {
    "unknown source", "power-on event", "external pin", "software via esp_restart",
    "exception/panic", "interrupt watchdog", "task watchdog", "other watchdogs",
    "exiting deep sleep mode", "brownout", "SDIO", "USB peripheral", "JTAG",
    "efuse error", "power glitch detected", "CPU lock up",
};

const char* aqm_reset_reason_string() {
  unsigned reason = esp_reset_reason();
  if (reason < sizeof(AQM_RESET_REASONS) / sizeof(AQM_RESET_REASONS[0])) {
    return AQM_RESET_REASONS[reason];
  }
  return "unknown source";
}

bool aqm_reset_was_brownout_or_glitch() {
  return esp_reset_reason() == ESP_RST_BROWNOUT || esp_reset_reason() == ESP_RST_PWR_GLITCH;
}

void aqm_log_begin() {
  esp_vfs_spiffs_conf_t conf = {
    .base_path              = AQM_MOUNT,
    .partition_label        = NULL,  // NULL = first spiffs partition found
    .max_files              = 5,
    .format_if_mount_failed = true,
  };
  esp_err_t ret = esp_vfs_spiffs_register(&conf);
  if (ret != ESP_OK) {
    ESP_LOGE("AqmLog", "SPIFFS mount failed: %s", esp_err_to_name(ret));
    return;
  }
  aqm_spiffs_mounted = true;
  size_t total = 0, used = 0;
  esp_spiffs_info(NULL, &total, &used);
  ESP_LOGI("AqmLog", "SPIFFS mounted. Total: %u bytes. Used: %u bytes. Free: %u bytes.",
           (unsigned)total, (unsigned)used, (unsigned)(total - used));
}

void aqm_log_write(const std::string& payload) {
  if (!aqm_spiffs_mounted) {
    ESP_LOGW("AqmLog", "SPIFFS not mounted — skipping write");
    return;
  }
  FILE* f = fopen(AQM_LOG_FILE, "a");
  if (!f) {
    ESP_LOGE("AqmLog", "Cannot open log file for writing");
    return;
  }
  int result = fprintf(f, "%s\n", payload.c_str());
  fclose(f);
  if (result < 0) {
    ESP_LOGE("AqmLog", "Write failed — SPIFFS may be full");
  }
}

int aqm_log_count() {
  if (!aqm_spiffs_mounted) return 0;
  FILE* f = fopen(AQM_LOG_FILE, "r");
  if (!f) return 0;
  int count = 0;
  char line[512];
  while (fgets(line, sizeof(line), f)) {
    for (int i = 0; line[i]; i++) {
      if (line[i] != '\n' && line[i] != '\r' && line[i] != ' ') { count++; break; }
    }
  }
  fclose(f);
  return count;
}

// Shared by aqm_log_build_bulk_body() and aqm_boot_log_build_array(): read a
// JSON-Lines file and join its lines into one JSON array's inner text (no
// brackets) -- each stored line is already a standalone JSON object, so this
// is just string concatenation with commas, no per-line parsing needed.
static std::string _aqm_file_to_json_array_inner(const char* path) {
  if (!aqm_spiffs_mounted) return "";
  FILE* f = fopen(path, "r");
  if (!f) return "";
  std::string out;
  char line[512];
  bool first = true;
  while (fgets(line, sizeof(line), f)) {
    std::string s(line);
    while (!s.empty() && (s.back() == '\n' || s.back() == '\r')) s.pop_back();
    if (s.empty()) continue;
    if (!first) out += ",";
    out += s;
    first = false;
  }
  fclose(f);
  return out;
}

// CARD-0377 Phase 2: replaces aqm_log_replay_stream() (per-line MQTT publish
// loop, removed along with MQTT entirely) -- builds the ENTIRE buffered log
// into one JSON body for a single HTTP POST to the data-pipeline gateway's
// bulk endpoint.
// CARD-0377 Phase 3: also splices in the boot-events array (built separately
// by the caller via aqm_boot_log_build_array()) so one upload carries both
// the session's readings and the boot events needed for the server-side
// session summary.
std::string aqm_log_build_bulk_body(const std::string& current_time,
                                     const std::string& current_boot,
                                     uint32_t current_uptime_s,
                                     const std::string& boot_events_array) {
  if (!aqm_spiffs_mounted) return "";
  return "{\"current_time\":\"" + current_time +
         "\",\"current_boot\":\"" + current_boot +
         "\",\"current_uptime_s\":" + std::to_string(current_uptime_s) +
         ",\"readings\":[" + _aqm_file_to_json_array_inner(AQM_LOG_FILE) +
         "],\"boot_events\":[" + boot_events_array + "]}";
}

void aqm_log_clear() {
  if (!aqm_spiffs_mounted) return;
  // Truncate rather than remove — more durable across power loss.
  FILE* f = fopen(AQM_LOG_FILE, "w");
  if (f) fclose(f);
  ESP_LOGI("AqmLog", "Log file cleared");
}

bool aqm_log_has_data() {
  if (!aqm_spiffs_mounted) return false;
  FILE* f = fopen(AQM_LOG_FILE, "r");
  if (!f) return false;
  fseek(f, 0, SEEK_END);
  long size = ftell(f);
  fclose(f);
  return size > 0;
}

// CARD-0377 Phase 3: one line per boot, written once at on_boot -- a
// reliable reset count needs a marker that exists independent of whether
// the clock was synced or any reading was ever buffered, which a
// reading-embedded boot id (CARD-0343's ts:null path) can't guarantee.
void aqm_boot_log_write(const std::string& payload) {
  if (!aqm_spiffs_mounted) {
    ESP_LOGW("AqmLog", "SPIFFS not mounted — skipping boot-event write");
    return;
  }
  FILE* f = fopen(AQM_BOOT_LOG_FILE, "a");
  if (!f) {
    ESP_LOGE("AqmLog", "Cannot open boot-event log file for writing");
    return;
  }
  fprintf(f, "%s\n", payload.c_str());
  fclose(f);
}

std::string aqm_boot_log_build_array() {
  return _aqm_file_to_json_array_inner(AQM_BOOT_LOG_FILE);
}

// CARD-0377 Phase 3 bug found live (2026-10-02, two OTA-dev-reboot test
// cycles): without this, a boot event with NO accompanying readings (any
// reboot between real sessions -- an OTA flash being the obvious case) just
// sits in the boot-events file until the NEXT session that actually has
// readings to upload, silently inflating that unrelated future session's
// reset count. Checked alongside aqm_log_has_data() in the upload script's
// eligibility/early-exit so a stray boot event gets flushed on its own
// promptly instead of waiting to piggyback on real data.
bool aqm_boot_log_has_data() {
  if (!aqm_spiffs_mounted) return false;
  FILE* f = fopen(AQM_BOOT_LOG_FILE, "r");
  if (!f) return false;
  fseek(f, 0, SEEK_END);
  long size = ftell(f);
  fclose(f);
  return size > 0;
}

void aqm_boot_log_clear() {
  if (!aqm_spiffs_mounted) return;
  FILE* f = fopen(AQM_BOOT_LOG_FILE, "w");
  if (f) fclose(f);
}
