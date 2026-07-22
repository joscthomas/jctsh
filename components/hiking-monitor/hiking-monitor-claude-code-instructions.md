# JCTsh Hiking Monitor — Claude Code Instructions
**Author:** Joseph C Thomas (JCT)
**Purpose:** Step-by-step build instructions for the hiking-monitor (hiking-monitor) component.
**Project:** JCT Smart Home (JCTsh)
**Version:** 1.2
**Version description:** Added Steps 23–26: Hiking observations pipeline via Tasker — voice observations captured on the Pixel during hikes, posted directly to the Apps Script doPost endpoint, written to the Hiking Observations sheet with automatic category classification.
**Related files:** JCTsh-hiking-monitor-phase1.md, core/data-pipeline/JCTsh-Environmental-Data-Architecture.md, JCTsh-Build-Standards.md, CLAUDE.md, components/front-porch-temp-sensor/

---

## Overview

The hiking-monitor is a portable, body-carried ESP32 environmental sensor. It measures temperature, humidity, barometric pressure, and UV index every 2 minutes. Readings are displayed on a Waveshare 2.13" e-ink display. During hikes (no WiFi), readings are logged to onboard flash with NTP-synced timestamps. On return home, the device connects to JCTnet1 WiFi and automatically replays all stored readings to MQTT using the original hike timestamps. This project also builds the JCTsh environmental data pipeline (Google Sheets + Apps Script + Node-RED) for the first time — this infrastructure will be inherited by all subsequent environmental sensors.

MQTT component name: `hiking-monitor`

---

## Working Pattern

Claude Code creates documentation and configuration files. Joseph follows those documents to perform physical assembly, wiring, flashing, and configuration outside of Claude Code. Joseph reports results back, and Claude Code updates documentation to reflect actual findings, deviations, and lessons learned. Do not proceed to the next step until Joseph confirms the current step is complete.

---

## Pre-Flight: Known Issues

**1. JCTsh-Build-Standards.md appears to have incorrect content.** When Claude Code reads `JCTsh-Build-Standards.md`, it receives parts inventory content instead of build standards. This file may have been accidentally overwritten. Joseph should inspect the file and restore the correct content. Build standards patterns are derived from existing components (front-porch-temp-sensor, garage-radar) as a fallback.

**2. LTR-390 UV sensor not confirmed in parts inventory.** The inventory update log from 2026-05-28 notes "hiking-monitor, Stock: E-ink display and push buttons added, various other." The LTR-390 is not listed explicitly in the Sensors table. Confirm receipt before Step 3. See Step 1.

---

## Hardware Context

| Component | Detail | Location |
|---|---|---|
| Microcontroller | ESP32 DevKitC-32, 38-pin, CP2102, USB-C | Bag 1 |
| Temperature/humidity/pressure sensor | BME280 GY-BME280, genuine, I2C 0x76 | Bag 3 (3 spare) |
| UV sensor | Adafruit LTR-390, I2C 0x53 | **Confirm receipt — see Step 1** |
| E-ink display | Waveshare 2.13" HAT V4, 250×122, SSD1680, SPI | Bag 30 |
| Push button | QTEATAK 6×6mm momentary tact | Plastic Box |
| LiPo battery | EEMB 1100mAh 603449, 3.7V, JST | Bag 7 |
| Charge/boost module | TP4056 + boost combined, 33×23mm | Bag 8 |
| Solar panel | SUNYIMA 5.5V 80mA (backpacking only) | Bag 6 |
| Firmware | ESPHome (Arduino framework) | — |
| Custom component | C++ onboard flash logger (hiking_logger.h) | — |
| Enclosure | 3D-printed, white or light PETG | Phase: Install |

**GPIO Assignments:**

| GPIO | Assignment | Notes |
|---|---|---|
| GPIO18 | SPI CLK (e-ink display) | VSPI default |
| GPIO23 | SPI MOSI / DIN (e-ink display) | VSPI default |
| GPIO5 | SPI CS (e-ink display) | Active-low; pulls high during boot (safe for SPI) |
| GPIO17 | DC (e-ink display) | Data/command select |
| GPIO16 | RST (e-ink display) | Active-low reset |
| GPIO4 | BUSY (e-ink display) | Input; high = display busy |
| GPIO21 | I2C SDA | Shared: BME280 + LTR-390 |
| GPIO22 | I2C SCL | Shared: BME280 + LTR-390 |
| GPIO32 | Button | Input pull-up; active-low; triggers display update |
| GPIO35 | Battery voltage ADC | Input-only; ADC1_CH7; voltage divider output |

**I2C Addresses:**
- BME280: 0x76 (SDO/CSB tied to GND on GY-BME280)
- LTR-390: 0x53 (fixed; no configurable address pin)

**Voltage Divider for Battery Monitoring:**
ESP32 ADC max input is 3.3V. LiPo max voltage is ~4.2V.
Use two equal resistors (e.g., 100kΩ + 100kΩ) for 2:1 divider: Vout = Vbatt / 2.
ADC reading × 2 = actual battery voltage.
Use GPIO35 with `attenuation: 11db` in ESPHome for 0–3.9V ADC range.

**LiPo Connector Polarity Warning:**
Verify JST connector polarity between EEMB LiPo and TP4056+boost module before first connection. Do not assume red = positive on the module side. Use a multimeter to confirm polarity at module JST header before inserting the battery.

---

## Network / Integration Architecture

```
BME280 (I2C 0x76) ──┐
LTR-390 (I2C 0x53) ─┤── ESP32 DevKitC-32 (ESPHome + hiking_logger.h)
E-ink display (SPI) ─┤
Button (GPIO32) ─────┤
Battery ADC (GPIO35)─┘
        │
        │ Two operating modes:
        │
        ├── FIELD MODE (no WiFi)
        │       Every 2 min: read sensors → format JSON → write to onboard flash
        │       Button press: update display immediately
        │
        └── HOME MODE (WiFi + MQTT connected)
                On MQTT connect: replay onboard flash log → MQTT data topic
                Every 5 min: publish heartbeat
                Every 2 min: publish live readings directly to MQTT

MQTT broker (Mosquitto, raspberrypi.local:1883)
        │
        ├── jctsh/components/hiking-monitor/data    ← sensor readings + replayed hike logs
        ├── jctsh/components/hiking-monitor/log     ← diagnostic messages
        └── jctsh/components/hiking-monitor/heartbeat ← 5-min heartbeat (home mode only)
                │
                ▼
        Node-RED (wildcard handler: jctsh/components/+/data)
                │ Computes: dew_point_f, heat_index_f
                │ Posts to Google Apps Script → Google Sheets "Environmental Data"
                └── Routes /log → Python log server
                └── Monitors /heartbeat (watchdog wildcard)

Google Sheets ("JCTsh Environmental Data")
        └── Environmental Data sheet (one row per reading, all sources)
```

**MQTT Topics:**

| Topic | Direction | Content |
|---|---|---|
| `jctsh/components/hiking-monitor/data` | ESP32 → broker | JSON sensor reading (see payload below) |
| `jctsh/components/hiking-monitor/log` | ESP32 → broker | JSON log messages — wildcard routes to Python log server |
| `jctsh/components/hiking-monitor/heartbeat` | ESP32 → broker | JSON heartbeat (home mode only) — wildcard monitored by Node-RED watchdog |

**Standard MQTT Payload (from JCTsh-Environmental-Data-Architecture.md):**
```json
{
  "component": "hiking-monitor",
  "ts": "2026-05-27T14:32:00Z",
  "lat": null,
  "lon": null,
  "temp_f": 87.4,
  "humidity_pct": 32.1,
  "pressure_hpa": 1005.2,
  "uv_index": 9.2,
  "battery_v": 3.94,
  "rssi_dbm": -67
}
```
Notes: `lat`/`lon` are always JSON null. `rssi_dbm` is 0 for field-mode readings (no WiFi at time of logging); actual RSSI for home-mode live readings. Derived fields (`dew_point_f`, `heat_index_f`) are computed by Node-RED, not sent by device.

**Log message format:**
```json
{ "component": "hiking-monitor", "category": "System", "message": "..." }
```
Valid categories: `MQTT`, `System`, `Sensor`, `Alert`, `Test`

**Heartbeat format:**
- Log topic: `{ "component": "hiking-monitor", "category": "System", "message": "Heartbeat - uptime: Xh Xm, RSSI: -XXdBm, temp: XX.X°F" }`
- Heartbeat topic: `{ "component": "hiking-monitor", "uptime": "Xh Xm", "rssi": -XX, "temp": XX.X }`

**Update and heartbeat intervals:**
- Sensor logging: every 2 minutes
- Heartbeat: every 5 minutes (home mode only — when WiFi + MQTT connected)

**Display layout:**
```
Temp: 87°F    Humidity: 32%
UV:   9.2     Pressure: ↓
```
Pressure trend arrow: ↑ rising (>+0.5 hPa over last 30 min), ↓ falling (<−0.5 hPa), → steady.

**SmartThings:** Not used. No SmartThings integration.
**HA:** Not used. No HA entities. No MQTT discovery.

**Timeout / interval locations:**
| Interval/timeout | Location | Purpose |
|---|---|---|
| 2 minutes | ESPHome interval | Sensor read + log/publish cycle |
| 5 minutes | ESPHome interval | Heartbeat (guarded: home mode only) |
| 50 ms | C++ loop delay | Throttle between MQTT publishes during log replay |
| 10 minutes | Node-RED watchdog | Heartbeat expiry detection |

---

## BENCH PHASE

All steps in this section are performed on the workbench. No step in this section requires the device to be in its final field configuration. Do not proceed to the Install Phase until every bench step below is confirmed complete.

---

## Step 1 — Parts Inventory Confirmation

**STATUS: COMPLETE (2026-06-02)**

Confirmed findings:
- **LTR-390:** On hand, Bag 22, qty 2. Adafruit #4831, STEMMA QT / Qwiic I2C version.
- **LiPo JST polarity:** Standard — red lead is positive (confirmed with multimeter). TP4056+boost module JST polarity must still be verified at Step 8 before first connection.
- **E-ink display:** V4 sticker present, PCB marked rev 2.2. SSD1680 driver confirmed.

**LTR-390 breadboard note:** The Adafruit LTR-390 (#4831) has STEMMA QT connectors, not standard 0.1" header pins. For breadboard use, solder standard 0.1" male header pins to the through-hole pads on the breakout board before wiring. Alternatively, use STEMMA QT-to-jumper wires if available. This must be done before Step 4.

---

## Step 2 — Create Dedicated MQTT Account

**STATUS: COMPLETE (2026-06-02)**

- MQTT account `hiking-monitor` created on Pi, Mosquitto restarted successfully
- Password stored in `credentials.local.md` → Mosquitto table
- `CLAUDE.md` credentials table updated

---

## Step 3 — ESPHome Configuration and Wiring Documents

**STATUS: COMPLETE (2026-06-02)**

Files created:
- `hiking-monitor.yaml` — ESPHome config (BME280, LTR-390, e-ink display, button, battery ADC, onboard flash replay, heartbeat)
- `secrets.yaml` — populated with all credentials (gitignored)
- `secrets.yaml.template` — template for reference
- `wiring.md` — complete breadboard wiring reference with STEMMA QT header note for LTR-390
- `hiking_logger.h` — C++ onboard flash logging component
- `ESP32pins.png` — copied from garage-radar

**STATUS: COMPLETE (2026-06-02)**

LTR-390 header pins soldered, files reviewed, ready to wire.

---

## Step 4 — Breadboard Wiring

**STATUS: COMPLETE (2026-06-03)** — all connections wired except battery charger module (deferred to Step 8).

**Joseph does:** Wire the breadboard per `wiring.md`. Sequence:
1. Insert ESP32 into 830-point breadboard (straddles center gap)
2. Mark key GPIO rows per CLAUDE.md note: ESP32 pin labels face down when inserted — use masking tape labels on breadboard rows for GPIO18, 21, 22, 23, 32, 35
3. Wire BME280 (I2C): VCC→3.3V, GND→GND, SDA→GPIO21, SCL→GPIO22
4. Wire LTR-390 (I2C): VIN→3.3V, GND→GND, SDA→GPIO21, SCL→GPIO22
5. Wire e-ink display (SPI + control): per wiring.md (CLK→GPIO18, DIN→GPIO23, CS→GPIO5, DC→GPIO17, RST→GPIO16, BUSY→GPIO4)
6. Wire push button: one leg→GPIO32, other leg→GND (ESPHome uses internal pull-up)
7. Wire voltage divider for battery monitoring: R1 and R2 (100kΩ each) with midpoint→GPIO35
8. Power ESP32 via USB-C from PC (not LiPo yet — Step 8)

**Joseph confirms:** Wiring complete. No shorts. Ready to flash.

---

## Step 5 — Flash Base Firmware and Validate Sensors + Display

**STATUS: COMPLETE (2026-06-03)**

Actual readings (indoors, Tucson):
- Temperature: 105°F — likely ESP32 self-heating the BME280 on breadboard; will improve on perfboard when BME280 is positioned away from ESP32
- Humidity: 12%
- Pressure: steady (trend arrow "->") — plausible for Tucson summer
- UV index: 0.00 (indoors, expected)

Findings:
- E-ink display model `2.13in-ttgo-b74` worked correctly on first try
- Display updates every 2 minutes and on button press ✓
- Button triggers immediate display refresh ✓
- "Hiking monitor online" and "MQTT connected" visible in log dashboard ✓
- Heartbeat appearing every 5 minutes ✓

**on_connect timing fix:** ESPHome drops `id(mqtt_client).publish()` calls made directly inside a raw lambda in `on_connect` — they fire before the broker session is fully ready. Fix: use native `mqtt.publish` actions with a `- delay: 500ms` prefix, matching the front-porch-temp-sensor pattern. Raw lambda calls in `on_connect` still work for the onboard flash replay (which runs after the native publishes).

---

## Step 6 — Custom Onboard Flash Logging Component Integration

**STATUS: COMPLETE (2026-06-03)**

Confirmed during Step 5 testing. When the device was disconnected from WiFi (during OTA flash cycles), it logged readings to onboard flash. On reconnect, the log dashboard showed:
- "Replaying 5 hike readings..."
- "Hike log replay complete."

All onboard flash behaviors confirmed working:
- `hike_log_begin()` mounts on boot ✓
- `hike_log_write()` logs to `/hike_log.jsonl` when WiFi disconnected ✓
- `hike_log_get_all()` returns stored lines on reconnect ✓
- `hike_log_clear()` clears log after replay ✓
- `hike_log_has_data()` guard prevents empty replay attempts ✓

Timestamp accuracy not explicitly verified (readings were logged during brief OTA disconnects of seconds, not minutes) — full timestamp accuracy will be confirmed in Step 12 field mode simulation with longer disconnection periods.

---

## Step 7 — Pressure Trend Validation

**STATUS: COMPLETE (2026-06-03)**

Display shows "P ->" (ASCII steady arrow) after the device ran for several hours. Arrow renders correctly on the e-ink display. Unicode arrows were not attempted — ASCII fallback (`->`, `^`, `v`) was already in the YAML and works fine.

---

## Step 8 — Power System Integration

**STATUS: COMPLETE (2026-06-04)**

- LiPo polarity verified: red = positive (3.84V multimeter reading) ✓
- TP4056 module has solder pads (not JST) — wire leads soldered to pads
- VOUT+: 5.7V (boost running slightly high — acceptable)
- Device running from LiPo without USB ✓
- `battery_v` in MQTT: 3.85V (matches multimeter 3.84V) ✓
- Full data payload confirmed. See `power-system.md` for complete readings.
- USB charging via TP4056 micro-USB port: not yet tested (deferred)

---

## Step 9 — Data Pipeline: Google Sheets Setup

**Claude Code does:** ✓ COMPLETE — `components/hiking-monitor/data-pipeline.md` created. Covers Steps 9–11: Google Sheets setup, Apps Script code and deployment, and Node-RED flow JSON.

Section 9 of data-pipeline.md covers Google Sheets setup:
- Create "JCTsh Environmental Data" Google Sheets workbook in Joseph's Google Drive
- Add sheet "Environmental Data" with exact column schema from JCTsh-Environmental-Data-Architecture.md
- Add sheet "Hiking Observations" (schema per architecture doc — for future use)
- Record spreadsheet ID (in URL: `docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/`)

**Joseph does:**
1. Create the Google Sheets workbook "JCTsh Environmental Data"
2. Add the Environmental Data sheet with exact column headers: `timestamp`, `source`, `lat`, `lon`, `temp_f`, `humidity_pct`, `pressure_hpa`, `dew_point_f`, `heat_index_f`, `uv_index`, `irradiance_wm2`, `wind_speed_mph`, `wind_dir_deg`, `rain_tips`, `rainin`, `dailyrainin`, `battery_v`, `rssi_dbm`, `pm1_ug_m3`, `pm25_ug_m3`, `pm4_ug_m3`, `pm10_ug_m3`, `voc_index`, `nox_index`
3. Add a "Hiking Observations" sheet (empty, just the header row from architecture doc)
4. Note the spreadsheet ID from the URL

**Joseph confirms:** Spreadsheet created, both sheets added, spreadsheet ID noted.

---

## Step 10 — Data Pipeline: Google Apps Script Web App

**Claude Code does:** Write complete Google Apps Script code and document the deployment procedure in data-pipeline.md Section 10:
- `doPost(e)` function accepting JSON POST
- Parses payload: routes `hiking-observations` to Observations sheet, all others to Environmental Data sheet
- Appends one row per request
- Authenticates via secret key in URL query parameter (`?key=<SECRET>`)
- Returns `{"status":"ok"}` on success, error message on failure

**Joseph does:**
1. In the Google Sheets workbook, open Extensions → Apps Script
2. Paste the Apps Script code
3. Deploy as web app:
   - Execute as: Me
   - Who has access: Anyone (required for Node-RED to POST without OAuth)
4. Copy the deployment URL (format: `https://script.google.com/macros/s/<SCRIPT_ID>/exec`)
5. Choose a secret key (random string, 16+ chars)
6. Store URL and key in Node-RED environment variables: `APPS_SCRIPT_URL` and `APPS_SCRIPT_KEY`

**STATUS: COMPLETE (2026-06-04)** — Apps Script deployed, test POST confirmed `{"status":"ok"}`, row appeared in Environmental Data sheet. URL and API key stored in `credentials.local.md`.

---

## Step 11 — Data Pipeline: Node-RED Handler Flow

**Claude Code does:** Write the complete Node-RED wildcard data handler flow as JSON and document it in data-pipeline.md Section 11.

Flow: `jctsh/components/+/data` subscription → parse JSON → compute derived fields → POST to Apps Script → log success/failure

The flow must:
1. MQTT In node subscribing to `jctsh/components/+/data`
2. Function node: parse payload JSON; compute `dew_point_f` and `heat_index_f` from `temp_f` + `humidity_pct`; add `source` field from `component`; map fields to Sheets column order
3. HTTP Request node: POST to Apps Script URL with `?key=<SECRET>` (uses Node-RED env vars)
4. Success branch: MQTT publish log message confirming row appended
5. Error branch: MQTT publish log message with error detail

Dew point formula (Magnus approximation):
```
a = 17.27, b = 237.7
gamma = (a * temp_c / (b + temp_c)) + ln(humidity/100)
dew_point_c = (b * gamma) / (a - gamma)
dew_point_f = dew_point_c * 9/5 + 32
```

Heat index formula (NWS Rothfusz regression, valid for temp ≥ 80°F, humidity ≥ 40%):
```
HI = -42.379 + 2.04901523*T + 10.14333127*H - 0.22475541*T*H - 0.00683783*T² 
     - 0.05481717*H² + 0.00122874*T²*H + 0.00085282*T*H² - 0.00000199*T²*H²
```
Where T = temp_f, H = humidity_pct. Use simple formula (T + H/5 - 10.3) when temp < 80°F.

**Joseph does:**
1. Import the Node-RED flow JSON via Node-RED UI → Import → Clipboard
2. Set Node-RED environment variables `APPS_SCRIPT_URL` and `APPS_SCRIPT_KEY`
3. Deploy the flow
4. Trigger a test MQTT message on `jctsh/components/hiking-monitor/data` with a valid payload
5. Confirm the row appears in the Google Sheet with correct values including computed dew_point_f and heat_index_f

**STATUS: COMPLETE (2026-06-04)** — `Sheets row appended for hiking-monitor` appearing in log dashboard every 2 minutes. Rows accumulating in Google Sheets with `dew_point_f` and `heat_index_f` populated.

**Deployment notes:**
- Env vars set in `/home/pi/.node-red/environment` (sourced via `EnvironmentFile=` in systemd service)
- Flow injected via direct `flows.json` edit; nodes need `z` property pointing to a tab node or they are orphaned and inactive
- Google Apps Script returns HTTP 302 → follow redirect → 405 (redirect destination rejects POST). Row IS appended on the initial POST. Treat 405 as success in the check response function.
- API key must be alphanumeric — special characters (`&`, `@`, `*`) break URL query parameter parsing even with `encodeURIComponent`

---

## Step 12 — Full End-to-End Test

**Claude Code does:** Create `components/hiking-monitor/testing.md` with the complete validation procedure.

**Joseph does:** Run the full end-to-end test:

1. **Sensor validation** — all four sensor values (temp, humidity, pressure, UV) updating every 2 minutes in MQTT Explorer
2. **Display validation** — all four fields rendering correctly on e-ink display; pressure arrow showing "→" (steady)
3. **Button validation** — button press triggers immediate display refresh
4. **Log dashboard** — log messages visible at `http://raspberrypi.local/` under `hiking-monitor`
5. **Heartbeat** — heartbeat appearing every 5 minutes in log dashboard
6. **Field mode simulation:**
   - Change WiFi password in secrets.yaml to wrong value, OTA flash
   - Let device log 5+ readings (10+ minutes)
   - Change password back to correct value, OTA flash
   - Confirm replay: log dashboard shows "Replaying N readings" and "Replay complete"
   - Confirm replayed rows appear in Google Sheets with original timestamps (not current time)
7. **Google Sheets validation:**
   - Confirm Environmental Data sheet has rows from test
   - Confirm `source` column = `hiking-monitor`
   - Confirm `dew_point_f` and `heat_index_f` are populated (not blank)
   - Confirm `lat` = null, `lon` = null
8. **Battery validation:**
   - Confirm `battery_v` column in Sheets shows plausible value (3.7–4.2V)
9. **Power cycle test:**
   - Power off by disconnecting LiPo
   - Power on, confirm device reconnects and resumes normal operation
   - Confirm onboard flash log survives power cycle (if data was logged before power-off, it replays after power-on + WiFi connect)

**Joseph confirms:** Report results for each test item. Identify any failures.

**Claude Code does:** Update testing.md with actual results. Fix any failures before proceeding to Install Phase.

---

## Step 13 — Parts Inventory Update

**STATUS: COMPLETE (2026-06-04)**

**Claude Code does:** Update `jctsh-parts-inventory.md` Inventory Update Log:
- ESP32 ×1 used (hiking-monitor)
- BME280 ×1 used (hiking-monitor)
- LTR-390 ×1 used (hiking-monitor)
- E-ink display ×1 used (hiking-monitor)
- Push button ×1 used (hiking-monitor)
- EEMB LiPo ×1 used (hiking-monitor)
- TP4056+boost module ×1 used (hiking-monitor)

Also update the LTR-390 Sensors table entry when confirmed received.

**Joseph confirms:** Inventory updated accurately.

---

## Bench Phase Complete — Install Phase Begins

All bench steps above are confirmed complete. The device has been:
- Sensors validated (BME280, LTR-390, e-ink display, button)
- Onboard flash logging and WiFi replay confirmed working
- Power system (LiPo + TP4056+boost) confirmed
- Environmental data pipeline live (Google Sheets receiving data via Node-RED + Apps Script)
- Full end-to-end test passed including field mode simulation

Do not proceed to Install Phase until all bench steps are confirmed complete.

---

## INSTALL PHASE

The hiking monitor install phase is primarily a physical enclosure build, not a location-specific installation like wall-mounted sensors. The device does not have a fixed installed location — it is portable.

---

## Step 14 — Perfboard Build

**Claude Code does:** Create `components/hiking-monitor/perfboard-layout.md` — COMPLETE (2026-06-04)


- ESP32 DevKit on two 19-pin female header strips (removable — do not solder directly)
- BME280 on female header strip, positioned away from ESP32 (ESP32 generates slight heat)
- LTR-390 on female header strip, positioned for top-face mounting in enclosure (must face sky)
- E-ink display connection via ribbon cable or 8-wire harness (not direct perfboard mount — display is on enclosure face)
- Button connection via 2-wire harness to perfboard
- Voltage divider resistors (100kΩ + 100kΩ) soldered directly to perfboard
- TP4056+boost module mounted on separate section of perfboard or separately in enclosure
- Wire harnesses for inter-module connections (use silicone hookup wire, Shelf)
- 5×7cm or 7×9cm perfboard depending on layout (measure before cutting)

**Joseph does:** Transfer to perfboard per perfboard-layout.md. Validate all sensors reading correctly after transfer.

**Joseph confirms:** Perfboard build complete, all sensors reading correctly, power system functioning.

---

## Step 15 — Enclosure Design

**Claude Code does:** Research and document enclosure design options in `components/hiking-monitor/enclosure.md`:
- Target footprint: ~75mm × 45mm × 20mm
- Requirements: Stevenson-screen louvered port for BME280, LTR-390 on top face, micro USB external, JST external, USB-C internal, button on side, carabiner bail/loop, light-colored PETG
- Evaluate: design from scratch vs. adapt existing open-source Stevenson screen STL

Research questions for enclosure.md:
1. Are there open-source STL files for similar hiking monitor enclosures with Stevenson-screen ventilation?
2. What is the UV transmission rating of natural PETG? (LTR-390 may need a UV-transparent window if recessed — or can be flush-mounted on the top face)
3. What free/low-cost 3D modeling tool is recommended for a first-time enclosure design (if designing from scratch)?

**Joseph does:** Review enclosure.md and decide: design from scratch or adapt existing. If adapting, identify the base STL. If designing from scratch, choose the modeling tool.

**Joseph confirms:** Enclosure approach decided. Report chosen approach.

**Claude Code does:** Update enclosure.md with the decided approach and any specific design guidance needed.

---

## Step 16 — Enclosure Assembly and Final Test

**Joseph does:**
1. Print the enclosure in white or light PETG
2. Install perfboard, display, LiPo, and TP4056+boost module
3. Route wires and close enclosure
4. Confirm all external ports accessible: micro USB charging, JST solar, button

**Joseph confirms:** Device assembled. All sensors, display, button, and power system confirmed functional after enclosure assembly.

---

## Step 17 — Field Test

**Joseph does:** Take device on a real hike (or extended outdoor walk):
1. Confirm device operates in field mode (no WiFi, logging to onboard flash)
2. Confirm display updates every 2 minutes
3. Confirm button wakes/refreshes display
4. Return home, dock in cradle (micro USB connected to charger)
5. Confirm device connects to JCTnet1 WiFi
6. Confirm hike log replays to MQTT
7. Confirm replayed readings appear in Google Sheets with correct timestamps
8. Confirm readings are correlated to GaiaGPS track by matching timestamps

**Joseph confirms:** Field test complete. Actual hike data in Google Sheets. Timestamp correlation to GaiaGPS track confirmed.

---

## Step 18 — README and Final Housekeeping

**Claude Code does:** Create `components/hiking-monitor/README.md` following the garage-radar README pattern. Must include:
- What the component does (field mode + home mode)
- Hardware table
- GPIO assignment table
- Wiring overview
- MQTT topics (data, log, heartbeat)
- Operating modes: field vs. home
- Onboard flash logging: file name, format, capacity
- Replay behavior: trigger, throttle, log messages
- Power system: TP4056+boost, LiPo, voltage divider
- Display: layout, update interval, button behavior
- Data pipeline: Google Sheets, Apps Script, Node-RED flow
- Known behaviors / tuning notes
- Deferred future enhancements
- Build document index

Also do the following final housekeeping:
1. Add `hiking-monitor` to root `README.md` Components list
2. Add `hiking-monitor` to root `CLAUDE.md` credentials table (MQTT account)
3. Add hiking-monitor IP, hostname `hiking-monitor.local`, and MAC to `jctsh-network.md` (obtain IP and MAC from ESPHome logs or router DHCP table)
4. Update `JCTsh-Parts-Inventory.md` inventory update log (Step 13 above)

**Joseph confirms:** README complete and accurate. All housekeeping items done.

---

## Backlog

### Sensor Health Detection (§4.6)
Per JCTsh-Build-Standards.md §4.6, ESPHome components with I2C sensors must publish explicit error log messages when a sensor read returns NaN. This component has two I2C sensors that need health checks added to the 5-minute heartbeat interval:
- BME280: check `id(bme_temp).state` — message: `"BME280 read failed — check I2C wiring"`
- LTR390: check `id(ltr_uv_index).state` — message: `"LTR390 read failed — check I2C wiring"`

Pattern: see `components/front-porch-temp-sensor/front-porch-temp-sensor.yaml` interval block. Add after the heartbeat `mqtt.publish` actions. Category: `Sensor`.

---

## Future Enhancements

### Deep Sleep Mode
Deep sleep between 2-minute readings reduces average current draw significantly and could extend backpacking battery life considerably. Deferred until basic operation confirmed. Key challenge: onboard flash log file must be properly closed before sleep; NTP-synced clock must be re-synced after wake (or RTC used). Implement after first successful hike.

### Solar Charging (Backpacking)
SUNYIMA panel (Bag 6) connects to TP4056 VIN+ via JST connector. Verify panel voltage under load before finalizing wiring (target: 4.5–6V; module input range on datasheet). Enclosure design must include accessible JST port for solar input. Only needed for multi-day backpacking — not required for day hikes.

### LTR-390 Enclosure Glazing
If LTR-390 is recessed in the enclosure rather than flush-mounted on the top face, it may require a UV-transparent window (acrylic blocks UV; use UV-transmissive materials or a cutout). Evaluate during enclosure design phase.

### Aspiration Fan for BME280
Forced airflow over BME280 could improve temperature accuracy (avoids sensing heated air inside enclosure). Evaluate after first hike — may not be needed if the Stevenson-screen ventilation provides sufficient natural airflow.

### Hiking Observations Pipeline
Voice observations via Google Recorder → Google Docs → Apps Script → Hiking Observations Sheets tab → MQTT. Path A (manual share) is the starting point. Design is complete in core/data-pipeline/JCTsh-Environmental-Data-Architecture.md. Implement as a separate project after the hiking monitor data pipeline is proven.

---

## Notes for Claude Code

- **Flash path:** Always flash from `C:\esphome\hiking-monitor\` — not from the repo path. Spaces in "JCT Documents" break the ESP-IDF compiler. Copy YAML, secrets.yaml, and hiking_logger.h to that directory before every flash.
- **ESPHome MQTT discovery:** Set `discovery: false` — the hiking monitor is not integrated with Home Assistant. No HA entities needed.
- **E-ink display model string:** The Waveshare 2.13" V4 SSD1680 likely uses model `2.13in-ttgo-b74` in ESPHome `waveshare_epaper` platform. Confirm at Step 5 — try `2.13in-ttgo-b74` first; if display shows garbage or doesn't initialize, try `2.13in-b74` or check current ESPHome docs for SSD1680 model strings.
- **Unicode arrows on e-ink:** ESPHome `waveshare_epaper` rendering uses bitmap fonts. Unicode arrows (↑ → ↓) require the font to include those glyphs. If rendering fails, fall back to ASCII: `^` / `=` / `v`. Confirm in Step 7.
- **ESP32 filesystem in ESPHome/Arduino:** Use SPIFFS via the ESP-IDF native VFS (`esp_spiffs.h`) — bundled with ESP-IDF, no external library needed. LittleFS (`LittleFS.h`, Arduino ESP32 core) is the alternative with better wear-leveling and directory support, but neither advantage matters for a single-file sequential log. Reference implementation: `hiking_logger.h`.
- **MQTT account:** Create before first flash. Account name: `hiking-monitor`. Commands: see mqtt-account-setup.md. Ownership gotcha: `mosquitto_passwd` resets file group to root — always run `sudo chown root:mosquitto /etc/mosquitto/passwd` immediately after.
- **Heartbeat:** Only publish heartbeat when WiFi + MQTT connected. Guard the heartbeat interval with a `wifi.connected` condition. Do not publish heartbeats during field mode — they would pile up and replay incorrectly.
- **rssi_dbm in field mode:** When logging to onboard flash in field mode (no WiFi), set `rssi_dbm` to `0` in the payload. Node-RED or Sheets analysis can filter `rssi_dbm = 0` to identify field-mode readings. Do not read wifi_signal sensor when WiFi is not connected — it returns NaN.
- **Pressure trend calculation:** Store a circular buffer of 16 pressure readings. Compare current reading to the reading 15 cycles ago (15 × 2 min = 30 min). Initialize all buffer slots to 0; guard against comparing to uninitialized slots (value == 0 means no history yet).
- **Node-RED flow:** The wildcard `jctsh/components/+/data` handler is new infrastructure — it does not exist yet. Build it in Step 11. The existing `jctsh/+/+/log` and `jctsh/+/+/heartbeat` wildcard handlers already exist and catch the hiking monitor automatically.
- **Apps Script auth:** The secret key in the URL query parameter is sufficient for this use case. No OAuth needed. URL format: `https://script.google.com/macros/s/<ID>/exec?key=<SECRET>`. Node-RED uses env vars for both.
- **Network entry:** After first successful boot, retrieve hiking-monitor IP and MAC from the ESPHome log or router DHCP table. Add to jctsh-network.md. Reserve the DHCP IP on the router.
- **Bench-first rule:** Steps 14–18 (enclosure, field test) come after all bench steps are confirmed. Do not skip to enclosure before the full end-to-end test (Step 12) passes.
- **Build Standards reference:** JCTsh-Build-Standards.md appears to have incorrect content (parts inventory instead of build standards). Standards are derived from existing component patterns (front-porch-temp-sensor, garage-radar) throughout these instructions. Joseph should investigate and restore the correct file.

---

## ITERATIVE REFINEMENT PHASE

Steps 19–21 add GPS correlation and Pixel hotspot sync as a discrete layer on top of the proven core build. Do not begin this phase until Step 18 (field test) is confirmed complete. The core pipeline (Google Sheets receiving data, timestamps accurate, onboard flash replay working) must be proven before adding GPS infrastructure on top of it.

These steps involve no firmware changes to the core hiking monitor logic. The `lat`/`lon` fields are already reserved as `null` in the payload schema — they are populated by Node-RED at upload time, not by the device. The only firmware change is adding the Pixel hotspot as a second WiFi network in Step 21.

The Node-RED GPS pipeline built in Steps 19–20 is shared infrastructure. The air quality monitor inherits it automatically via the existing `jctsh/components/+/data` wildcard handler — no air quality monitor changes needed. The van sensor project (future) inherits it the same way.

---

## Step 19 — GPSLogger Configuration and Google Sheets GPS Track

**Claude Code does:** Create `components/hiking-monitor/gps-pipeline.md` documenting the full GPS correlation architecture:

Section 1 — GPSLogger Android app configuration:
- App: GPSLogger for Android (open source, F-Droid or Play Store)
- Logging: enabled, passive background operation
- Custom URL logger: GET to Google Apps Script GPS endpoint (see Section 2)
- URL format: `https://script.google.com/macros/s/<SCRIPT_ID>/exec?key=<API_KEY>&action=gps&lat=%LAT&lon=%LON&ts=%TIME&acc=%ACC&alt=%ALT`
  - `%LAT`, `%LON`, `%ALT`, `%ACC`, `%TIME` are GPSLogger placeholders substituted at post time
  - `%TIME` is a Unix epoch timestamp (seconds) — Apps Script converts to ISO8601
- Retry on failure: enabled — GPSLogger queues failed GETs and retries when connectivity returns
- Posting interval: every 30 seconds
- No router port forwarding or public Pi access required — posts go directly to Google

Section 2 — Google Apps Script GPS endpoint:
- Extend the existing Apps Script in "JCTsh Environmental Data" with a new `action=gps` branch in `doGet(e)`
- When `action=gps`: parse `lat`, `lon`, `ts` (Unix epoch → ISO8601), `acc`, `alt` from query params
- Append one row to "GPS Track" sheet: `timestamp`, `lat`, `lon`, `accuracy_m`, `altitude_m`
- Authenticate via existing `API_KEY` query parameter — no new credentials needed
- Return `{"status":"ok"}` — required for GPSLogger retry logic

Section 3 — "GPS Track" sheet in "JCTsh Environmental Data":
- Add "GPS Track" tab to the existing spreadsheet
- Columns: `timestamp` (ISO8601 UTC), `lat`, `lon`, `accuracy_m`, `altitude_m`
- No pruning needed — ~1,200 trackpoints per hike at 30s interval ≈ trivial size

Section 4 — Timestamp lookup (for Step 20):
- Given a sensor reading timestamp `ts`, find the GPS Track row with the nearest timestamp
- Acceptable match window: ±5 minutes
- If no row within ±5 minutes: return `null`/`null` — do not interpolate
- Lookup is performed by Node-RED via an Apps Script `action=lookup` GET endpoint (see Step 20)

**Joseph does:**
1. Install GPSLogger on Pixel 10 Pro XL
2. Add "GPS Track" sheet to "JCTsh Environmental Data" spreadsheet with correct columns
3. Extend the Apps Script with the `action=gps` branch per gps-pipeline.md Section 2; redeploy as new version
4. Configure GPSLogger custom URL per gps-pipeline.md Section 1
5. Take a short outdoor walk with GPSLogger active
6. Verify trackpoints appearing in the "GPS Track" sheet

**Joseph confirms:** GPSLogger posting successfully. Trackpoints visible in GPS Track sheet. Report: number of trackpoints logged, approximate duration of test walk.

**Claude Code does:** Update gps-pipeline.md with actual Apps Script deployment URL, any GPSLogger settings that differed from defaults, and confirmed sheet column layout.

---

## Step 20 — Node-RED lat/lon Population in Wildcard Data Handler

**Claude Code does:** Update the Node-RED wildcard data handler flow (built in Step 11) to populate `lat`/`lon` from the GPS Track sheet. Update `data-pipeline.md` Section 11 to reflect the change.

Also extend the Apps Script with an `action=lookup` GET endpoint:
- Accepts `ts` (ISO8601 timestamp) query parameter
- Reads all rows from "GPS Track" sheet
- Finds the row with timestamp nearest to `ts`
- If nearest row is within ±5 minutes: returns `{"lat": <lat>, "lon": <lon>}`
- If no row within ±5 minutes or sheet is empty: returns `{"lat": null, "lon": null}`

The updated Node-RED flow:
1. MQTT In: `jctsh/components/+/data` (unchanged)
2. HTTP Request node — **GPS lookup** (new, inserted before derived fields):
   - GET `https://script.google.com/macros/s/<SCRIPT_ID>/exec?key=<KEY>&action=lookup&ts=<msg.payload.ts>`
   - On success: set `msg.payload.lat` and `msg.payload.lon` from response
   - On error or null response: leave `lat`/`lon` as `null` — do not break the pipeline
3. Function node — derived fields (`dew_point_f`, `heat_index_f`) (unchanged)
4. HTTP Request: POST to Apps Script environmental data endpoint (unchanged)
5. Success/error logging (unchanged)

**Joseph does:**
1. Redeploy the Apps Script with the `action=lookup` branch added
2. Import the updated Node-RED flow and deploy
3. Trigger a test MQTT message with a timestamp that falls within the GPS track logged in Step 19
4. Confirm `lat` and `lon` columns in Google Sheets are populated with plausible coordinates
5. Trigger a test message with a timestamp outside the GPS track
6. Confirm `lat` and `lon` are null

**Joseph confirms:** lat/lon populated correctly for matched timestamps. Null returned for unmatched timestamps. All other pipeline fields unaffected.

**Claude Code does:** Update data-pipeline.md Section 11 with the lookup endpoint code and test results.

---

## Step 21 — Pixel Hotspot Second WiFi Network

**Claude Code does:** Update `hiking-monitor.yaml` to add the Pixel hotspot as a second WiFi network. Update `wiring.md` (or create a `wifi-config.md` note if wiring.md is not the right home) to document the two-network configuration.

ESPHome `wifi:` block change:
```yaml
wifi:
  networks:
    - ssid: !secret wifi_ssid
      password: !secret wifi_password
    - ssid: !secret hotspot_ssid
      password: !secret hotspot_password
  ap:
    ssid: "hiking-monitor-fallback"
    password: !secret ap_password
```

Add to `secrets.yaml`:
```yaml
hotspot_ssid: "<Pixel hotspot SSID>"
hotspot_password: "<Pixel hotspot password>"
```

Add to `secrets.yaml.template`:
```yaml
hotspot_ssid: "<Pixel hotspot SSID>"
hotspot_password: "<Pixel hotspot password>"
```

Important constraints to document:
- Pixel hotspot SSID and password must be fixed — do not change them after this step
- ESP32 tries networks in order: home WiFi first, hotspot second — hotspot only connects when home WiFi is not in range
- When connected via hotspot, the device connects to the home Mosquitto broker over cellular using the same broker hostname/IP as always — no broker configuration change needed
- Onboard flash replay triggers on any MQTT connect, regardless of which network connected — hotspot sync works identically to home sync
- Heartbeat publishes on hotspot connection — Node-RED watchdog will show device online during hotspot sync; this is correct behavior
- Cellular data volume: trivially small — ~200 bytes/reading × 180 readings/6-hour hike = ~36KB per hike replay

**Joseph does:**
1. Set a fixed Pixel hotspot SSID and password on the Pixel 10 Pro XL (note: changing these later requires re-flashing the device)
2. Add hotspot credentials to `secrets.yaml`
3. OTA flash updated YAML from `C:\esphome\hiking-monitor\`
4. With home WiFi unavailable (or temporarily disabled on the device), enable Pixel hotspot
5. Confirm device connects to hotspot
6. Confirm device connects to home Mosquitto broker over cellular
7. With a few readings in onboard flash (log a short field mode session first), confirm replay occurs over hotspot connection
8. Confirm replayed readings appear in Google Sheets with correct timestamps

**Joseph confirms:** Hotspot connection confirmed. Onboard flash replay over hotspot confirmed. Readings in Google Sheets with correct timestamps. Report: approximate time from hotspot enable to replay complete.

**Claude Code does:** Update `wifi-config.md` (or equivalent) with actual hotspot SSID (not password), confirmed replay behavior, and timing note. Update `secrets.yaml.template` to reflect the new field.

---

## Step 22 — Harvest New Patterns into Build Standards

**Claude Code does:** Review the completed hiking monitor build in full — ESPHome YAML, `hiking_logger.h`, Node-RED flows (wildcard data handler, GPS lookup, GPS HTTP-in listener), Apps Script, wiring decisions, power system, and any deviations from original plans captured in step confirmations. Identify coding patterns, configuration decisions, or integration approaches not yet captured in `JCTsh-Build-Standards.md` or that supersede existing entries.

For each candidate pattern, state:
- (a) What the pattern is
- (b) Where it appeared in this build (file and step)
- (c) Proposed addition or update to `JCTsh-Build-Standards.md`

Likely candidates (Claude Code confirms or adds to this list after reviewing the actual build):
- Onboard flash logging + WiFi replay pattern (custom C++ ESPHome component)
- Multi-network WiFi with ordered fallback (home → hotspot)
- GPS trackpoint store (flat JSONL file) and timestamp-nearest lookup in Node-RED
- Node-RED file read in function node (`fs.readFileSync` with try/catch)
- `rssi_dbm = 0` convention for field-mode readings
- `on_connect` timing fix (native `mqtt.publish` + 500ms delay before raw lambda replay)
- E-ink display model string confirmation (SSD1680 → `2.13in-ttgo-b74`)
- ASCII pressure trend arrows as fallback for e-ink Unicode rendering

Do not write changes to `JCTsh-Build-Standards.md` until Joseph reviews and approves.

**Joseph does:** Review proposed additions. Approve, modify, or reject each one.

**Joseph confirms:** Approved additions identified. Proceed to update `JCTsh-Build-Standards.md`.

**Claude Code does:** Write approved additions and updates to `JCTsh-Build-Standards.md`. Bump the version number and update the version description to reflect what was added.

---

## Step 23 — Hiking Observations: Update Apps Script

**Claude Code does:** Update `environmental-data.gs` to handle voice observations from Tasker — strip the "observation" keyword prefix, scan the text against the category taxonomy, normalize the timestamp, and append to the Hiking Observations sheet. The updated handler is already in `core/data-pipeline/environmental-data.gs`.

Paste the entire contents of `core/data-pipeline/environmental-data.gs` into the Apps Script editor (Extensions → Apps Script), replacing what's there. Then redeploy:

1. Click **Deploy → Manage deployments**
2. Click the pencil icon on the existing deployment
3. Change **Version** to **New version**
4. Click **Save**

The deployment URL does not change.

**Claude Code does:** Construct a test POST from PowerShell to verify the updated handler. Retrieve `<SCRIPT_ID>` and `<KEY>` from `credentials.local.md`, then put the test command on the clipboard.

```powershell
$url = "https://script.google.com/macros/s/<SCRIPT_ID>/exec?key=<KEY>"
$body = '{"component":"hiking-observations","ts":"2026-06-13T17:00:00Z","lat":null,"lon":null,"observation":"saw a hawk circling above the ridge, very clear sky today","categories":[],"source":"voice"}'
Invoke-RestMethod -Uri $url -Method Post -ContentType "application/json" -Body $body
```

Expected response: `{"status":"ok"}`

**Joseph does:** Run the test command. Then open the Hiking Observations sheet and confirm a new row appeared:

| Column | Expected value |
|---|---|
| `timestamp` | `2026-06-13T17:00:00.000Z` |
| `observation` | `saw a hawk circling above the ridge, very clear sky today` |
| `categories` | `["wildlife","visibility","sky"]` |
| `source` | `voice` |

**Joseph confirms:** Row in sheet is correct. Proceed to Step 24.

---

## Step 24 — Hiking Observations: Create Tasker Task

**Joseph does:** In Tasker on the Pixel 10 Pro XL, create a new task named **"Log Observation"**:

1. Open Tasker → Tasks tab → **+** → name it `Log Observation`

2. **Action 1 — Get Voice:**
   - Search for **Get Voice**
   - Title: `Speak your observation`
   - Output Variable: `obs_text` (no `%` — Tasker adds it)
   - Note: Get Voice stores result in `%VOICE` regardless of the Output Variable field

3. **Action 2 — Stop if no input (user cancelled):**
   - Search for **Stop**
   - Condition: `%VOICE` **Is Not Set**
   - Error checkbox: **unchecked**

4. **Action 3 — POST to Apps Script:**
   - Search for **HTTP Request**
   - Method: `POST`
   - URL: *(from `credentials.local.md` — deployment URL + `?key=<KEY>`)*
   - Headers: `Content-Type: application/json`
   - Body: `{"component":"hiking-observations","ts":"%TIMES","lat":null,"lon":null,"observation":"%VOICE","categories":[],"source":"voice"}`

   Tasker substitutes `%VOICE` with spoken text and `%TIMES` with Unix epoch seconds before sending. No JavaScript needed.

5. **Action 4 — Notify:**
   - Search for **Flash**
   - Text: `Observation logged`

**Test the task manually:** In the Tasks list, tap the play button next to `Log Observation`. Speak an observation when prompted. Check the Hiking Observations sheet — a new row should appear within a few seconds with categories auto-assigned.

**Joseph confirms:** Manual task test produced a correct row in the sheet. Proceed to Step 25.

---

## Step 25 — Hiking Observations: Home Screen Widget

**Joseph does:** Add the Tasker task as a one-tap home screen widget on the Pixel:

1. Long-press an empty area of the home screen → **Widgets**
2. Find **Tasker** in the widget list → select **Task Shortcut** (1×1)
3. Drag it to a convenient home screen position
4. When prompted, select task: **Log Observation**
5. Icon and label: leave default or customize

The widget is now a single tap to record an observation from anywhere on the home screen.

**Joseph confirms:** Widget tapped, observation spoken, row appeared in sheet. Proceed to Step 26.

---

## Step 26 — Hiking Observations: End-to-End Field Simulation

**Joseph does:** Simulate a hiking observation session:

1. Tap the **Log Observation** widget
2. Say: *"saguaro blooms are out on the south-facing slopes, first of the season"*
3. Open the Hiking Observations sheet — confirm row with:
   - Timestamp: current time in UTC
   - Observation: `saguaro blooms are out on the south-facing slopes, first of the season`
   - Categories: `["vegetation"]`
4. Tap the widget a second time
5. Say: *"coyote tracks crossing the wash near the boulder field, looks fresh"*
6. Confirm row with categories: `["wildlife","trail"]`

**Joseph confirms:** Both rows correct. CARD-0007 is done — move to Done in backlog.