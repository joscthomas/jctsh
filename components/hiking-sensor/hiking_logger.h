// hiking_logger.h — Custom SPIFFS logging component for hiking-monitor
// Uses ESP-IDF native SPIFFS VFS (esp_spiffs.h) + POSIX file I/O.
// SPIFFS is a bundled ESP-IDF component — no external library needed.
//
// Responsibilities:
//   hike_log_begin()          — mount SPIFFS VFS on boot
//   hike_log_write()          — append one JSON line during field mode (no WiFi)
//   hike_log_count()          — count stored lines without loading into RAM
//   hike_log_replay_stream()  — stream stored lines one at a time via callback
//   hike_log_clear()          — truncate log file after successful replay
//   hike_log_has_data()       — check whether any stored data exists
//
// Log file: /spiffs/hike_log.jsonl (JSON Lines — one JSON object per line)
// Partition: "spiffs" label — 1.47MB in ESPHome default ESP32 partition table
// Replay is streaming — no RAM limit regardless of log size.

#pragma once
#include <esp_spiffs.h>
#include <functional>
#include <stdio.h>
#include <string>

static const char* HIKE_MOUNT    = "/spiffs";
static const char* HIKE_LOG_FILE = "/spiffs/hike_log.jsonl";
static bool hike_spiffs_mounted  = false;

void hike_log_begin() {
  esp_vfs_spiffs_conf_t conf = {
    .base_path              = HIKE_MOUNT,
    .partition_label        = NULL,  // NULL = first spiffs partition found
    .max_files              = 5,
    .format_if_mount_failed = true,
  };
  esp_err_t ret = esp_vfs_spiffs_register(&conf);
  if (ret != ESP_OK) {
    ESP_LOGE("HikeLog", "SPIFFS mount failed: %s", esp_err_to_name(ret));
    return;
  }
  hike_spiffs_mounted = true;
  size_t total = 0, used = 0;
  esp_spiffs_info(NULL, &total, &used);
  ESP_LOGI("HikeLog", "SPIFFS mounted. Total: %u bytes. Used: %u bytes. Free: %u bytes.",
           (unsigned)total, (unsigned)used, (unsigned)(total - used));
}

void hike_log_write(const std::string& payload) {
  if (!hike_spiffs_mounted) {
    ESP_LOGW("HikeLog", "SPIFFS not mounted — skipping write");
    return;
  }
  FILE* f = fopen(HIKE_LOG_FILE, "a");
  if (!f) {
    ESP_LOGE("HikeLog", "Cannot open log file for writing");
    return;
  }
  int result = fprintf(f, "%s\n", payload.c_str());
  fclose(f);
  if (result < 0) {
    ESP_LOGE("HikeLog", "Write failed — SPIFFS may be full");
  }
}

int hike_log_count() {
  if (!hike_spiffs_mounted) return 0;
  FILE* f = fopen(HIKE_LOG_FILE, "r");
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

void hike_log_replay_stream(std::function<void(const std::string&)> callback) {
  if (!hike_spiffs_mounted) return;
  FILE* f = fopen(HIKE_LOG_FILE, "r");
  if (!f) return;
  char line[512];
  while (fgets(line, sizeof(line), f)) {
    std::string s(line);
    while (!s.empty() && (s.back() == '\n' || s.back() == '\r')) s.pop_back();
    if (!s.empty()) callback(s);
  }
  fclose(f);
}

void hike_log_clear() {
  if (!hike_spiffs_mounted) return;
  // Truncate rather than remove — more durable across power loss.
  FILE* f = fopen(HIKE_LOG_FILE, "w");
  if (f) fclose(f);
  ESP_LOGI("HikeLog", "Log file cleared");
}

bool hike_log_has_data() {
  if (!hike_spiffs_mounted) return false;
  FILE* f = fopen(HIKE_LOG_FILE, "r");
  if (!f) return false;
  fseek(f, 0, SEEK_END);
  long size = ftell(f);
  fclose(f);
  return size > 0;
}
