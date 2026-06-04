# JCTsh Build Standards
**Author:** Joseph C Thomas (JCT)
**Purpose:** Defines the required build, integration, and documentation standards for all JCTsh smart home components. Claude Code consults this file before beginning any component build.
**Version:** 1.5
**Version description:** Added §5.4 Node-RED flow deployment patterns (MQTT v5 field issue, flows.json injection, Apps Script 405 redirect, alphanumeric API keys, env vars via EnvironmentFile), watchdog is a new Node-RED flow (not an existing process). Added SmartThings actual integration path (Node-RED → HA REST API → virtual switch). Added MQTT account creation as a required step. Added phone notification via HA companion app as watchdog alert method.
**Project:** JCTsh — Smart Home Automation
**Related files:** README.md, CLAUDE.md, JCTsh-Component-Planning-Pattern.md, JCTsh-Parts-Inventory.md

---

## How to Use This Document

These standards apply to every JCTsh component build. Claude Code must read this file at the start of every project and apply all relevant standards before producing any documentation, configuration, or code. Standards are not optional and are not subject to deferral unless explicitly overridden by the Claude Code instruction set for a specific project.

When a standard says "examine the existing pattern," Claude Code must locate and read the relevant existing component files before writing anything. Never invent a new convention when an existing one can be matched.

---

## 1. Physical Build Standards

### 1.1 Enclosure Convention

Open standoff mount is the **default first option** for ESP32 and small PCB projects. No enclosure panels. The perfboard is mounted using M3 brass male-female standoffs that space the board away from the mounting surface for cable clearance and serve as the attachment points.

Escalate to a more enclosed option only when:
- The component is installed outdoors or in a weather-exposed location → use a weatherproof project box
- The component requires a finished appearance outside the workshop → use a project box
- Dust accumulation becomes a documented problem → add an acrylic lid panel (cut to perfboard footprint, held by the same standoffs)

Never purchase or specify an enclosure without first confirming the open standoff mount is unsuitable for the specific installation context.

### 1.2 Breadboard vs. Perfboard

- **Breadboard:** prototyping and validation only. Never the final install.
- **Perfboard:** all permanent builds. Validate the full circuit on the breadboard before transferring to perfboard. Nothing gets soldered until breadboard validation is complete.
- **Perfboard size:** 5×7cm Chanzon FR4 boards are the standard for ESP32 DevKit projects.
- **Component socketing:** ESP32 DevKit plugs into two 19-pin female header strips soldered to the perfboard — not soldered directly. This keeps the ESP32 removable for replacement or reuse. Other modules use female header strips sized to their pin count.

### 1.3 Standoffs

M3 brass male-female standoffs are the standard mounting hardware. Check JCTsh-Parts-Inventory.md for available sizes before specifying. Default length: 10mm for perfboard-to-surface clearance.

### 1.4 Parts Inventory

Consult JCTsh-Parts-Inventory.md before adding any item to the BOM. Use on-hand parts before purchasing. Update the inventory update log at the end of every project.

---

## 2. ESP32 / ESPHome Standards

### 2.1 Platform

ESPHome is the required platform for all new ESP32 components. Arduino C++ is not used for new builds. Existing components built in Arduino C++ (e.g. salt sensor) are not required to migrate.

### 2.2 ESPHome Version

Verify ESPHome version before flashing. The native LD2412 component requires 2025.8.0 or later. Document the minimum required version in the component instruction set when a version dependency exists.

### 2.3 UART

Hardware UART only. Never use software UART (SoftwareSerial). On ESP32 DevKitC-32:
- UART0 (GPIO1/GPIO3) — used for USB, do not use for peripherals
- UART1 — may conflict with flash on some boards, avoid unless confirmed safe
- UART2 (GPIO16 RX / GPIO17 TX) — recommended for peripheral use

### 2.4 Credentials

All WiFi credentials and MQTT broker addresses must use `!secret` references in ESPHome YAML. Never hardcode credentials. Secrets stored in `components/<name>/secrets.yaml` (gitignored).

### 2.5 Firmware Updates

First flash via USB. All subsequent updates via ESPHome OTA. Document the OTA update command in the component flashing.md.

### 2.6 GPIO Assignment

Before assigning GPIOs, exclude the following on ESP32 DevKitC-32 38-pin:
- GPIO0 — boot mode, avoid
- GPIO1, GPIO3 — UART0 / USB
- GPIO6–11 — internal flash, never use
- GPIO34, GPIO35, GPIO36, GPIO39 — input only, cannot drive output

Document all GPIO assignments in the Hardware Context table of the instruction set. Note the pin label orientation issue: ESP32 DevKit pin labels face down when inserted in a breadboard. Mark key GPIO rows with masking tape before wiring. A pinout PNG should be placed in the component directory for reference.

### 2.7 ESPHome MQTT Publishing Patterns

These patterns are derived from garage-radar and front-porch-temp-sensor — the two reference implementations. Always diff one of those YAMLs before writing MQTT publish code in a new component.

**Rule: never use `id(mqtt_client).publish()` inside a raw lambda for anything other than the SPIFFS replay loop (see §2.10).** Use native `mqtt.publish` actions instead. Raw lambda publishes in `on_connect` are silently dropped before the broker session is fully ready. Native actions are queued correctly by ESPHome.

**`on_connect` pattern:**
```yaml
on_connect:
  - delay: 500ms
  - mqtt.publish:
      topic: jctsh/<type>/<component>/log
      payload: !lambda |-
        char buf[256];
        snprintf(buf, sizeof(buf),
          "{\"component\":\"<name>\",\"category\":\"System\","
          "\"message\":\"<Name> online - ESPHome " ESPHOME_VERSION ", IP: %s\"}",
          id(wifi_ip).state.c_str());
        return std::string(buf);
  - mqtt.publish:
      topic: jctsh/<type>/<component>/log
      payload: '{"component":"<name>","category":"MQTT","message":"MQTT connected"}'
```

The `delay: 500ms` gives the broker session time to fully settle before publishing. The `wifi_info` text sensor (`id: wifi_ip`, `internal: true`) must be declared for the IP lambda.

**Heartbeat pattern (home-mode-only guard):**

For components that have a field mode (no WiFi), wrap heartbeat publishes in a `condition` so they are suppressed when MQTT is not connected:
```yaml
- interval: 5min
  then:
    - if:
        condition:
          lambda: 'return id(mqtt_client).is_connected();'
        then:
          - mqtt.publish:
              topic: jctsh/<type>/<component>/log
              payload: !lambda |-
                # ... build heartbeat log message ...
                return std::string(buf);
          - mqtt.publish:
              topic: jctsh/<type>/<component>/heartbeat
              payload: !lambda |-
                # ... build heartbeat payload ...
                return std::string(buf);
```

For components that are always home (garage-radar, front-porch), the `if` guard is not needed — the interval fires without a condition check. The `mqtt_client` `id:` must be declared on the `mqtt:` component block for `is_connected()` to be callable.

**Reference implementations:** `components/garage-radar/garage-radar.yaml`, `components/front-porch-temp-sensor/front-porch-temp-sensor.yaml`

---

### 2.8 ESPHome Component Boilerplate

Every new ESPHome component uses this exact boilerplate. Do not deviate without a documented reason.

**Board and framework:**
```yaml
esp32:
  board: esp32dev
  framework:
    type: arduino
```

**Logger:** Always `INFO`. Debug and verbose levels produce excessive serial output that obscures real issues.
```yaml
logger:
  level: INFO
```

**captive_portal:** Always include. Allows browser-based recovery when WiFi credentials are wrong.
```yaml
captive_portal:
```

**WiFi AP fallback:** Name the fallback AP `<component-name>-fallback`. Makes it identifiable on the network if the device can't reach JCTnet1.
```yaml
wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password
  ap:
    ssid: "<component-name>-fallback"
    password: !secret ap_password
```

**Component naming:** The ESPHome `name:` field determines the device hostname (`<name>.local`) and the ESPHome auto-generated MQTT sub-topics. It must match the component name used in the MQTT topic prefix. All three must be consistent:
- `esphome: name: hiking-monitor` → hostname `hiking-monitor.local`
- `mqtt: topic_prefix: jctsh/components/hiking-monitor`
- Log messages: `"component": "hiking-monitor"`

**Flash path:** ESPHome must be run from `C:\esphome\<component-name>\`. Spaces in `JCT Documents` break the ESP-IDF compiler mid-build with no useful error. Copy `<name>.yaml`, `secrets.yaml`, and any custom headers to that directory before every flash. Do not run `esphome` from inside the repo path.

---

### 2.9 Sensor Coding Standards

**NaN guards:** Always check `isnan()` before using sensor values in lambdas. BME280, LTR-390, and other I2C sensors return NaN on the first read cycle while they initialize. Publishing NaN produces malformed JSON and can crash the log server parser.

```cpp
float temp = id(bme_temp).state;
if (isnan(temp)) {
  // skip or use fallback
}
```

**Standard I2C pins:** Use GPIO21 (SDA) and GPIO22 (SCL) for all I2C buses. This is the consistent choice across all JCTsh I2C components. Only deviate if a GPIO conflict forces it, and document the reason.

**Internal sensors:** Mark housekeeping sensors `internal: true` to suppress automatic MQTT publishing. These sensors are used in lambdas only — their values should not appear as independent MQTT topics.

```yaml
- platform: uptime
  id: uptime_sec
  internal: true

- platform: wifi_signal
  id: wifi_rssi
  internal: true
  update_interval: 60s

# Required for IP address in on_connect message:
text_sensor:
  - platform: wifi_info
    ip_address:
      id: wifi_ip
      internal: true
```

All three of these sensors are required in every component that publishes a heartbeat or an on_connect log message.

---

### 2.10 Onboard Flash Logging (Field Mode)

For components that log sensor readings to flash when WiFi is unavailable, use **ESP-IDF native SPIFFS VFS** (`esp_spiffs.h`), not the Arduino LittleFS library (`LittleFS.h`).

**Why SPIFFS, not LittleFS:**
- SPIFFS is bundled with the ESP-IDF — no external library declaration or download needed
- LittleFS offers better wear-leveling and directory support, but neither matters for this use case (sequential append and read of a single `.jsonl` file)
- SPIFFS mounts reliably under the ESPHome Arduino framework and supports standard POSIX file I/O (`fopen`, `fprintf`, `fgets`, `remove`)

**Implementation pattern** (`hiking_logger.h` is the reference):
```cpp
#include <esp_spiffs.h>

esp_vfs_spiffs_conf_t conf = {
  .base_path              = "/spiffs",
  .partition_label        = NULL,   // first SPIFFS partition
  .max_files              = 5,
  .format_if_mount_failed = true,   // auto-format on first use
};
esp_vfs_spiffs_register(&conf);
```

Log file path: `/spiffs/<component>_log.jsonl` (JSON Lines — one payload object per line).

**Capacity:** The default ESPHome ESP32 partition table allocates ~1.47 MB to SPIFFS. At ~200 bytes per reading and a 2-minute interval, a 6-hour hike produces ~180 readings (~36 KB) — well within limits.

**Naming:** Name the custom header and documentation files by their function, not by the library. Use `<component>_logger.h` and `<component>-logger.md`, not `littlefs_logger.h` or `spiffs_logger.h`. The library choice is an implementation detail.

**Reference implementation:** `components/hiking-sensor/hiking_logger.h` — see `components/hiking-sensor/hiking-logger.md` for a complete description of the API, operating modes, replay flow, capacity, and troubleshooting.

---

### 2.11 MQTT Account Creation

Every new ESP32 component requires its own dedicated Mosquitto account. Create it before first flash:

```bash
sudo mosquitto_passwd -b /etc/mosquitto/passwd <component-name> <password>
sudo chown root:mosquitto /etc/mosquitto/passwd
sudo systemctl restart mosquitto
```

**Critical:** `sudo mosquitto_passwd` resets `/etc/mosquitto/passwd` group to `root`. Always run the `chown` command immediately after any password change or Mosquitto will fail to read the file.

Store the password in `components/<name>/secrets.yaml` (gitignored). Add the account name to the credentials table in CLAUDE.md.

---

## 3. MQTT Standards

### 3.1 Topic Naming Convention

```
jctsh/<type>/<component>/<message-type>
```

Examples:
- `jctsh/components/garage-radar/state` — primary state
- `jctsh/components/garage-radar/log` — log messages (routed to Python log server by Node-RED)
- `jctsh/components/garage-radar/heartbeat` — 5-minute heartbeat (monitored by Node-RED watchdog)
- `jctsh/sensors/salt-sensor/data` — sensor readings

### 3.2 Standard Sub-Topics

For ESP32 components, the following sub-topics are standard:
- `/state` — primary on/off or presence state
- `/log` — all log messages in standard JSON format (see Section 4.2)
- `/heartbeat` — 5-minute heartbeat in standard JSON format (see Section 4.1)
- Additional sub-topics named for the specific sensor value (e.g. `/still`, `/moving`, `/distance`, `/level`)

### 3.3 Broker

Mosquitto broker on `raspberrypi.local`, port 1883. Fixed IP: `192.168.1.117` (use if `.local` resolution fails). Tailscale IP: `100.70.162.24` (use for remote access). Reference by hostname in configuration files.

### 3.4 Will Message

Every ESP32 component configures an MQTT Last Will and Testament (LWT). The broker publishes it automatically when the device disconnects unexpectedly. This is how `"MQTT disconnected"` appears in the log dashboard without the device sending it.

Required pattern — no deviations:
```yaml
will_message:
  topic: jctsh/<type>/<component>/log
  payload: '{"component":"<name>","category":"MQTT","message":"MQTT disconnected"}'
  retain: false
  qos: 0
```

`retain: false` is critical. A retained will message would re-appear in the log every time a new subscriber connects to the broker, producing phantom "disconnected" entries long after the device is back online.

### 3.5 MQTT Discovery

Set `discovery:` based on whether the component has Home Assistant integration:

| HA integration? | Setting |
|---|---|
| Yes (entities visible in HA) | `discovery: true` + `discovery_prefix: homeassistant` |
| No (MQTT only, no HA entities) | `discovery: false` |

Do not leave `discovery:` at its ESPHome default (`true`) for components that have no HA integration. Auto-discovery would create unwanted HA entities for every sensor value the device publishes.

---

## 4. Observability Standards

Observability is **not optional**. Every ESP32 component implements message logging and heartbeat, and is registered with the Node-RED watchdog flow. These are required in the initial build — not features to be added later.

### 4.1 Heartbeat

All ESP32 components publish a heartbeat every **5 minutes** to two topics:

> **Note:** garage-radar and front-porch-temp-sensor currently use a 30-minute interval — they predate this standard. New components use 5 minutes per this standard. The hiking-monitor is the first component built to the 5-minute standard.

**Log topic** (visible in dashboard):
```
topic: jctsh/<type>/<component>/log
payload: { "component": "<name>", "category": "System", "message": "Heartbeat - uptime: Xh Xm, RSSI: -XXdBm, <state-key>: <value>" }
```

**Heartbeat topic** (monitored by Node-RED watchdog):
```
topic: jctsh/<type>/<component>/heartbeat
payload: { "component": "<name>", "uptime": "Xh Xm", "rssi": -XX, "<state-key>": "<value>" }
```

Both are published on the same 5-minute interval. The log topic entry makes the heartbeat visible in the dashboard. The heartbeat topic is what the Node-RED watchdog monitors.

> **Critical:** The log topic heartbeat message **must begin with `"Heartbeat - "`** (with a space and hyphen). The log server uses this prefix to collapse consecutive same-state heartbeats into a single dashboard row showing count and time range. Any other prefix causes each heartbeat to appear as a separate row, filling the dashboard with noise.

### 4.2 Log Message Format

All log messages are published as JSON to `jctsh/<type>/<component>/log`. Node-RED subscribes to this topic and routes messages to the Python log server at `http://raspberrypi.local/`.

**Required format:**
```json
{ "component": "<name>", "category": "<category>", "message": "<text>" }
```

**Valid categories:** `MQTT`, `System`, `Sensor`, `Alert`, `Test`

**Do not include timestamps** — the log server adds them on receipt.

### 4.3 Standard Log Events

Every ESP32 component logs the following events:

| Event | Category | Message format |
|---|---|---|
| Boot | System | `<Component name> online - ESPHome vX.X.X, IP: x.x.x.x` |
| MQTT connected | MQTT | `MQTT connected` |
| MQTT disconnected | MQTT | `MQTT disconnected` (sent by broker as LWT — not by device) |
| Primary state ON | Sensor | `<State name> detected - <key>: ON (<detail>)` |
| Primary state OFF | Sensor | `<State name> cleared - <key>: OFF, timeout elapsed` |
| Heartbeat | System | `Heartbeat - uptime: Xh Xm, RSSI: -XXdBm, <state-key>: <value>` |
| OTA started | System | Handled natively by ESPHome |
| OTA completed | System | Handled natively by ESPHome |

### 4.4 Node-RED Watchdog Flow

The JCTsh watchdog is a Node-RED flow that monitors the heartbeat topic of each registered ESP32 component. It alerts Joseph via the Home Assistant companion app on his Pixel 10 Pro if a component goes silent.

**This is a JCTsh infrastructure component**, first built as part of the garage-radar project. It lives at `core/node-red/watchdog.flow.json`.

**How it works:**
- Subscribes to `jctsh/+/+/heartbeat` (wildcard — catches all component heartbeats)
- On each received heartbeat, resets a per-component timer
- If a timer expires (no heartbeat received within 10 minutes for a 5-minute interval), fires an alert
- Alert path: Node-RED → HA REST API (port 8123) → HA companion app → Joseph's Pixel 10 Pro
- Alert message format: `JCTsh alert: <component-name> has not reported in <N> minutes`

**When adding a new component:**
- No registration step required — the wildcard subscription catches all `/heartbeat` topics automatically
- Confirm the new component's heartbeat topic matches `jctsh/<type>/<name>/heartbeat`
- Confirm the heartbeat is publishing before considering observability complete

**Salt sensor retrofit:** The salt sensor (Arduino C++) will need a heartbeat added to its sketch to benefit from the watchdog. This is a separate future task — do not block new components on it.

### 4.5 Message Logging Integration

Node-RED already subscribes to `jctsh/+/+/log` (wildcard) and routes all matching messages to the Python log server. No per-component Node-RED changes are needed for logging — publish to the `/log` topic in the correct JSON format and it appears in the dashboard automatically.

Verify logging is working by checking `http://raspberrypi.local/` (Basic Auth, user: `jctsh`) after first flash.

---

## 5. SmartThings Integration Standards

Every JCTsh component that produces actionable state is exposed in SmartThings. Determine the SmartThings device type during Phase 3 — not deferred.

### 5.1 Device Type Selection

| Use case | SmartThings device type | Notes |
|---|---|---|
| Presence / occupancy (is someone there?) | Motion Sensor | Active/Inactive — most natural fit for room presence |
| Simple on/off state consistent with existing virtual switches | Virtual Switch | On/Off — use when consistency with existing components matters |
| Door, window, or physical open/close state | Contact Sensor | Open/Closed |
| Person associated with a location (arrival/departure) | Presence Sensor | Present/Not Present — for person-tracking, not room sensors |
| Environmental reading (temp, humidity, level) | Use appropriate SmartThings capability | Match to the sensor type |

### 5.2 Integration Path

The only integration path to SmartThings is via Home Assistant:

```
Node-RED → HA REST API (port 8123) → SmartThings integration → SmartThings device
```

There is no direct MQTT-to-SmartThings path. Do not attempt to create one.

**Pattern:**
1. Create a virtual switch (or appropriate device type) in SmartThings
2. Expose it as an HA entity — HA syncs it to SmartThings automatically
3. Control it from Node-RED via the HA REST API

**Reference implementation:** The salt sensor switches (`switch.salt_critical_alert`, `switch.salt_low_alert`, etc.) are the established pattern. Examine `components/salt-sensor/` before writing any new SmartThings integration.

### 5.3 HA REST API

Node-RED calls HA at `http://raspberrypi.local:8123/`. The HA long-lived access token is stored in Node-RED credentials (not in source control). Do not hardcode the token.

---

## 5.4 Node-RED Flow Deployment Patterns

Lessons from the hiking-monitor environmental data pipeline (2026-06-04):

**Do not inject flows directly into `flows.json` via Python/SSH.** The correct method is Node-RED UI → Import → Clipboard. Direct injection has subtle failure modes that the UI avoids.

**Every node must have a `z` property pointing to a tab node.** Nodes without `z` are orphaned — they load silently but never execute. Always include a `type: "tab"` node in the flow JSON and set `z` on every other node to match its `id`.

**MQTT v5 fields silently break MQTT v3 brokers.** The JCTsh broker runs MQTT v3.1.1 (`protocolVersion: 4`). Node-RED v4 UI imports add MQTT v5 fields to MQTT In and Out nodes that are not present in existing working nodes:
- MQTT In: `nl` (No Local), `rap` (Retain As Published) — causes subscription to silently fail
- MQTT Out: `respTopic`, `contentType`, `userProps`, `correl`, `expiry` — causes publish to silently fail

After any UI import of MQTT nodes, verify these fields are absent. The working reference nodes (`mqtt_in_reading`, `mqtt_out_log`, etc.) have only: `id`, `type`, `z`, `name`, `topic`, `qos`, `retain` (out only), `broker`, `wires`.

**Google Apps Script returns 405 on redirect — treat it as success.** When Node-RED POSTs to an Apps Script web app URL, Google executes the script and appends the row, then returns a 302 redirect. Node-RED follows the redirect with POST; the redirect destination returns 405 (Method Not Allowed). The row WAS appended. The check response function must treat `statusCode === 405` as success, not as an error.

**Apps Script API keys must be alphanumeric.** Special characters (`&`, `@`, `*`) in URL query parameters break parsing even with `encodeURIComponent`. Generate keys using only `[a-zA-Z0-9]`.

**Node-RED env vars via systemd EnvironmentFile.** The Node-RED service on the Pi reads `/home/pi/.node-red/environment` via `EnvironmentFile=` in the systemd unit. Add `KEY=value` lines to this file for secrets passed to function nodes via `env.get('KEY')`. Restart Node-RED after editing.

---

## 6. Integration Standards

### 6.1 Additive First

New components are additive by default. Existing inputs, automations, and integrations are never removed or modified without an explicit decision documented in the instruction set. When integrating a new component alongside existing ones, wire it in parallel — do not replace.

### 6.2 Timeout and Timer Logic

Document where timeout/timer logic lives for every component. The three options are:

- **ESPHome** — sensor-level smoothing (short timeouts, e.g. 30 seconds). Changes require a firmware reflash.
- **Node-RED** — flow-level logic. Changes made in Node-RED UI without reflashing.
- **Home Assistant** — automation-level logic. Changes made in HA UI without reflashing.

When both a short smoothing timeout (ESPHome) and a longer presence timeout (HA or Node-RED) exist, document both with their distinct purposes so they are not confused.

### 6.3 Existing Pattern Investigation

Before writing any integration code that touches an existing process (logging, presence automation, HA-SmartThings bridge, Node-RED flows), Claude Code must examine the existing implementation first. Never assume — always verify. Read the relevant flow JSON, YAML, or source file before writing new code.

---

## 7. Documentation Standards

### 7.1 Required Documents per Component

Every completed component must have the following in `components/<name>/`:

| Document | Purpose |
|---|---|
| `README.md` | Permanent component reference — what it does, hardware, wiring, MQTT topics, integration, known behaviors, tuning notes |
| `<name>.yaml` or equivalent | ESPHome YAML or source code — the actual implementation |
| `wiring.md` | Pin-by-pin wiring reference including connection table and breadboard layout |
| `flashing.md` | Flash and OTA update instructions |
| `testing.md` | Sensor validation and enhancement validation procedures |
| `perfboard-layout.md` | Permanent build layout, soldering sequence, continuity check procedure |
| `mounting.md` | Physical installation guide |
| `integration.md` | Integration instructions for Node-RED, HA, and SmartThings |
| `integration-notes.md` | Findings from investigating existing logging, watchdog, presence automation, and SmartThings bridge patterns |
| `end-to-end-test.md` | Full system validation procedure |
| Pinout PNG | ESP32 DevKit pinout reference image |

### 7.2 Top-Level README

Update the top-level `README.md` Components list when a new component is completed.

### 7.3 CLAUDE.md Credentials Table

Add the new component's MQTT account to the credentials table in root `CLAUDE.md` when the account is created.

### 7.4 Parts Inventory Update

Add an entry to JCTsh-Parts-Inventory.md inventory update log when a project is completed. Record all tracked parts consumed.

### 7.5 Documentation Captures Reality

Instructions are updated with actual findings during the build, not just intentions. The repo reflects what was actually built. Deviations from the plan are documented immediately when discovered.

---

## 8. LED Indicator Standards

When LED indicators are included in a component:

- **Green LED** — primary positive state (presence detected, sensor active, connection established)
- **Yellow LED** — secondary or downstream state (virtual switch status, integration state)
- **Red LED** — fault, error, or disconnected state (reserved for future use)
- **Current-limiting resistor:** 330Ω for standard 5mm LEDs at 3.3V (~6-7mA)
- **GPIO selection:** avoid GPIO0 (boot), GPIO2 (onboard LED), and any GPIO already allocated to a peripheral

---

## Standards Version History

| Version | Change |
|---|---|
| 1.0 | Initial release. Enclosure convention, ESP32/ESPHome standards, MQTT conventions, observability standards, SmartThings integration, LED standards, documentation standards. |
| 1.4 | Added §2.10 onboard flash logging standard: use ESP-IDF SPIFFS not Arduino LittleFS; name files by function not library. Fixed §2.7 reference from "LittleFS replay loop" to "SPIFFS replay loop". Renumbered MQTT account creation to §2.11. |
| 1.3 | Added §2.8 ESPHome component boilerplate (board, framework, logger, captive_portal, WiFi AP fallback naming, component naming consistency, flash path). Added §2.9 sensor coding standards (NaN guards, standard I2C pins GPIO21/22, internal: true housekeeping sensors). Added §3.4 will_message pattern (retain: false critical). Added §3.5 MQTT discovery rule. Fixed §4.1 heartbeat message format and added "Heartbeat - " prefix requirement. Fixed §4.3 log event message formats (hyphen throughout, removed MQTT reconnected event, clarified LWT). |
| 1.2 | Added §2.7 ESPHome MQTT publishing patterns (on_connect and heartbeat). Fixed §4.3 online message format (hyphen not em dash). Added §4.1 note on heartbeat interval discrepancy between standard (5 min) and existing components (30 min). Renumbered MQTT account creation to §2.8/§2.10. |
| 1.1 | Corrected observability section: log format is JSON to /log topic routed by Node-RED (not a separate process to examine). Watchdog is a new Node-RED flow built as part of garage-radar project, not an existing process. Added actual SmartThings integration path (Node-RED → HA REST API → virtual switch). Added MQTT account creation procedure (Section 2.7) including Mosquitto passwd ownership gotcha. Added phone notification via HA companion app as watchdog alert method. Added CLAUDE.md credentials table update to documentation standards. |
