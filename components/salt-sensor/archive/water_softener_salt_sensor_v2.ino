/*
 * Water Softener Salt Level Sensor  v2
 * Board:   ESP32 Dev Module
 * Sensor:  JSN-SR04T Waterproof Ultrasonic
 *
 * Wiring:
 *   JSN-SR04T Trig  → GPIO 5
 *   JSN-SR04T Echo  → 1kΩ → GPIO 18 → 2kΩ → GND
 *   Red LED    → GPIO 2  via 220Ω   (Critical  < 15%)
 *   Yellow LED → GPIO 15 via 220Ω   (Warning  15–33%)
 *   Green LED  → GPIO 4  via 220Ω   (Good      > 33%)
 *
 * Web Monitor:
 *   Open a browser on any device on the same WiFi network and go to:
 *   http://salt-sensor.local        <- always works (mDNS, no IP needed)
 *   http://192.168.1.178            <- direct IP (may change on reboot)
 *   The page auto-refreshes every 5 seconds and shows the last 100 log lines.
 *
 * Reset Switch behavior:
 *   Only polled every 5 minutes when a warning or critical alert is active.
 *   When triggered: takes a live sensor reading, turns reset switch OFF, then:
 *     - GREEN range  → clears all alerts, green LED solid
 *     - WARNING range → clears critical, resends warning alert
 *     - CRITICAL range → clears warning, resends critical alert
 *
 * PAT Expiration:
 *   If the SmartThings PAT expires, all three LEDs go solid (not blinking)
 *   and [AUTH ERROR] messages appear every 60s in the web monitor and Serial.
 *   To fix: generate a new PAT at https://account.smartthings.com/tokens,
 *   update the PAT constant below, and flash via OTA.
 */

#include <WiFi.h>
#include <ArduinoOTA.h>
#include <HTTPClient.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include "secrets.h"

// ================== PIN DEFINITIONS ==================
const int trigPin      = 5;
const int echoPin      = 18;
const int redLedPin    = 2;
const int yellowLedPin = 15;
const int greenLedPin  = 4;

// ================== WiFi ==================
const char* ssid     = WIFI_SSID;
const char* password = WIFI_PASSWORD;

// ================== SmartThings ==================
// Manage PAT: https://account.smartthings.com/tokens
const String PAT              = ST_PAT;
const String criticalDeviceID = ST_CRITICAL_DEVICE;
const String warningDeviceID  = ST_WARNING_DEVICE;
const String testModeDeviceID = ST_TESTMODE_DEVICE;
const String fullResetDeviceID= ST_FULLRESET_DEVICE;

// ================== CALIBRATION ==================
const float FULL_DISTANCE_CM  = 20.4;  // measured with full tank
const float EMPTY_DISTANCE_CM = 43.0;  // measured to empty tank floor (17 inches)
const float WARNING_PERCENT   = 33.0;
const float CRITICAL_PERCENT  = 15.0;

// ================== TEST MODE ==================
// Two distances that exercise each alert threshold:
//   Step 1 → WARNING zone  (between critical and warning)
//   Step 2 → CRITICAL zone (below critical)
const float TEST_DISTANCE_WARNING_CM  = 33.0;  // ~24% salt → Yellow
const float TEST_DISTANCE_CRITICAL_CM = 43.0;  // ~0%  salt → Red

// ================== TIMING ==================
const unsigned long NORMAL_INTERVAL      = 43200000UL;  // 12 hours (twice a day)
const unsigned long TEST_INTERVAL        = 1000UL;       // 1 second in test mode
const unsigned long ST_POLL_INTERVAL     = 60000UL;      // Poll test mode switch every 60s
const unsigned long RESET_POLL_INTERVAL  = 300000UL;     // Poll reset switch every 5 min (alerts active only)

// ================== GLOBALS ==================
bool  criticalAlertSent = false;
bool  warningAlertSent  = false;
bool  switchesReset     = false;
bool  patExpired        = false;   // true when a 401 is received from SmartThings

unsigned long lastCheckTime     = 0;
unsigned long lastSTPollTime    = 0;
unsigned long lastResetPollTime = 0;

// Cached SmartThings switch states
bool testModeOn = false;

// Cached last valid percent for LED blinking outside the check interval
float lastPercent = 100.0;

// Test mode cycles between warning and critical distances each call
int testStep = 0;

// ================== WEB LOG BUFFER ==================
// Stores the last 100 log lines for display on the web monitor page.
const int  LOG_MAX_LINES = 100;
String     logBuffer[LOG_MAX_LINES];
int        logHead  = 0;   // index of oldest line (circular buffer)
int        logCount = 0;   // how many lines are stored

// Append a line to the circular log buffer AND print to Serial
void logLine(const String& msg) {
  Serial.println(msg);
  logBuffer[logHead] = msg;
  logHead = (logHead + 1) % LOG_MAX_LINES;
  if (logCount < LOG_MAX_LINES) logCount++;
}

// ================== WEB SERVER ==================
WebServer webServer(80);

void handleWebRoot() {
  // Build the log output in order (oldest -> newest)
  String logHtml = "";
  int start = (logCount < LOG_MAX_LINES) ? 0 : logHead;
  for (int i = 0; i < logCount; i++) {
    String line = logBuffer[(start + i) % LOG_MAX_LINES];
    // Colour-code lines by priority
    if      (line.indexOf("AUTH ERROR") >= 0) logHtml += "<span style='color:#ff00ff;font-weight:bold'>" + line + "</span>\n";
    else if (line.indexOf("CRITICAL")   >= 0) logHtml += "<span style='color:#ff4444'>" + line + "</span>\n";
    else if (line.indexOf("WARNING")    >= 0) logHtml += "<span style='color:#ffaa00'>" + line + "</span>\n";
    else if (line.indexOf("TEST MODE")  >= 0) logHtml += "<span style='color:#00ccff'>" + line + "</span>\n";
    else if (line.indexOf("[Reset]")    >= 0) logHtml += "<span style='color:#00ff99'>" + line + "</span>\n";
    else if (line.indexOf("[Boot]")     >= 0) logHtml += "<span style='color:#aaaaaa'>" + line + "</span>\n";
    else                                      logHtml += line + "\n";
  }

  // Banner at top of page when PAT is expired
  String authBanner = "";
  if (patExpired) {
    authBanner = "<div style='background:#ff00ff;color:#000;padding:10px;border-radius:6px;"
                 "font-weight:bold;margin-bottom:10px;'>&#9888; SmartThings PAT EXPIRED - "
                 "Generate a new token at https://account.smartthings.com/tokens and flash via OTA</div>";
  }

  String html =
    "<!DOCTYPE html><html><head>"
    "<meta charset='UTF-8'>"
    "<meta http-equiv='refresh' content='5'>"
    "<title>Salt Sensor Monitor</title>"
    "<style>"
    "  body { background:#1a1a1a; color:#e0e0e0; font-family:monospace; font-size:13px; margin:20px; }"
    "  h2   { color:#00cc66; }"
    "  pre  { background:#111; padding:12px; border-radius:6px; overflow-x:auto; }"
    "  .label { color:#888; font-size:11px; }"
    "</style>"
    "</head><body>"
    "<h2>&#127538; Salt Sensor Monitor</h2>"
    "<p class='label'>Auto-refreshes every 5 seconds &nbsp;|&nbsp; "
    "IP: " + WiFi.localIP().toString() + " &nbsp;|&nbsp; "
    "Uptime: " + String(millis() / 60000) + " min</p>" +
    authBanner +
    "<pre>" + logHtml + "</pre>"
    "</body></html>";

  webServer.send(200, "text/html", html);
}

// ─────────────────────────────────────────────────────────────────────
// Called whenever a 401 is detected. Sets the patExpired flag,
// logs a visible error, and lights all three LEDs solid.
void handleAuthError(const String& context) {
  if (!patExpired) {
    // First time - log prominently
    logLine("╔══════════════════════════════════════════════════════╗");
    logLine("║  [AUTH ERROR] SmartThings PAT has EXPIRED            ║");
    logLine("║  SmartThings integration is OFFLINE                  ║");
    logLine("║  1. Go to https://account.smartthings.com/tokens     ║");
    logLine("║  2. Generate a new PAT                               ║");
    logLine("║  3. Update PAT in sketch and flash via OTA           ║");
    logLine("╚══════════════════════════════════════════════════════╝");
    patExpired = true;
  } else {
    // Subsequent - shorter reminder every poll cycle
    logLine("[AUTH ERROR] PAT expired - ST offline. Context: " + context);
  }
  // All three LEDs solid (not blinking) as visual indicator
  digitalWrite(redLedPin,    HIGH);
  digitalWrite(yellowLedPin, HIGH);
  digitalWrite(greenLedPin,  HIGH);
}

// ─────────────────────────────────────────────────────────────────────
// Returns true if switch is ON, false if OFF or error.
// Sets patExpired flag on 401.
bool isSwitchOn(const String& devID) {
  if (WiFi.status() != WL_CONNECTED) return false;
  HTTPClient http;
  String url = "https://api.smartthings.com/v1/devices/" + devID + "/status";
  http.begin(url);
  http.addHeader("Authorization", "Bearer " + PAT);
  int code = http.GET();
  bool state = false;
  if (code == 200) {
    String body = http.getString();
    state = (body.indexOf("\"value\":\"on\"") > 0);
  } else if (code == 401) {
    handleAuthError("isSwitchOn devID=" + devID.substring(devID.length() - 8));
  } else if (code > 0) {
    logLine("[SmartThings] GET failed, HTTP " + String(code));
  }
  http.end();
  return state;
}

// Sends an on/off command to a SmartThings device.
// Sets patExpired flag on 401.
void sendCommand(const String& devID, bool on) {
  if (WiFi.status() != WL_CONNECTED) {
    logLine("[WiFi] Not connected - skipping SmartThings command.");
    return;
  }
  HTTPClient http;
  String url = "https://api.smartthings.com/v1/devices/" + devID + "/commands";
  http.begin(url);
  http.addHeader("Authorization", "Bearer " + PAT);
  http.addHeader("Content-Type", "application/json");
  String payload = on
    ? "{\"commands\":[{\"component\":\"main\",\"capability\":\"switch\",\"command\":\"on\"}]}"
    : "{\"commands\":[{\"component\":\"main\",\"capability\":\"switch\",\"command\":\"off\"}]}";
  int code = http.POST(payload);
  if (code == 401) {
    handleAuthError("sendCommand devID=" + devID.substring(devID.length() - 8));
  } else if (code != 200 && code != 202) {
    logLine("[SmartThings] Command failed, HTTP " + String(code));
  }
  http.end();
}

// ─────────────────────────────────────────────────────────────────────
void checkWiFi() {
  if (WiFi.status() != WL_CONNECTED) {
    logLine("[WiFi] Connection lost - reconnecting...");
    WiFi.reconnect();
    unsigned long start = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - start < 10000UL) {
      delay(500);
      Serial.print(".");
    }
    if (WiFi.status() == WL_CONNECTED) {
      logLine("[WiFi] Reconnected.");
    } else {
      logLine("[WiFi] Reconnect failed - will retry next cycle.");
    }
  }
}

// ─────────────────────────────────────────────────────────────────────
float getFilteredDistance() {
  float readings[15];
  int count = 0;
  for (int i = 0; i < 15; i++) {
    digitalWrite(trigPin, LOW);  delayMicroseconds(2);
    digitalWrite(trigPin, HIGH); delayMicroseconds(10);
    digitalWrite(trigPin, LOW);
    long duration = pulseIn(echoPin, HIGH, 40000);
    float d = duration * 0.0343 / 2.0;
    if (d > 2 && d < 200) readings[count++] = d;
    delay(50);
  }
  if (count == 0) return -1;
  // Insertion sort -> median
  for (int i = 1; i < count; i++) {
    float key = readings[i];
    int j = i - 1;
    while (j >= 0 && readings[j] > key) { readings[j+1] = readings[j]; j--; }
    readings[j+1] = key;
  }
  return readings[count / 2];
}

float calculatePercent(float dist) {
  dist = constrain(dist, FULL_DISTANCE_CM, EMPTY_DISTANCE_CM);
  return 100.0 * (EMPTY_DISTANCE_CM - dist) / (EMPTY_DISTANCE_CM - FULL_DISTANCE_CM);
}

// ─────────────────────────────────────────────────────────────────────
// Called every loop so warning/critical LEDs actually blink.
// When PAT is expired, all three LEDs are held solid by handleAuthError()
// and this function is bypassed.
void updateLEDs(float percent, bool blinkState) {
  if (patExpired) return;   // LEDs held solid by handleAuthError()

  // Green: solid when good
  digitalWrite(greenLedPin, (percent > WARNING_PERCENT) ? HIGH : LOW);

  if (percent < CRITICAL_PERCENT) {
    digitalWrite(redLedPin,    blinkState ? HIGH : LOW);
    digitalWrite(yellowLedPin, LOW);
  } else if (percent <= WARNING_PERCENT) {
    digitalWrite(yellowLedPin, blinkState ? HIGH : LOW);
    digitalWrite(redLedPin,    LOW);
  } else {
    digitalWrite(redLedPin,    LOW);
    digitalWrite(yellowLedPin, LOW);
  }
}

// ─────────────────────────────────────────────────────────────────────
// Returns the simulated distance for this test step, then advances.
float getTestDistance() {
  float dist;
  if (testStep == 0) {
    dist = TEST_DISTANCE_WARNING_CM;
    logLine("╔══════════════════════════════════════╗");
    logLine("║  TEST MODE - Step 1/2: WARNING zone  ║");
    logLine("║  Simulated distance: " + String(dist, 1) + " cm          ║");
    logLine("╚══════════════════════════════════════╝");
  } else {
    dist = TEST_DISTANCE_CRITICAL_CM;
    logLine("╔══════════════════════════════════════╗");
    logLine("║  TEST MODE - Step 2/2: CRITICAL zone ║");
    logLine("║  Simulated distance: " + String(dist, 1) + " cm         ║");
    logLine("╚══════════════════════════════════════╝");
  }
  testStep = (testStep + 1) % 2;   // toggle 0 -> 1 -> 0 -> ...
  return dist;
}

// ─────────────────────────────────────────────────────────────────────
// Handle the reset switch: always takes a LIVE sensor reading.
// Always turns the reset switch OFF regardless of outcome.
// Clears/resends alerts based on what the sensor actually reads.
void handleResetSwitch() {
  logLine("[Reset] Reset switch detected ON - taking live sensor reading...");

  // Always turn the reset switch OFF immediately
  sendCommand(fullResetDeviceID, false);

  float dist = getFilteredDistance();
  if (dist < 0) {
    logLine("[Reset] ERROR - no valid sensor reading. Alerts unchanged.");
    return;
  }

  float percent = calculatePercent(dist);
  lastPercent = percent;
  logLine("[Reset] Live reading: " + String(dist, 1) + " cm  ->  " + String((int)percent) + "% salt");

  if (percent > WARNING_PERCENT) {
    // ── GREEN: tank is full, clear everything ──────────────────────
    criticalAlertSent = false;
    warningAlertSent  = false;
    sendCommand(criticalDeviceID, false);
    sendCommand(warningDeviceID,  false);
    logLine("[Reset] SUCCESS - tank is full. All alerts cleared. Green LED on.");

  } else if (percent >= CRITICAL_PERCENT) {
    // ── WARNING range: clear critical, resend warning ──────────────
    if (criticalAlertSent) {
      sendCommand(criticalDeviceID, false);
      criticalAlertSent = false;
    }
    if (!warningAlertSent) {
      sendCommand(warningDeviceID, true);
      warningAlertSent = true;
    }
    logLine("[Reset] Tank still LOW - critical cleared, warning alert resent.");

  } else {
    // ── CRITICAL range: clear warning, resend critical ─────────────
    if (warningAlertSent) {
      sendCommand(warningDeviceID, false);
      warningAlertSent = false;
    }
    if (!criticalAlertSent) {
      sendCommand(criticalDeviceID, true);
      criticalAlertSent = true;
    }
    logLine("[Reset] Tank CRITICALLY LOW - warning cleared, critical alert resent.");
  }
}

// ─────────────────────────────────────────────────────────────────────
void doMeasurementCycle() {
  // Skip SmartThings calls if PAT is expired - sensor and LEDs still work
  if (patExpired) {
    float dist = getFilteredDistance();
    if (dist > 0) {
      lastPercent = calculatePercent(dist);
      logLine("[Sensor] Distance: " + String(dist, 1) + " cm  ->  Salt level: " +
              String((int)lastPercent) + "%  [ST OFFLINE - PAT expired]");
    }
    return;
  }

  float dist = testModeOn ? getTestDistance() : getFilteredDistance();

  if (dist < 0) {
    logLine("[ERROR] No valid sensor reading - check wiring.");
    // Blink all three LEDs to signal hardware fault
    for (int i = 0; i < 6; i++) {
      digitalWrite(redLedPin,    HIGH);
      digitalWrite(yellowLedPin, HIGH);
      digitalWrite(greenLedPin,  HIGH);
      delay(150);
      digitalWrite(redLedPin,    LOW);
      digitalWrite(yellowLedPin, LOW);
      digitalWrite(greenLedPin,  LOW);
      delay(150);
    }
    return;
  }

  float percent = calculatePercent(dist);
  lastPercent = percent;

  String msg = "[Sensor] Distance: " + String(dist, 1) + " cm  ->  Salt level: " + String((int)percent) + "%";
  if (testModeOn) msg += "  [TEST MODE]";
  logLine(msg);

  // ── SmartThings alert logic ──────────────────────────────────────
  if (percent < CRITICAL_PERCENT) {
    if (!criticalAlertSent) {
      sendCommand(criticalDeviceID, true);
      criticalAlertSent = true;
      logLine("[Alert] >>> CRITICAL - salt very low. Notification sent.");
      if (testModeOn) {
        logLine("[Test]  Pausing 5s - check ST app for Critical alert...");
        delay(5000);
      }
    }
    // Ensure warning is cleared if we've dropped into critical
    if (warningAlertSent) {
      sendCommand(warningDeviceID, false);
      warningAlertSent = false;
    }
  } else if (criticalAlertSent) {
    sendCommand(criticalDeviceID, false);
    criticalAlertSent = false;
    logLine("[Alert] Critical cleared.");
  }

  if (percent >= CRITICAL_PERCENT && percent <= WARNING_PERCENT) {
    if (!warningAlertSent) {
      sendCommand(warningDeviceID, true);
      warningAlertSent = true;
      logLine("[Alert] >>> WARNING - salt getting low. Notification sent.");
      if (testModeOn) {
        logLine("[Test]  Pausing 5s - check ST app for Warning alert...");
        delay(5000);
      }
    }
  } else if (warningAlertSent && percent > WARNING_PERCENT) {
    sendCommand(warningDeviceID, false);
    warningAlertSent = false;
    logLine("[Alert] Warning cleared.");
  }
}

// ─────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(2000);
  Serial.println("\n\n=== Water Softener Salt Sensor v2 ===");

  pinMode(trigPin,      OUTPUT);
  pinMode(echoPin,      INPUT);
  pinMode(redLedPin,    OUTPUT);
  pinMode(yellowLedPin, OUTPUT);
  pinMode(greenLedPin,  OUTPUT);

  // LED startup sequence
  Serial.println("[Boot] LED self-test...");
  digitalWrite(redLedPin,    HIGH); delay(600);
  digitalWrite(yellowLedPin, HIGH); delay(600);
  digitalWrite(greenLedPin,  HIGH); delay(600);
  for (int i = 0; i < 4; i++) {
    digitalWrite(redLedPin, LOW); digitalWrite(yellowLedPin, LOW); digitalWrite(greenLedPin, LOW);
    delay(300);
    digitalWrite(redLedPin, HIGH); digitalWrite(yellowLedPin, HIGH); digitalWrite(greenLedPin, HIGH);
    delay(300);
  }
  digitalWrite(redLedPin, LOW); digitalWrite(yellowLedPin, LOW); digitalWrite(greenLedPin, LOW);
  Serial.println("[Boot] LED test complete.");

  // OTA verification: 3 rapid triple-flashes on each reboot
  for (int i = 0; i < 3; i++) {
    digitalWrite(redLedPin, HIGH); digitalWrite(yellowLedPin, HIGH); digitalWrite(greenLedPin, HIGH);
    delay(100);
    digitalWrite(redLedPin, LOW); digitalWrite(yellowLedPin, LOW); digitalWrite(greenLedPin, LOW);
    delay(100);
  }

  // WiFi
  Serial.printf("[WiFi] Connecting to %s...\n", ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println("\n[WiFi] Connected.  IP: " + WiFi.localIP().toString());

  // mDNS - allows http://salt-sensor.local on any device on the same network
  if (MDNS.begin("salt-sensor")) {
    Serial.println("[mDNS] Responder started  ->  http://salt-sensor.local");
  } else {
    Serial.println("[mDNS] Failed to start");
  }

  // Web monitor server
  webServer.on("/", handleWebRoot);
  webServer.begin();
  Serial.println("[Web]  Monitor started     ->  http://salt-sensor.local");

  // OTA
  ArduinoOTA.setHostname("salt-sensor");
  ArduinoOTA.setPassword(OTA_PASSWORD);
  ArduinoOTA.begin();
  Serial.println("[OTA]  Ready.");

  // Reset alert and fullReset switches on boot (NOT test mode - that is user-controlled)
  sendCommand(warningDeviceID,   false);
  sendCommand(criticalDeviceID,  false);
  sendCommand(fullResetDeviceID, false);
  switchesReset = true;
  logLine("[Boot] SmartThings alert switches reset.");

  // Wait for SmartThings to settle before reading switch states
  logLine("[Boot] Waiting for SmartThings to settle...");
  delay(3000);

  // Initial poll of switch states
  testModeOn = isSwitchOn(testModeDeviceID);
  lastSTPollTime    = millis();
  lastResetPollTime = millis();

  logLine(testModeOn
    ? "[Boot] Test mode switch: ON  <- running at 1s intervals with simulated distances"
    : "[Boot] Test mode switch: OFF <- running at 12-hour intervals with live sensor");
  logLine("[Boot] Salt Sensor ready.");
}

// ─────────────────────────────────────────────────────────────────────
void loop() {
  ArduinoOTA.handle();
  webServer.handleClient();
  checkWiFi();

  // ── Blink state (500 ms toggle, runs every loop) ──────────────────
  static bool blinkState = false;
  static unsigned long lastBlink = 0;
  if (millis() - lastBlink >= 500) {
    blinkState = !blinkState;
    lastBlink  = millis();
  }

  // Always update LEDs so blinking is smooth regardless of check interval
  // (bypassed when PAT expired - LEDs held solid)
  updateLEDs(lastPercent, blinkState);

  // ── Skip SmartThings polling if PAT is expired ────────────────────
  if (!patExpired) {

    // ── Poll test mode switch every 60 s ───────────────────────────
    if (millis() - lastSTPollTime >= ST_POLL_INTERVAL) {
      testModeOn = isSwitchOn(testModeDeviceID);
      lastSTPollTime = millis();
      if (testModeOn) {
        logLine("[SmartThings] Test mode is ON.");
      }
    }

    // ── Poll reset switch every 5 min, ONLY when an alert is active ─
    bool alertActive = criticalAlertSent || warningAlertSent;
    if (alertActive && millis() - lastResetPollTime >= RESET_POLL_INTERVAL) {
      lastResetPollTime = millis();
      if (isSwitchOn(fullResetDeviceID)) {
        handleResetSwitch();
      }
    }
    // Keep timer fresh when no alert is active
    if (!alertActive) {
      lastResetPollTime = millis();
    }

  } else {
    // ── PAT expired: log reminder every 60 s ───────────────────────
    if (millis() - lastSTPollTime >= ST_POLL_INTERVAL) {
      lastSTPollTime = millis();
      logLine("[AUTH ERROR] PAT expired - ST offline. Flash new PAT via OTA to restore.");
    }
  }

  // ── Measurement cycle (runs regardless of PAT state) ─────────────
  unsigned long interval = testModeOn ? TEST_INTERVAL : NORMAL_INTERVAL;

  if (lastCheckTime == 0 || millis() - lastCheckTime >= interval) {
    doMeasurementCycle();
    lastCheckTime = millis();
  }

  delay(100);   // short yield; keeps blink, web server & OTA responsive
}
