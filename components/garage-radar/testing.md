# Garage Radar — Sensor Validation (Step 4)

## Prerequisites

- ESP32 flashed and connected (WiFi + MQTT confirmed)
- All 8 entities visible in HA under the garage-radar device
- HA Developer Tools → States accessible

---

## Test 1 — Baseline (no presence)

With nobody in front of the radar:

| Entity | Expected |
|---|---|
| Presence | `off` |
| Moving Target | `off` |
| Still Target | `off` |
| Moving Distance | 0 or unavailable |
| Still Distance | 0 or unavailable |
| Moving Energy | low or 0 |
| Still Energy | low or 0 |
| Detection Distance | 0 or unavailable |

If Presence is stuck `on` with no one present, the radar may be detecting a wall or
object. Reposition or angle the sensor slightly.

---

## Test 2 — Moving presence

Walk in front of the radar at a distance of roughly 1–3 meters:

| Entity | Expected |
|---|---|
| Presence | `on` |
| Moving Target | `on` |
| Still Target | `off` (may flicker) |
| Moving Distance | updates in cm as you move |
| Moving Energy | > 0 |

---

## Test 3 — Still presence

Stand or sit still in front of the radar for 5–10 seconds:

| Entity | Expected |
|---|---|
| Presence | `on` |
| Moving Target | `off` (may take a few seconds) |
| Still Target | `on` |
| Still Distance | stable cm reading |
| Still Energy | > 0 |

The LD2412 uses both motion and micro-motion (breathing, small movements) for still
detection. Standing completely rigid may reduce still energy — normal slight movement
is enough.

---

## Test 4 — Delayed off (30-second holdoff)

Walk in front of the radar, confirm Presence is `on`, then leave the detection zone:

- Presence should remain `on` for approximately 30 seconds after you leave
- After 30 seconds, Presence should go `off`

This confirms the `delayed_off: 30s` filter is working. If Presence drops immediately
when you leave, check the filter in `garage-radar.yaml`.

---

## Test 5 — Detection range

Walk toward the radar from outside the room and note the distance (Moving Distance)
at which Presence first goes `on`. Walk back and note where it drops off (after the
30s holdoff). Adjust the radar's physical angle or position if the range is too short
or too wide for the garage.

> The LD2412 has a detection range of up to ~9 meters in moving mode and ~6 meters in
> still mode. In a typical garage, 4–6 meters is a reasonable working range.

---

## Watching values in real time

**Option A — HA Developer Tools:**
Developer Tools → States → filter by `garage_radar` → watch values update live.

**Option B — MQTT:**
From the Pi or any machine with mosquitto_sub:
```
mosquitto_sub -h 192.168.1.117 -u jctsh-log-server -P <password-from-log-server.env> \
  -t "jctsh/components/garage-radar/#" -v
```

---

## Pass criteria

All 5 tests pass when:
- [ ] Baseline shows no presence with empty detection zone
- [ ] Moving presence detected within 1–3 meters
- [ ] Still presence detected after stopping
- [ ] 30-second holdoff confirmed on departure
- [ ] Detection range appropriate for garage installation point

---

## Next Step (after Step 4 only)

If all Step 4 tests pass, proceed to Step 4.5 enhancements, then run the Step 4.6
validation below before moving to `perfboard-layout.md` (Step 5).

---

# Enhancement Validation (Step 4.6)

Run these tests after completing Step 4.5 (LEDs added, YAML reflashed, watchdog flow
imported into Node-RED).

---

## LD2412 initialization note

After flashing new LD2412 configuration (range, sensitivity, gate thresholds), the
radar module may not apply the new settings on the first boot. Symptom: device is
online and sending heartbeats but presence is never detected. The "Presence cleared —
timeout elapsed" message on boot is a positive sign — it means the LD2412 initialized
correctly and briefly detected something on startup.

**Fix:** After any flash that changes LD2412 parameters, restart the device a second
time from the ESPHome web UI (`http://192.168.1.119` → Restart). Confirmed 2026-06-09.

---

## Test 6 — Green LED (presence indicator)

Walk in front of the radar and confirm:
- [x] Green LED lights when `Presence` goes `on`
- [x] Green LED extinguishes approximately 30 seconds after you leave the detection zone
  (it follows the `delayed_off: 30s` filter, not the raw radar state)

If the LED does not light: check GPIO33 wiring — resistor orientation, LED polarity
(flat side / short leg = cathode = GND side).

---

## Test 7 — Yellow LED (garage presence vswitch mirror)

The yellow LED mirrors the `garage-presence-vswitch` MQTT state. To test:

1. In HA, manually turn `switch.garage_presence_vswitch` **on**
   (Developer Tools → Services → `switch.turn_on` → entity: `switch.garage_presence_vswitch`)
2. Confirm yellow LED lights
3. Turn the switch **off** — confirm yellow LED extinguishes

If the LED does not respond: the ESP32 may not yet have received a retained message on
`jctsh/components/garage-presence-vswitch/state`. Confirm that topic is being published
(check with MQTT explorer or `mosquitto_sub`). If the topic is not published, HA may need
to be configured to publish the switch state to MQTT — investigate the garage-presence
component setup.

---

## Test 8 — Log messages

Open the log dashboard at `http://raspberrypi.local/` and filter by component `garage-radar`.

Trigger each condition and confirm the corresponding log entry appears:

| Action | Expected log message |
|---|---|
| ESP32 boot / MQTT connect | `Garage radar online — ESPHome vX.X.X, IP: x.x.x.x` |
| MQTT connect | `MQTT broker connected — publishing to ...` |
| Walk in front of radar | `Presence detected — has_target: ON (still: ..., moving: ..., distance: ...m)` |
| Leave detection zone (after 30s) | `Presence cleared — has_target: OFF, timeout elapsed` |
| Wait up to 5 minutes | `Heartbeat — uptime: Xh Xm, RSSI: -XXdBm, presence: ON/OFF` |

If log messages are not appearing: confirm Node-RED is routing `jctsh/+/+/log` to the
Python log server. Check Node-RED debug panel for MQTT subscription errors.

---

## Test 9 — Heartbeat

Wait up to 5 minutes after boot. Confirm:
- [ ] A heartbeat log entry appears in the dashboard under `garage-radar` (System category)
- [ ] In Node-RED, open the watchdog flow tab and enable the debug node — confirm a
  message arrives on `jctsh/components/garage-radar/heartbeat` within 5 minutes

---

## Test 10 — Watchdog alert

> **Duration:** up to 12 minutes. Run when you have time to wait.

1. Note the time
2. Power off the ESP32 (unplug USB)
3. Wait — the watchdog timer starts counting from the last heartbeat received
4. Within 10 minutes of the last heartbeat, a push notification should arrive on the
   Pixel 10 Pro: `JCTsh alert: garage-radar has not reported in 10 minutes`
5. An alert entry should also appear in the log dashboard under component `watchdog`
6. Power the ESP32 back on — confirm the watchdog timer resets (no further alerts)

If the notification does not arrive: check Node-RED watchdog flow for errors. Confirm
`HA_TOKEN` environment variable is set in Node-RED and is a valid HA long-lived access
token. Confirm the HA notify service name `mobile_app_pixel_10_pro` matches the device
name in HA (Settings → Companion App).

---

## Step 4.6 pass criteria

- [x] Green LED lights on presence, extinguishes after 30s timeout
- [ ] Yellow LED mirrors garage presence vswitch state
- [ ] All log message types appear in the dashboard
- [ ] Heartbeat appears every 5 minutes
- [ ] Watchdog push notification received within 10 minutes of ESP32 power-off
- [ ] Watchdog resets when ESP32 comes back online

If all pass, proceed to `perfboard-layout.md` (Step 5).
