# Front Porch Temp Sensor — Integration Notes (Step 1)

Investigation findings from existing patterns before writing any configuration.

---

## 1. Garage-Radar Heartbeat Implementation

**Source:** `components/garage-radar/garage-radar.yaml`

The heartbeat is implemented using an `interval: 5min` component. Each firing publishes
two MQTT messages:

**Publish 1 — to `.../log` (log dashboard):**
```yaml
- mqtt.publish:
    topic: jctsh/components/garage-radar/log
    payload: !lambda |-
      // snprintf → JSON string
      // {"component":"garage-radar","category":"System","message":"Heartbeat - uptime: Xh Xm, RSSI: -XXdBm, presence: ON/OFF"}
```

**Publish 2 — to `.../heartbeat` (Node-RED watchdog):**
```yaml
- mqtt.publish:
    topic: jctsh/components/garage-radar/heartbeat
    payload: !lambda |-
      // snprintf → JSON string
      // {"component":"garage-radar","uptime":"Xh Xm","rssi":-XX,"presence":"ON/OFF"}
```

**Supporting sensors (both `internal: true`):**
```yaml
- platform: uptime
  id: uptime_sec
  internal: true

- platform: wifi_signal
  id: wifi_rssi
  internal: true
  update_interval: 60s
```

The lambda body converts `id(uptime_sec).state` (float seconds) to hours/minutes via
integer arithmetic (`h = secs / 3600`, `m = (secs % 3600) / 60`). RSSI is cast to `int`.

**Front-porch-temp-sensor adaptation:** Replace the `presence` field with `temp` (float °F).
Log message becomes: `"Heartbeat — uptime: Xh Xm, RSSI: -XXdBm, temp: XX.X°F"`
Heartbeat payload: `{"component":"front-porch-temp-sensor","uptime":"Xh Xm","rssi":-XX,"temp":XX.X}`

---

## 2. Garage-Radar MQTT Structure

**Source:** `components/garage-radar/garage-radar.yaml`

```yaml
mqtt:
  broker: !secret mqtt_broker
  username: !secret mqtt_username
  password: !secret mqtt_password
  topic_prefix: jctsh/components/garage-radar
  discovery: true
  discovery_prefix: homeassistant
  will_message:
    topic: jctsh/components/garage-radar/log
    payload: '{"component":"garage-radar","category":"MQTT","message":"MQTT disconnected"}'
    retain: false
    qos: 0
  on_connect:
    - mqtt.publish:  # System online message (includes ESPHome version and IP)
    - mqtt.publish:  # MQTT connected message
```

The `will_message` is the LWT (Last Will and Testament) — the broker publishes it
automatically when the device disconnects without a clean shutdown.

**Front-porch-temp-sensor adaptation:** Replace `garage-radar` with `front-porch-temp-sensor`
in all topic strings. On_connect messages should log: WiFi connected (System), MQTT connected (MQTT),
MQTT disconnected (MQTT via LWT), MQTT reconnected (MQTT).

---

## 3. ESPHome Board and Framework

**Source:** `components/garage-radar/garage-radar.yaml`

```yaml
esp32:
  board: esp32dev
  framework:
    type: arduino
```

Front-porch-temp-sensor uses the same board (ESP32 DevKitC-32). Use identical settings.

---

## 4. Secrets Template Format

**Source:** `components/garage-radar/secrets.yaml.template`

Seven keys, all referenced via `!secret` in the YAML:

```yaml
wifi_ssid: "your_wifi_ssid"
wifi_password: "your_wifi_password"
ap_password: "your_fallback_ap_password"

mqtt_broker: "raspberrypi.local"
mqtt_username: "your_mqtt_username"
mqtt_password: "your_mqtt_password"

ota_password: "your_ota_password"
```

`secrets.yaml` is gitignored in `components/garage-radar/.gitignore`. The front-porch-temp-sensor
directory must have the same `.gitignore` entry.

---

## 5. Wildcard Subscriptions Confirmed — No Node-RED Changes Needed

**Source:** `core/node-red/watchdog.flow.json` and `core/logging/log_server.py`

### `/heartbeat` wildcard — Node-RED watchdog

`watchdog.flow.json` subscribes to `jctsh/+/+/heartbeat`. From the tab info field:

> "New components are picked up automatically — no changes to this flow needed when new components are added."

The watchdog sets a 10-minute per-component timer that resets on each heartbeat. Silence
for 10 minutes triggers a push notification to the Pixel 10 Pro XL via HA.

### `/log` wildcard — Python log server (direct, not via Node-RED)

The Python log server (`core/logging/log_server.py`, line 29) subscribes directly:
```python
MQTT_TOPIC = "jctsh/+/+/log"
```

**Clarification on CLAUDE.md description:** CLAUDE.md describes Node-RED as routing log
messages to the log server. In practice, the log server subscribes to `jctsh/+/+/log`
directly via its own MQTT client. Node-RED is not involved in log routing. This means
log messages from `front-porch-temp-sensor` are picked up automatically the moment the
device starts publishing — no Node-RED or log server changes needed.

**No Node-RED flow file is needed for this component.** Wildcard subscriptions in both
`watchdog.flow.json` and `log_server.py` automatically handle the new component.

---

## 6. Existing MQTT Accounts

**Source:** Root `CLAUDE.md` credentials table

| Account | Used by |
|---|---|
| `jctsh-log-server` | Python log server |
| `nodered` | Node-RED |
| `homeassistant` | Home Assistant MQTT integration |
| `garage-radar` | garage-radar ESPHome device |
| `salt-sensor` | salt-sensor ESP32 sketch |

`front-porch-temp-sensor` does not exist yet — no naming conflict. The new account
will be created in Step 2 before any flashing attempt.

---

## 7. Deviations from Expected Patterns

None found in the garage-radar YAML itself. One clarification noted above:

- **Log routing:** CLAUDE.md architecture diagram implies Node-RED routes `/log` to the
  Python log server. The actual implementation has the log server subscribe directly.
  This does not change any build steps — it means log messages are received without any
  Node-RED involvement.

---

## Ready to Proceed

All patterns confirmed. Step 2 (MQTT account creation) can begin.
