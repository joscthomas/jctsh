// sensor_logger.h — Offline flash logging template for JCTsh property sensors
//
// PURPOSE: When a sensor has no WiFi connection, readings are written to
// onboard flash storage instead of MQTT. On reconnect, all stored readings
// are replayed to MQTT with their original timestamps, then the log is cleared.
//
// ADAPTATION: Copy this file to components/<name>/<name>_logger.h and do a
// global find-replace of "sensor_log" → "<name>_log" (e.g. "van_log", "aq_log").
// Update SENSOR_LOG_FILE to "/spiffs/<name>_log.jsonl".
// Include the renamed file in your ESPHome YAML: esphome: includes: - <name>_logger.h
//
// IMPLEMENTATION: Uses ESP-IDF native SPIFFS VFS (esp_spiffs.h) — bundled with
// the ESP-IDF, no external library needed. Single-file sequential append + read
// is sufficient; LittleFS wear-leveling and directory support are not needed here.
// See JCTsh-Build-Standards.md §2.10 for the full technology rationale.
//
// REFERENCE: components/hiking-monitor/hiking_logger.h is the production implementation.

#pragma once
#include <esp_spiffs.h>
#include <functional>
#include <stdio.h>
#include <string>

static const char* SENSOR_LOG_MOUNT = "/spiffs";
static const char* SENSOR_LOG_FILE  = "/spiffs/sensor_log.jsonl";   // ← update name
static bool sensor_log_mounted       = false;

// Mount the flash filesystem. Call once at boot via on_boot priority 600.0.
// Auto-formats the partition on first use or if corrupt.
void sensor_log_begin() {
  esp_vfs_spiffs_conf_t conf = {
    .base_path              = SENSOR_LOG_MOUNT,
    .partition_label        = NULL,
    .max_files              = 5,
    .format_if_mount_failed = true,
  };
  esp_err_t ret = esp_vfs_spiffs_register(&conf);
  if (ret != ESP_OK) {
    ESP_LOGE("OfflineLog", "Mount failed: %s", esp_err_to_name(ret));
    return;
  }
  sensor_log_mounted = true;
  size_t total = 0, used = 0;
  esp_spiffs_info(NULL, &total, &used);
  ESP_LOGI("OfflineLog", "Mounted. Total: %u  Used: %u  Free: %u",
           (unsigned)total, (unsigned)used, (unsigned)(total - used));
}

// Append one JSON payload line. Call when MQTT is not connected.
void sensor_log_write(const std::string& payload) {
  if (!sensor_log_mounted) { ESP_LOGW("OfflineLog", "Not mounted"); return; }
  FILE* f = fopen(SENSOR_LOG_FILE, "a");
  if (!f) { ESP_LOGE("OfflineLog", "Cannot open log file"); return; }
  int r = fprintf(f, "%s\n", payload.c_str());
  fclose(f);
  if (r < 0) ESP_LOGE("OfflineLog", "Write failed — flash may be full");
}

// Return true if the log file is non-empty. Use to guard replay in on_connect.
bool sensor_log_has_data() {
  if (!sensor_log_mounted) return false;
  FILE* f = fopen(SENSOR_LOG_FILE, "r");
  if (!f) return false;
  fseek(f, 0, SEEK_END);
  long size = ftell(f);
  fclose(f);
  return size > 0;
}

// Count stored lines without loading data into RAM.
int sensor_log_count() {
  if (!sensor_log_mounted) return 0;
  FILE* f = fopen(SENSOR_LOG_FILE, "r");
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

// Stream stored lines one at a time via callback. Constant RAM use regardless of log size.
void sensor_log_replay_stream(std::function<void(const std::string&)> callback) {
  if (!sensor_log_mounted) return;
  FILE* f = fopen(SENSOR_LOG_FILE, "r");
  if (!f) return;
  char line[512];
  while (fgets(line, sizeof(line), f)) {
    std::string s(line);
    while (!s.empty() && (s.back() == '\n' || s.back() == '\r')) s.pop_back();
    if (!s.empty()) callback(s);
  }
  fclose(f);
}

// Truncate (not delete) the log file after replay completes.
// Truncate is more durable than delete across unexpected power loss —
// if power is cut mid-replay, the log survives intact for a retry on next boot.
void sensor_log_clear() {
  if (!sensor_log_mounted) return;
  FILE* f = fopen(SENSOR_LOG_FILE, "w");
  if (f) fclose(f);
  ESP_LOGI("OfflineLog", "Log cleared");
}
