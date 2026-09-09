// aqm_logger.h — Onboard flash logging component for air-quality-monitor
// Adapted from components/hiking-monitor/hiking_logger.h (Step 8, CARD-0012) — same
// SPIFFS-backed append/replay mechanism, renamed prefix so both devices' logic can be
// read side by side without confusing which log file/functions belong to which device.
// See hiking_logger.h's own header comment for the full design rationale (SPIFFS over
// LittleFS, streaming replay with no RAM limit).
//
// Responsibilities:
//   aqm_log_begin()          — mount SPIFFS VFS on boot
//   aqm_log_write()          — append one JSON line when not connected (field mode)
//   aqm_log_count()          — count stored lines without loading into RAM
//   aqm_log_replay_stream()  — stream stored lines one at a time via callback
//   aqm_log_clear()          — truncate log file after successful replay
//   aqm_log_has_data()       — check whether any stored data exists
//
// Log file: /spiffs/aqm_log.jsonl (JSON Lines — one JSON object per line)
// Partition: "spiffs" label — 1.47MB in ESPHome default ESP32 partition table
// Replay is streaming — no RAM limit regardless of log size.

#pragma once
#include <esp_spiffs.h>
#include <functional>
#include <stdio.h>
#include <string>

static const char* AQM_MOUNT    = "/spiffs";
static const char* AQM_LOG_FILE = "/spiffs/aqm_log.jsonl";
static bool aqm_spiffs_mounted  = false;

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

void aqm_log_replay_stream(std::function<void(const std::string&)> callback) {
  if (!aqm_spiffs_mounted) return;
  FILE* f = fopen(AQM_LOG_FILE, "r");
  if (!f) return;
  char line[512];
  while (fgets(line, sizeof(line), f)) {
    std::string s(line);
    while (!s.empty() && (s.back() == '\n' || s.back() == '\r')) s.pop_back();
    if (!s.empty()) callback(s);
  }
  fclose(f);
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
