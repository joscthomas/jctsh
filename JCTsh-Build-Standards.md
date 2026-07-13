# JCTsh Build Standards
**Author:** Joseph C Thomas (JCT)
**Purpose:** Defines the required build, integration, and documentation standards for all JCTsh smart home components. Claude Code consults this file before beginning any component build.
**Version:** 1.15
**Version description:** Added §1.2 pin-verification guidance — harvested from salt-sensor's CARD-0049 perfboard build: identify pins by printed silkscreen label rather than a documented reference table's position numbers (different board brands/clones can have different physical pin order despite the same GPIO count), and add isolation checks between visually-adjacent pin labels to Pre-Power Checks, not just intentional-net continuity checks.
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
- **Identify pins by their printed silkscreen label, not a documented reference table's position numbers.** Different ESP32 board brands/clones (e.g. a generic "38-pin ESP32 DevKitC-32" vs. a SparkleIoT XH-32S) can have completely different physical pin *order* despite the same GPIO count and nominal form factor. A documented per-component pin table (like an `ESP32-project-pins.md`) is only as good as the specific physical board it was written against — verify against the actual board's printed labels before soldering or probing, every time, even if a table already exists. Established after `salt-sensor`'s CARD-0049 perfboard build found its documented pin table didn't match the actual board in hand.
- **Add isolation checks between visually-adjacent pin labels to Pre-Power Checks**, not just intentional-net continuity checks. Dense silkscreens put unrelated pins (e.g. `D5`/`TX2`/`RX2`) right next to each other, and it's easy to solder to the wrong one while reading quickly — this is exactly what happened on `salt-sensor`'s build (Trig landed on `RX2` instead of `D5`), caught only because Pre-Power Checks were done by reading labels rather than trusting the (wrong) documented position. For any pin sitting near a similarly-named or visually-adjacent label, add an explicit "should be OL/open, not beep" check between the two, alongside the normal intended-net checks.

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
- interval: 30min
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

**Exception — deep sleep components:** Do NOT include `captive_portal:` when the component uses `deep_sleep:`. ESPHome's captive portal calls `App.prevent_deep_sleep()` internally, which permanently blocks sleep entry for the entire boot cycle. Omit `captive_portal:` and add a YAML comment documenting why:
```yaml
# captive_portal removed — calls App.prevent_deep_sleep() and blocks deep sleep entry
```

**WiFi AP fallback:** Name the fallback AP `<component-name>-fallback`. Makes it identifiable on the network if the device can't reach JCTnet1.

**Single-network (home-only components):**
```yaml
wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password
  ap:
    ssid: "<component-name>-fallback"
    password: !secret ap_password
```

**Multi-network variant (portable components — home WiFi + cellular hotspot):** Use the `networks:` list syntax. ESPHome tries networks in list order at boot — put home WiFi first so it takes priority when at home:
```yaml
wifi:
  networks:
    - ssid: !secret wifi_ssid
      password: !secret wifi_password
    - ssid: !secret hotspot_ssid
      password: !secret hotspot_password
  ap:
    ssid: "<component-name>-fallback"
    password: !secret ap_password
```

Add `hotspot_ssid` and `hotspot_password` to `secrets.yaml` and `secrets.yaml.template` when using this variant. The hotspot SSID and password are fixed at flash time — changing them after flashing requires a re-flash.

**Hotspot SSID naming:** Use a device-independent name (e.g., `JCT Hotspot`) rather than a phone model name (e.g., `JCT Pixel 10 Pro XL`). A device-independent name means any phone can serve as the hotspot by matching the SSID and password — no re-flash needed to switch devices.

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

### 2.12 E-ink Display Pattern

For components with an e-ink display, three rules apply:

**1. Set `update_interval: never`.** E-ink full refresh takes ~2 seconds. Letting it fire on every sensor update cycle produces constant flicker and wear. Drive it explicitly instead:
```yaml
display:
  - platform: waveshare_epaper
    update_interval: never
    full_update_every: 1
```

**2. Use a `deep_sleep_pending` global to render a shutdown screen before sleep.** The display retains its last image with power off — make it show the right thing. Set the flag, update the display, then sleep:
```yaml
globals:
  - id: deep_sleep_pending
    type: bool
    restore_value: false
    initial_value: 'false'
```
Pre-sleep sequence (in `on_connect`, `on_state`, etc.):
```yaml
- lambda: 'id(deep_sleep_pending) = true;'
- component.update: <display_id>
- deep_sleep.allow: <sleep_id>
- deep_sleep.enter: <sleep_id>
```
The display lambda checks `id(deep_sleep_pending)` first and renders a shutdown layout if true.

**3. The display lambda must handle NaN during the first read cycle.** I2C sensors return NaN while they initialize. Render an "initializing" fallback rather than printing garbage or crashing:
```cpp
if (isnan(temp) || isnan(hum) || isnan(uv)) {
  it.print(5, 10, id(font_data), "<Component name>");
  it.print(5, 72, id(font_data), "initializing");
} else {
  // normal display
}
```

**Reference implementation:** `components/hiking-sensor/hiking-sensor.yaml` display block.

---

### 2.13 Multi-priority `on_boot` Sequencing

When boot requires ordered phases with dependencies, use multiple `on_boot:` blocks with different priority values. ESPHome runs higher priorities first:

| Priority | Use |
|---|---|
| `600.0` | Early hardware setup — fires before component initialization. Use for SPIFFS mount, hardware reset, or anything that must happen before sensors start. |
| `-100.0` | First sensor reads and display update — sensors are initialized and ready. |
| `-200.0` | Conditional sleep entry — must run last so all other boot actions complete first. |

```yaml
on_boot:
  - priority: 600.0
    then:
      - lambda: 'hike_log_begin();'   # SPIFFS must mount before any sensor cycle
  - priority: -100.0
    then:
      - component.update: my_sensor   # first read on boot
      - component.update: my_display
  - priority: -200.0
    then:
      - if:
          condition:
            and:
              - binary_sensor.is_off: mode_switch
              - binary_sensor.is_off: dock_detect
          then:
            - deep_sleep.allow: deep_sleep_control
            - deep_sleep.enter: deep_sleep_control
```

Negative priorities run after all components are initialized. Any `on_boot` action that reads sensor values, updates a display, or enters sleep must use a negative priority.

**Reference implementation:** `components/hiking-sensor/hiking-sensor.yaml` `on_boot:` block (priorities 600.0, -100.0, -200.0).

---

### 2.14 Battery-Powered Component Safety Standards

Required for every component powered by a rechargeable LiPo/Li-ion cell — applied during initial build, never deferred as a future enhancement. Established after the hiking-monitor's original battery failed on its first field trip (2026-07-03) with no advance warning.

**1. Cell selection — built-in PCM protection required.** Only use cells with a Protection Circuit Module (PCM) covering overcharge, over-discharge, overcurrent, and short-circuit. Confirm this from the listing/datasheet before purchase and note it in `JCTsh-Parts-Inventory.md`. Reject bare/unprotected cells. Reference: the EEMB 603449 line in stock is PCM-protected and UN 38.3 compliant — confirmed via manufacturer documentation, not assumed.

**2. Firmware low-battery cutoff required.** Watch the battery voltage sensor. Below a safe threshold (3.4V for single-cell LiPo — leaves margin above the cell's own PCM trip point and above boost-converter end-of-charge instability), force deep sleep regardless of any mode switch, and render a persistent on-screen warning if a display is present (e-ink holds the frame with zero power). Also check at boot, so waking a critically-low device shows the warning and safely re-sleeps instead of attempting normal operation. This layer exists to act *before* the cell's PCM has to trip — it gives an early, visible warning instead of a silent hard stop. Reference: `components/hiking-sensor/hiking-sensor.yaml` (`low_battery_shutdown` script).

**3. Charging safety.**
- Charge inside a fireproof LiPo charging bag (silicone-coated fiberglass, ~$10-15) — required, not optional, regardless of cell quality or PCM protection.
- Set the bag on a heat-insulating, non-combustible surface — concrete/masonry floor, ceramic tile, cement board, or a metal tray lined with sand/kitty litter. Never place it on bare sheet metal on a wooden workbench: metal conducts heat rather than blocking it, and a thermal runaway event (600°C+, sustained for several minutes) will carry straight through thin metal and scorch or ignite the wood underneath.
- Never charge unattended for extended periods (e.g. leaving to charge overnight unsupervised).
- Never charge a cell that reads 0V, shows swelling/puffiness, feels hot, or has any chemical smell. Treat as damaged and retire it — do not attempt to revive it. (This is exactly what happened with the original hiking-monitor cell.)

**4. Storage.** Cells not in active use should be stored at 40–60% charge, not full or empty. Recheck/recharge to that range roughly every 3 months during long storage — fully depleted long-term storage degrades cells even with PCM protection.

**5. Disposal.** Tape over the JST terminals before discarding a retired cell (prevents short-circuit in a bin/drawer). Recycle at a battery drop-off (Home Depot, Lowe's, Batteries Plus, etc.) — never in household trash.

**6. Connector polarity.** Verify polarity with a multimeter before the first connection of any new battery/module pairing — do not assume color convention (red = positive is common but not guaranteed on every module).

**7. Power architecture — prefer direct LiPo-to-LDO over boost-then-buck (recommended default for new builds, not a retrofit requirement).** A boost converter that steps the LiPo's native 3.0–4.2V up to ~5V, followed by the microcontroller's onboard regulator stepping it back down to 3.3V, is two conversions in opposite directions — wasted efficiency, and each stage draws its own idle current even while "asleep." Since the ESP32 and most peripherals (BME280, LTR-390, e-ink, etc.) run natively on 3.3V, default new battery-powered builds to a single low-quiescent-current LDO taking the LiPo directly to 3.3V (Adafruit Feather-style), skipping the boost stage entirely. This also removes the boost converter's end-of-charge "voltage cliff" instability — a contributing factor in the hiking-monitor's original battery incident. Only use a boost converter when a specific peripheral requires 5V. Not applied retroactively to hiking-monitor's existing perfboard — apply to the next new battery-powered component.

**8. [CANDIDATE — not yet required, pending validation] GPIO-controlled power gating for I2C/SPI peripherals during sleep.** Observed 2026-07-03: ESP32 deep sleep only stops the CPU from executing — it does not cut power to anything downstream. With no gating in place, I2C/SPI peripherals (BME280, LTR-390, etc.) stay fully powered and drawing their own operating current for the entire "sleep" duration, on top of any boost-converter quiescent draw (see point 7). Confirmed visually on hiking-monitor: the ESP32's and LTR-390's power-indicator LEDs stayed lit after the device entered deep sleep. Candidate fix: a P-FET (or similar high-side load switch) in-line on the 3.3V rail between the microcontroller's own 3.3V output and the peripherals — not between the boost module and the microcontroller's `VIN`, since the microcontroller must stay powered to control the gate signal — gated by a spare GPIO, cutting peripheral power during sleep and re-enabling it on wake. **Not promoted to a required standard yet** — this needs to be built and measured (see `components/hiking-sensor` backlog CARD-0026, CARD-0027) before it's confirmed worth the added complexity for future builds. Revisit this entry once validated.

---

## 3. MQTT Standards

### 3.1 Topic Naming Convention

```
jctsh/<type>/<component>/<message-type>
```

Examples:
- `jctsh/components/garage-radar/state` — primary state
- `jctsh/components/garage-radar/log` — log messages (routed to Python log server by Node-RED)
- `jctsh/components/garage-radar/heartbeat` — 30-minute heartbeat (monitored by Node-RED watchdog)
- `jctsh/sensors/salt-sensor/data` — sensor readings

### 3.2 Standard Sub-Topics

For ESP32 components, the following sub-topics are standard:
- `/state` — primary on/off or presence state
- `/log` — all log messages in standard JSON format (see Section 4.2)
- `/heartbeat` — 30-minute heartbeat in standard JSON format (see Section 4.1)
- Additional sub-topics named for the specific sensor value (e.g. `/still`, `/moving`, `/distance`, `/level`)

### 3.3 Broker

Mosquitto broker on `raspberrypi.local`, port 1883. Fixed IP: `192.168.1.117` (use if `.local` resolution fails). Tailscale IP: `100.70.162.24` (use for remote access). Reference by hostname in configuration files.

**For components that connect from outside the home network** (e.g., via a cellular hotspot): use `jctsh.duckdns.org` as `mqtt_broker` in `secrets.yaml`. `raspberrypi.local` is mDNS link-local and unreachable from cellular; `192.168.1.117` and `100.70.162.24` are likewise unreachable from cellular. DuckDNS + router port forward (port 1883 → 192.168.1.117) is the only path. See `core/mqtt/monitoring.md` for the full infrastructure setup and layer-by-layer monitoring commands.

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

### 3.6 Field-mode Sentinel — `rssi_dbm: 0`

For portable environmental sensors that log readings to SPIFFS when WiFi is unavailable, include `rssi_dbm` in every data payload:

- When MQTT-connected: set to the actual WiFi RSSI (negative integer, e.g. `-45`)
- When logging to SPIFFS in field mode (no WiFi): set to `0`

```cpp
int rssi = id(mqtt_client).is_connected() ? (int)id(wifi_rssi).state : 0;
// include rssi in the JSON payload
```

This convention lets downstream processors distinguish reading types:
- `rssi_dbm == 0` → field-mode reading; `ts` is the actual hike timestamp
- `rssi_dbm != 0` → home-mode reading; `ts` is live capture or replay-upload time

Node-RED can detect field session boundaries using the `rssi_dbm` transition: nonzero → zero = field session started; zero → nonzero = field session ended. The `lastTs` at the transition is the precise start/end timestamp from the sensor payload.

**Reference implementation:** `components/hiking-sensor/hiking-hike-events.flow.json` (`Detect field session start / end` function node).

---

## 4. Observability Standards

Observability is **not optional**. Every ESP32 component implements message logging and heartbeat, and is registered with the Node-RED watchdog flow. These are required in the initial build — not features to be added later.

### 4.1 Heartbeat

All ESP32 components publish a heartbeat every **30 minutes** to two topics:

> **Rationale:** The Node-RED watchdog timeout is 35 minutes (30-minute interval + 5-minute buffer). 30 minutes is the standard because it is derived from the watchdog — not arbitrary. Battery-powered components may use a longer interval; document the reason and accept that the watchdog may not catch them reliably.

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

Both are published on the same 30-minute interval. The log topic entry makes the heartbeat visible in the dashboard. The heartbeat topic is what the Node-RED watchdog monitors.

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
- If a timer expires (no heartbeat received within 35 minutes for a 30-minute interval), fires an alert
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

### 4.6 Sensor Health Detection

ESPHome components with **I2C or SPI sensors** must publish explicit error log messages when a sensor read fails (returns NaN). This makes hardware faults visible in the dashboard instead of silently showing stale retained MQTT values in HA.

**When to apply:** Any component where a physical sensor failure would cause `sensor.state` to return NaN — typically BME280, BH1750, LTR390, and similar I2C/SPI sensor platforms.

**Pattern:** Add one `if` block per sensor at the end of the 30-minute heartbeat interval, after the heartbeat publishes:

```yaml
      - if:
          condition:
            lambda: 'return isnan(id(<sensor_id>).state);'
          then:
            - mqtt.publish:
                topic: jctsh/<type>/<component>/log
                payload: '{"component":"<name>","category":"Sensor","message":"<SensorName> read failed — check I2C wiring (SDA GPIO<X> / SCL GPIO<Y>)"}'
```

**Reference implementation:** `components/front-porch-temp-sensor/front-porch-temp-sensor.yaml` — checks `bme280_temp` and `bh1750_lux`, publishes under category `Sensor`.

**Rules:**
- One `if` block per sensor ID — do not combine into a single message
- Category must be `Sensor` (not `System`) so it appears as a distinct row type in the dashboard
- Message must name the specific sensor and the GPIO pins, not just "sensor error"
- Check is run every 5 minutes — if the sensor recovers, the error stops appearing automatically

**Backlog:** hiking-monitor has BME280 (`bme_temp`) and LTR390 (`ltr_uv_index`) — both need this pattern added. See `components/hiking-sensor/hiking-sensor-claude-code-instructions.md`.

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

**The JCTsh broker (Mosquitto 2.0.21) runs MQTT v5.** The Node-RED broker config node uses `protocolVersion: 5`. Node-RED v4 UI imports generate MQTT v5 fields (`nl`, `rap`, `respTopic`, `contentType`, etc.) — these are now correct and do not need cleanup. ESP32/ESPHome devices and HA remain on MQTT v3.1.1; Mosquitto accepts both simultaneously.

**Google Apps Script returns 405 on redirect — treat it as success.** When Node-RED POSTs to an Apps Script web app URL, Google executes the script and appends the row, then returns a 302 redirect. Node-RED follows the redirect with POST; the redirect destination returns 405 (Method Not Allowed). The row WAS appended. The check response function must treat `statusCode === 405` as success, not as an error.

**Apps Script API keys must be alphanumeric.** Special characters (`&`, `@`, `*`) in URL query parameters break parsing even with `encodeURIComponent`. Generate keys using only `[a-zA-Z0-9]`.

**Node-RED env vars via systemd EnvironmentFile.** The Node-RED service on the Pi reads `/home/pi/.node-red/environment` via `EnvironmentFile=` in the systemd unit. Add `KEY=value` lines to this file for secrets passed to function nodes via `env.get('KEY')`. Restart Node-RED after editing.

---

### 5.5 GPS Timestamp Lookup Pattern

For body-worn environmental sensors that need GPS coordinates without GPS hardware on the ESP32: use the GPSLogger → Google Apps Script → GPS Track sheet pipeline.

**Architecture:**
```
Pixel (GPSLogger app)
    │  GET every 30 seconds while hiking
    ▼
Google Apps Script  action=gps
    │  append one row (timestamp, lat, lon, accuracy_m, altitude_m)
    ▼
"GPS Track" sheet in workbook

          ↕  (on SPIFFS replay)

Node-RED wildcard data handler
    │  GET action=lookup&ts=<sensor_ts>
    ▼
Google Apps Script  action=lookup
    │  nearest trackpoint within ±5 minutes
    ▼
lat/lon populated in Environmental Data sheet
```

**Key implementation details:**
- GPSLogger's `%TIME` placeholder is a Unix epoch integer (seconds, not milliseconds). The Apps Script converts it to ISO 8601 UTC before writing to the sheet.
- Lookup tolerance is ±5 minutes. This covers the worst case: 2-minute sensor interval with 30-second GPS interval means the nearest GPS point is always within 1 minute when hiking. The 5-minute window also tolerates brief GPS signal loss.
- Home-mode readings (rssi_dbm ≠ 0) always return `{lat: null, lon: null}` — no GPS track exists for home timestamps. This is correct behavior, not an error.
- No port forwarding needed. GPSLogger posts directly to Google over cellular — the Pi is not involved in GPS logging.

**Apps Script note:** The lookup function is in the same `doGet(e)` handler as any other GET actions. Add it alongside existing actions without replacing them.

**Reference:** `components/hiking-sensor/gps-pipeline.md`, `core/data-pipeline/environmental-data.gs`

---

### 5.6 Node-RED Per-Component Context Isolation

When a Node-RED function node handles multiple components via a wildcard subscription (e.g., `jctsh/components/+/data`), use the component name as a key suffix in `context.get/set` to prevent state from leaking between components:

```javascript
var component = msg.payload.component;

// Read per-component state (undefined on first message from this component)
var lastRssi = context.get('lastRssi_' + component);
var lastTs   = context.get('lastTs_'   + component) || '';

// Write per-component state
context.set('lastRssi_' + component, rssi);
context.set('lastTs_'   + component, ts);

// Initialize cleanly on first message — don't process a state transition yet
if (lastRssi === undefined) return null;
```

New components are picked up automatically by the wildcard subscription and get their own isolated context slots with no code changes. This pattern scales to any number of components.

**Important:** Node-RED in-memory context is cleared on service restart (`sudo systemctl restart nodered`). If you need to reset stale per-component state (e.g., after a long offline period), a restart is the cleanest method.

**Reference:** `components/hiking-sensor/hiking-hike-events.flow.json`, `Detect field session start / end` function node.

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

## 9. Non-ESP32 / Docker-Based Component Standards

Standards for components that are not ESP32/ESPHome devices — Docker-based services on dedicated Linux hosts (e.g. `photo-server`). Sections 1-8 above assume an ESP32; this section is the equivalent for a Docker/Linux host component. First established during the `photo-server` (Immich) build.

### 9.1 Docker DNS Pinning

Pin DNS in the Docker daemon config for any host running containers that need external connectivity:

```json
{
  "dns": ["8.8.8.8", "8.8.4.4"]
}
```

Applied at `/etc/docker/daemon.json`, then `sudo systemctl restart docker`. This is now twice-applied (Home Assistant's container, Immich's) — required, not optional. Root cause it prevents: a stale DHCP-assigned DNS server getting baked into a container's network config at creation time, which caused a full cloud-connectivity outage for HA in June 2026 and would otherwise repeat for any new container.

### 9.2 UUID-Based USB Storage Mounts

Any component with attached external storage mounts via UUID in `/etc/fstab` — never a raw device path (`/dev/sdX`), which can silently renumber on reconnect (confirmed happening mid-build to photo-server's own primary drive, `sda` → `sdc`, with no user action). Always add `nofail`, so a disconnected or missing drive doesn't block the host from booting:

```
UUID=<disk-uuid>  /mnt/<mount-point>  ext4  defaults,nofail  0  2
```

Prefer bus-powered 2.5" USB drives for compact installations — no separate power brick/cable to manage or fail. Note the tradeoff when sizing spares: a larger bus-powered drive may not exist, forcing a choice between capacity and the bus-powered convenience.

**Reference implementation:** `components/photo-server/backup.md`, `components/photo-server/network.md`.

### 9.3 Incremental Local Backup (rsync)

Weekly cron running `rsync -av --delete <source>/ <backup-destination>/` from primary storage to a local backup drive.

**This is incremental by design** — worth stating explicitly, since it is not obvious from a one-line script. `rsync` only transfers files that are new or changed since the last run (by size/mtime); `--delete` additionally removes anything from the destination no longer present in the source, keeping it an exact mirror rather than an ever-growing pile. A slow first run does not mean something is wrong — it means the destination is being fully reconciled for the first time (or after an unrelated change invalidated it); subsequent weekly runs should be fast, transferring only that week's actual changes.

**Reference implementation:** `components/photo-server/photo-library-backup.sh`, `components/photo-server/backup.md`.

### 9.4 Dashboard Visibility for Scheduled/Background Jobs

The non-ESP32 equivalent of §4's heartbeat/log standards. For any recurring systemd timer or cron job on a Docker/Linux host (scheduled reboots, backups, or similar), publish a matched pair of MQTT log messages to the JCTsh dashboard — one immediately before the job starts, one on completion:

```json
{"component":"<host-component-name>","category":"System","message":"<Job> starting."}
{"component":"<host-component-name>","category":"System","message":"<Job> complete."}
{"component":"<host-component-name>","category":"Alert","message":"<Job> failed (<detail>)."}
```

Reuse the host's existing MQTT account (e.g. `photo-server`, `jctsh-log-server`) via `mosquitto_pub` — do not create a new account per job. Neither message uses the `"Heartbeat - "` prefix, so each occurrence stays visible as its own dashboard row rather than collapsing, matching how ESP32 Alert-category messages behave (§4.2).

This pattern was established twice in the same build with an identical shape both times (scheduled-reboot notifications, then backup-run notifications), which is what promotes it from a one-off to a standard — the second implementation should not need to reinvent it.

**Reference implementation:** `core/maintenance/reboot-complete-pi.service` / `reboot-complete-m8.service`, `components/photo-server/photo-library-backup.sh`.

### 9.5 Scheduled Maintenance Windows — Cross-Host Coordination

Any new recurring job (cron or systemd timer) on any JCTsh host must be checked against the **Scheduled Maintenance Windows** table in `jctsh-network.md` before scheduling, and added to that table once deployed.

**Rule of thumb:** at least one hour of clearance from any other recurring job on any host, especially where one job's MQTT publish depends on another host being reachable — e.g. the Pi/M8 reboot stagger exists specifically because the M8's heartbeat publishes to the Pi's broker, so overlapping reboots would produce a false "down" reading for the wrong reason.

### 9.6 Detached Remote Job Execution

For any long-running remote job (data imports, backups, verification runs) that must survive the initiating SSH session ending, launch it via `nohup <command> & disown` on the remote host itself — not a local polling/monitoring loop.

**Critical:** verify actual state via `ps aux` / `systemctl status` on the remote host directly. Never assume that stopping a local monitoring tool has any effect on a detached remote process — it does not, and assuming otherwise caused a real duplicate-write race during the original `photo-server` Takeout migration (two `mv` operations racing on the same files after a local poller was stopped but the remote job kept running).

**Reference:** `components/photo-server/migration.md` ("Killed background processes didn't actually die").

---

## 10. Security Standards

Harvested from the full JCTsh security hardening audit (`jctsh-security-hardening.md`, CARD-0022/CARD-0023, completed 2026-07-09). Applies to every current and future JCTsh component and every account/service the ecosystem depends on.

### 10.1 SSH — key-only, no password auth

The Pi (and any future JCTsh host) must have `PasswordAuthentication no`, `PubkeyAuthentication yes` in `sshd_config` (check drop-in files under `sshd_config.d/` too — cloud-init images can silently override the default with `PasswordAuthentication yes`). Verify with a live rejected-password login test after any change, not just a config read.

### 10.2 MQTT broker authentication required

`allow_anonymous false` with a non-empty `password_file` is mandatory on Mosquitto. Every component gets its own dedicated account (see CLAUDE.md Credentials table) — never share credentials across components.

### 10.3 `secrets.yaml` / `secrets.h` always gitignored

Every ESPHome/Arduino component's credentials file must be excluded via `.gitignore` (`secrets.yaml`, `secrets.h`, `*.key`, `credentials.local.md`). Confirm periodically with `git log --all --full-history -- "**/secrets.yaml"` — should always return nothing.

### 10.4 Node-RED requires `adminAuth`

The Node-RED flow editor must never be reachable without a login — `adminAuth` with a bcrypt-hashed password in `settings.js` is required, since an unauthenticated editor exposes both automation logic and MQTT payload contents.

### 10.5 No direct internet port forwarding except MQTT (accepted exception)

Tailscale is the sole remote-access path for Pi services (SSH, Node-RED, HA). The one accepted exception is MQTT port 1883, forwarded via DuckDNS specifically so field ESP32 devices (e.g. hiking-monitor) can reach the broker over cellular when away from Tailscale-capable hardware — mitigated by fail2ban + strong per-component passwords, with TLS (port 8883) tracked as a follow-up (CARD-0003). Any new component considering port forwarding should default to Tailscale first and only forward a port if the device genuinely cannot run Tailscale.

### 10.6 MFA required on every cloud account in the ecosystem

Google (all family accounts), Amazon/Ring, Samsung/SmartThings, Ecobee, Microsoft (Windows login), and Home Assistant (TOTP via Profile → Multi-Factor Authentication Modules, per-user — must be enabled for every HA user account, not just the owner). Check this whenever a new cloud-dependent component or account is added to the ecosystem.

### 10.7 Router: UPnP off unless something actually needs it, remote management always off

Default UPnP to disabled — before enabling it for any device, confirm nothing already works without it. Check the router's UPnP mapping list; zero registered clients is the sign it can be safely turned off with no functional loss. Remote/WAN-side router admin access must always be off — LAN-only administration.

### 10.8 Router admin password and firmware currency

Router admin password must be a strong unique password (16+ characters), stored only in `credentials.local.md` (never in a versioned/harvested doc like this one). Prefer enabling automatic firmware updates over relying on periodic manual checks, where the router supports it — removes the recurring audit burden.

### 10.9 SSH private key Windows file permissions

On the Windows dev machine, the private key (`~/.ssh/id_ed25519`) must be restricted to the owning user only. Cloud-init/default Windows ACLs can leave `BUILTIN\Administrators`/`NT AUTHORITY\SYSTEM` with access — tighten with `icacls ... /inheritance:r /grant:r "<user>:(R)"` and confirm SSH still works afterward.

---

## Standards Version History

| Version | Change |
|---|---|
| 1.15 | Added §1.2 pin-verification guidance — harvested from salt-sensor's CARD-0049 perfboard build: identify pins by printed silkscreen label rather than a documented reference table's position numbers (different board brands/clones can have different physical pin order despite the same GPIO count), and add isolation checks between visually-adjacent pin labels to Pre-Power Checks, not just intentional-net continuity checks. |
| 1.14 | Added §10 Security Standards — harvested from the completed JCTsh security hardening audit (CARD-0022/CARD-0023, `jctsh-security-hardening.md`). Covers SSH key-only auth, MQTT broker auth, `secrets.yaml` gitignore requirement, Node-RED `adminAuth`, Tailscale-as-sole-remote-access-path with the accepted MQTT-port-forward exception, MFA requirement across every cloud account (including per-user HA TOTP), router UPnP/remote-management policy, router admin password/firmware currency, and Windows SSH private key permissions. |
| 1.13 | Added §9 Non-ESP32 / Docker-Based Component Standards — first section for non-ESP32/Docker host components, harvested from the `photo-server` (Immich) build. §9.1 Docker DNS pinning (twice-applied: HA, Immich). §9.2 UUID-based USB storage mounts with `nofail`, bus-powered drive preference. §9.3 incremental rsync local backup — explicit note that `rsync --delete` is incremental, not a full re-copy each run. §9.4 dashboard visibility for scheduled/background jobs — matched start/complete MQTT message pairs, the non-ESP32 equivalent of §4's heartbeat standard, established twice in one build (reboot notifications, backup notifications) with an identical shape. §9.5 cross-host schedule coordination via the `jctsh-network.md` Scheduled Maintenance Windows table, ≥1 hour clearance rule of thumb. §9.6 detached remote job execution (`nohup ... & disown`) with the rule to always verify via `ps aux`/`systemctl status` on the remote host, never assume a local monitor stopping affects a detached remote process. |
| 1.12 | Added §2.14 point 3 charging-surface guidance: the fireproof bag must sit on a heat-insulating, non-combustible surface (concrete/masonry, ceramic tile, cement board, or a sand/kitty-litter-lined metal tray) — never bare sheet metal on a wooden workbench, since metal conducts thermal-runaway heat straight through to the wood rather than blocking it. |
| 1.11 | Added §2.14 point 8: GPIO-controlled power gating for I2C/SPI peripherals during sleep (P-FET high-side switch on the microcontroller's 3.3V output, not the boost module's output) — flagged as a candidate pattern, not yet a required standard, pending validation via hiking-sensor CARD-0026/CARD-0027. |
| 1.10 | Added §2.14 point 7: prefer direct LiPo-to-LDO power architecture over boost-then-buck for new battery-powered builds — avoids two-stage conversion idle draw and the boost converter's end-of-charge instability. Recommended default for the *next* build, not applied retroactively to hiking-monitor. |
| 1.9 | Added §2.14 Battery-Powered Component Safety Standards: PCM-protected cells required (verify before purchase, EEMB 603449 confirmed compliant), firmware low-battery cutoff required (3.4V threshold, checked at boot and during operation, persistent e-ink warning), fireproof charging bag required, never charge a cell showing 0V/swelling/heat/smell, storage at 40-60% charge, disposal via battery recycling, connector polarity verification before first use. Established after hiking-monitor's original battery failed in the field with no advance warning (2026-07-03). |
| 1.0 | Initial release. Enclosure convention, ESP32/ESPHome standards, MQTT conventions, observability standards, SmartThings integration, LED standards, documentation standards. |
| 1.8 | Updated §5.4: broker now runs MQTT v5 (Mosquitto 2.0.21, `protocolVersion: 5` in Node-RED broker node). Removed MQTT v5 field cleanup warning — v5 fields from Node-RED v4 UI imports are now correct. ESP32/ESPHome/HA remain on v3.1.1; Mosquitto accepts both simultaneously. |
| 1.7 | Changed heartbeat standard from 5 minutes to 30 minutes throughout (§2.7, §3.2, §4.1, §4.4, §4.6). 30 min is derived from the watchdog timeout (35 min = interval + 5-min buffer), not arbitrary. Updated front-porch-temp-sensor.yaml to match. |
| 1.6 | Added §2.8 multi-network WiFi variant (networks: list) and captive_portal deep-sleep exception. Added §2.12 e-ink display pattern. Added §2.13 multi-priority on_boot sequencing. Updated §3.3 with DuckDNS broker guidance for cellular components. Added §3.6 rssi_dbm=0 field-mode sentinel. Added §5.5 GPS timestamp lookup pattern. Added §5.6 Node-RED per-component context isolation. |
| 1.5 | Added §5.4 Node-RED flow deployment patterns (MQTT v5 field issue, flows.json injection, Apps Script 405 redirect, alphanumeric API keys, env vars via EnvironmentFile), watchdog is a new Node-RED flow (not an existing process). Added SmartThings actual integration path (Node-RED → HA REST API → virtual switch). Added MQTT account creation as a required step. Added phone notification via HA companion app as watchdog alert method. |
| 1.4 | Added §2.10 onboard flash logging standard: use ESP-IDF SPIFFS not Arduino LittleFS; name files by function not library. Fixed §2.7 reference from "LittleFS replay loop" to "SPIFFS replay loop". Renumbered MQTT account creation to §2.11. |
| 1.3 | Added §2.8 ESPHome component boilerplate (board, framework, logger, captive_portal, WiFi AP fallback naming, component naming consistency, flash path). Added §2.9 sensor coding standards (NaN guards, standard I2C pins GPIO21/22, internal: true housekeeping sensors). Added §3.4 will_message pattern (retain: false critical). Added §3.5 MQTT discovery rule. Fixed §4.1 heartbeat message format and added "Heartbeat - " prefix requirement. Fixed §4.3 log event message formats (hyphen throughout, removed MQTT reconnected event, clarified LWT). |
| 1.2 | Added §2.7 ESPHome MQTT publishing patterns (on_connect and heartbeat). Fixed §4.3 online message format (hyphen not em dash). Added §4.1 note on heartbeat interval discrepancy between standard (5 min) and existing components (30 min). Renumbered MQTT account creation to §2.8/§2.10. |
| 1.1 | Corrected observability section: log format is JSON to /log topic routed by Node-RED (not a separate process to examine). Watchdog is a new Node-RED flow built as part of garage-radar project, not an existing process. Added actual SmartThings integration path (Node-RED → HA REST API → virtual switch). Added MQTT account creation procedure (Section 2.7) including Mosquitto passwd ownership gotcha. Added phone notification via HA companion app as watchdog alert method. Added CLAUDE.md credentials table update to documentation standards. |
