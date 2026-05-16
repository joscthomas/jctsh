/*
 * Water Softener Salt Level Sensor  v3
 * Board:   ESP32 Dev Module
 * Sensor:  JSN-SR04T Waterproof Ultrasonic
 *
 * Wiring:
 *   JSN-SR04T Trig  → GPIO 5
 *   JSN-SR04T Echo  → 1kΩ → GPIO 18 → 2kΩ → GND
 *   Red LED    → GPIO 2  via 220Ω   (Critical)
 *   Yellow LED → GPIO 15 via 220Ω   (Warning)
 *   Green LED  → GPIO 4  via 220Ω   (Good)
 *
 * Architecture:
 *   ESP32 publishes sensor readings to MQTT every 12 hours.
 *   Node-RED applies threshold logic and controls SmartThings
 *   via Home Assistant. Node-RED publishes a status string back
 *   to the ESP32 which drives the LEDs.
 *
 * MQTT Topics:
 *   Publish:   jctsh/sensors/salt-sensor/data   {"distance_cm":25.3,"percent":78}
 *   Publish:   jctsh/sensors/salt-sensor/log    {"component":"salt-sensor","category":"...","message":"..."}
 *   Subscribe: jctsh/sensors/salt-sensor/status "ok" | "warning" | "critical" | "error"
 *
 * OTA:
 *   Host: salt-sensor   Password: see secrets.h
 *   Three rapid LED flashes confirm successful reboot.
 */

#include <WiFi.h>
#include <ArduinoOTA.h>
#include <PubSubClient.h>
#include "secrets.h"

// ================== PIN DEFINITIONS ==================
const int trigPin      = 5;
const int echoPin      = 18;
const int redLedPin    = 2;
const int yellowLedPin = 15;
const int greenLedPin  = 4;

// ================== CALIBRATION ==================
const float FULL_DISTANCE_CM  = 20.4;
const float EMPTY_DISTANCE_CM = 43.0;

// ================== TIMING ==================
const unsigned long READING_INTERVAL    = 43200000UL;  // 12 hours
const unsigned long MQTT_RETRY_INTERVAL = 30000UL;     // 30 s between reconnect attempts

// ================== MQTT TOPICS ==================
const char* TOPIC_DATA   = "jctsh/sensors/salt-sensor/data";
const char* TOPIC_STATUS = "jctsh/sensors/salt-sensor/status";
const char* TOPIC_LOG    = "jctsh/sensors/salt-sensor/log";

// ================== GLOBALS ==================
String currentStatus = "unknown";
float  lastDistance  = 0.0;
float  lastPercent   = 0.0;

unsigned long lastReadingTime = 0;
unsigned long lastMqttAttempt = 0;

// ================== MQTT ==================
WiFiClient   wifiClient;
PubSubClient mqtt(wifiClient);

void publishLog(const char* category, const String& message) {
  String payload = "{\"component\":\"salt-sensor\",\"category\":\"";
  payload += category;
  payload += "\",\"message\":\"";
  payload += message;
  payload += "\"}";
  mqtt.publish(TOPIC_LOG, payload.c_str());
  Serial.println(payload);
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String msg = "";
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];

  if (String(topic) == TOPIC_STATUS) {
    if (msg != currentStatus) {
      publishLog("MQTT", "Status: " + currentStatus + " -> " + msg);
    }
    currentStatus = msg;
  }
}

bool mqttConnect() {
  if (WiFi.status() != WL_CONNECTED) return false;
  publishLog("MQTT", "Connecting to " + String(MQTT_HOST) + "...");
  if (mqtt.connect("salt-sensor-esp32", MQTT_USER, MQTT_PASS)) {
    mqtt.subscribe(TOPIC_STATUS);
    publishLog("MQTT", "Connected. Subscribed to " + String(TOPIC_STATUS));
    return true;
  }
  publishLog("MQTT", "Failed, rc=" + String(mqtt.state()) + " - will retry in 30s");
  return false;
}

void publishReading(float distCm, float percent) {
  if (!mqtt.connected()) return;
  String payload = "{\"distance_cm\":" + String(distCm, 1) +
                   ",\"percent\":"     + String((int)percent) + "}";
  mqtt.publish(TOPIC_DATA, payload.c_str(), true);  // retained
  publishLog("MQTT", "Published: " + payload);
}

// ================== SENSOR ==================
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

// ================== LEDs ==================
void updateLEDs(bool blinkState) {
  if (currentStatus == "ok") {
    digitalWrite(greenLedPin,  HIGH);
    digitalWrite(yellowLedPin, LOW);
    digitalWrite(redLedPin,    LOW);
  } else if (currentStatus == "warning") {
    digitalWrite(greenLedPin,  LOW);
    digitalWrite(yellowLedPin, blinkState ? HIGH : LOW);
    digitalWrite(redLedPin,    LOW);
  } else if (currentStatus == "critical") {
    digitalWrite(greenLedPin,  LOW);
    digitalWrite(yellowLedPin, LOW);
    digitalWrite(redLedPin,    blinkState ? HIGH : LOW);
  } else if (currentStatus == "error") {
    digitalWrite(greenLedPin,  blinkState ? HIGH : LOW);
    digitalWrite(yellowLedPin, blinkState ? HIGH : LOW);
    digitalWrite(redLedPin,    blinkState ? HIGH : LOW);
  } else {
    // unknown / no status yet — slow-blink green to show it's alive
    digitalWrite(greenLedPin,  blinkState ? HIGH : LOW);
    digitalWrite(yellowLedPin, LOW);
    digitalWrite(redLedPin,    LOW);
  }
}

// ================== WiFi ==================
void checkWiFi() {
  if (WiFi.status() != WL_CONNECTED) {
    publishLog("System", "WiFi connection lost - reconnecting...");
    WiFi.reconnect();
    unsigned long start = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - start < 10000UL) {
      delay(500);
      Serial.print(".");
    }
    publishLog("System", WiFi.status() == WL_CONNECTED ? "WiFi reconnected." : "WiFi reconnect failed.");
  }
}

// ================== SETUP ==================
void setup() {
  Serial.begin(115200);
  delay(2000);
  Serial.println("\n\n=== Water Softener Salt Sensor v3 ===");

  pinMode(trigPin,      OUTPUT);
  pinMode(echoPin,      INPUT);
  pinMode(redLedPin,    OUTPUT);
  pinMode(yellowLedPin, OUTPUT);
  pinMode(greenLedPin,  OUTPUT);

  // LED self-test
  Serial.println("[Boot] LED self-test...");
  digitalWrite(redLedPin, HIGH);    delay(600);
  digitalWrite(yellowLedPin, HIGH); delay(600);
  digitalWrite(greenLedPin, HIGH);  delay(600);
  for (int i = 0; i < 4; i++) {
    digitalWrite(redLedPin, LOW); digitalWrite(yellowLedPin, LOW); digitalWrite(greenLedPin, LOW);
    delay(300);
    digitalWrite(redLedPin, HIGH); digitalWrite(yellowLedPin, HIGH); digitalWrite(greenLedPin, HIGH);
    delay(300);
  }
  digitalWrite(redLedPin, LOW); digitalWrite(yellowLedPin, LOW); digitalWrite(greenLedPin, LOW);

  // OTA reboot confirmation: 3 rapid triple-flashes
  for (int i = 0; i < 3; i++) {
    digitalWrite(redLedPin, HIGH); digitalWrite(yellowLedPin, HIGH); digitalWrite(greenLedPin, HIGH);
    delay(100);
    digitalWrite(redLedPin, LOW);  digitalWrite(yellowLedPin, LOW);  digitalWrite(greenLedPin, LOW);
    delay(100);
  }

  // WiFi
  Serial.printf("[WiFi] Connecting to %s...\n", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println("\n[WiFi] Connected.  IP: " + WiFi.localIP().toString());

  // OTA
  ArduinoOTA.setHostname("salt-sensor");
  ArduinoOTA.setPassword(OTA_PASSWORD);
  ArduinoOTA.begin();
  Serial.println("[OTA]  Ready.");

  // MQTT
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(mqttCallback);
  mqttConnect();

  publishLog("System", "Salt Sensor v3 ready. IP: " + WiFi.localIP().toString());
}

// ================== LOOP ==================
void loop() {
  ArduinoOTA.handle();
  checkWiFi();

  // MQTT keep-alive and reconnect
  if (mqtt.connected()) {
    mqtt.loop();
  } else if (millis() - lastMqttAttempt >= MQTT_RETRY_INTERVAL) {
    lastMqttAttempt = millis();
    mqttConnect();
  }

  // Blink state (500 ms toggle)
  static bool blinkState = false;
  static unsigned long lastBlink = 0;
  if (millis() - lastBlink >= 500) {
    blinkState = !blinkState;
    lastBlink  = millis();
  }
  updateLEDs(blinkState);

  // Sensor reading every 12 hours
  if (lastReadingTime == 0 || millis() - lastReadingTime >= READING_INTERVAL) {
    lastReadingTime = millis();
    float dist = getFilteredDistance();
    if (dist < 0) {
      publishLog("System", "No valid sensor reading - check wiring.");
      currentStatus = "error";
    } else {
      lastDistance = dist;
      lastPercent  = calculatePercent(dist);
      publishLog("Sensor", "Distance: " + String(dist, 1) + " cm  ->  Salt: " + String((int)lastPercent) + "%");
      publishReading(dist, lastPercent);
    }
  }

  delay(100);
}
