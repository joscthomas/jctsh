# JCTsh Node-RED Watchdog

Monitors all JCTsh component heartbeats. Sends a push notification to the Pixel
if any component goes silent for 35 minutes, then re-alerts every 2 hours for
as long as it stays silent (CARD-0331).

---

## How It Works

1. All ESP32 components publish a heartbeat to `jctsh/+/+/heartbeat` — every 30 minutes for
   `garage-radar`, `salt-sensor`, `front-porch-temp-sensor` and `back-patio-temp-sensor`; every 5
   minutes for `hiking-monitor` and `air-quality-monitor` (`JCTsh-Build-Standards.md` §4.1)
2. The watchdog MQTT In node subscribes to that wildcard — all components are caught
   automatically, no flow changes needed when new components are added
3. On each heartbeat receipt, a per-component 35-minute setTimeout is reset, and any
   active re-alert interval (see step 5) is cleared — the component is back
4. If 35 minutes pass with no heartbeat from a component:
   - Push notification sent to Pixel 10 Pro XL via HA companion app
   - Alert logged to `jctsh/core/watchdog/log`
5. **CARD-0331:** if the component is still silent, a follow-up alert re-fires every
   2 hours after that, carrying the accumulated downtime (e.g. "down 2h15m"), until
   either a heartbeat arrives (step 3 clears it) or it stays down indefinitely. Without
   this, a 35-minute outage and a 16-hour outage were indistinguishable in the alert
   stream — found live 2026-09-22 cross-checking an alert against the Pi's actual log.

6. **CARD-0324 — daily check line.** Every day at 07:00 the watchdog also logs a normal `System`
   line, e.g. `Daily check: 6 components reporting, 1 silent (hiking-monitor)`. Without it the
   watchdog only ever spoke when something was wrong, so its `/status` row showed its last outage
   indefinitely and its silence couldn't be told apart from Node-RED itself being down. Now the
   line replaces the stale alert as its last message, and if it stops appearing the watchdog (or
   Node-RED) is what died. It is fed by `fn_track_heartbeats`, a separate function on the same
   heartbeat subscription that records each component's last heartbeat time in flow context —
   `fn_timer_manager`, the alerting path, is untouched. "Silent" uses the same 35-minute threshold;
   components unheard-from for 7 days drop out of the count. Flow context resets on a Node-RED
   restart, so a check right after one reports few components until heartbeats resume (~5 minutes).
   The wording deliberately isn't `Heartbeat - ` or `Watchdog: `, which `log_server.py` treats as
   heartbeats and would expect every ~70 minutes.

The 35-minute window is sized for the slowest heartbeat, 30 minutes + a 5-minute margin
(`JCTsh-Build-Standards.md` §4.1) — for the 5-minute devices that is 6 missed heartbeats before
alerting. A 30-minute-interval device would otherwise trip it on any reboot, since its interval
counts from boot; those devices therefore also send a heartbeat ~90 s after every boot
(CARD-0333, CARD-0335), so a reboot no longer raises a false alert.

---

## Flow: `core/node-red/watchdog.flow.json`

```
jctsh/+/+/heartbeat  ──► Timer manager (per component) ──► [35-min timeout fires]
                                                                    │
                                                              Build alert
                                                             /           \
                                              HA notify (Pixel)     MQTT log out
                                                    │                     │
                                             Log HA response    jctsh/core/watchdog/log
                                                    │
                                            (on error only)
                                         jctsh/core/watchdog/log
```

---

## Alert Message

**Initial alert, push notification (Pixel 10 Pro XL):**
```
Title: JCTsh Watchdog
Message: JCTsh alert: <component> has not reported in 35 minutes
```

**Initial alert, log message (`jctsh/core/watchdog/log`):**
```json
{ "component": "watchdog", "category": "Alert", "message": "Component <name> silent for 35 minutes" }
```

**Repeat alert (CARD-0331), every 2h while still silent — push notification:**
```
Title: JCTsh Watchdog
Message: JCTsh alert: <component> still silent -- down 2h15m
```

**Repeat alert, log message:**
```json
{ "component": "watchdog", "category": "Alert", "message": "Component <name> still silent -- down 2h15m" }
```

---

## Configuration

**HA_TOKEN:** The HA long-lived access token is read from the Node-RED `HA_TOKEN`
environment variable. Set in `/home/pi/.node-red/environment`:
```
HA_TOKEN=<long-lived-access-token>
```

Restart Node-RED after changing: `sudo systemctl restart nodered`

**Notification service name:** `mobile_app_pixel_10_pro_xl` — must match the device
name in HA (Settings → Companion App). If the Pixel device name changes, update
`fn_build_alert` in the flow.

---

## Adding New Components

Nothing to do. The wildcard `jctsh/+/+/heartbeat` picks up any component that
publishes a heartbeat to that topic pattern. Ensure new ESP32 components publish
a heartbeat to `jctsh/components/<name>/heartbeat` (5 or 30 minutes; a 30-minute device also needs
the ~90 s boot-time heartbeat, §4.1).

---

## Testing

1. Note the time of the last heartbeat from the component under test (log dashboard)
2. Power off the ESP32
3. Wait 35 minutes from the last heartbeat
4. Confirm push notification arrives on the Pixel
5. Confirm alert appears in log dashboard under component `watchdog`
6. Leave it off and confirm a repeat alert arrives 2 hours later, with the accumulated
   downtime in the message (CARD-0331)
7. Power ESP32 back on — watchdog timer resets on the next heartbeat, repeat interval
   is cleared, no further alerts

To test without waiting 35 minutes / 2 hours: temporarily edit the `fn_timer_manager`
function node to use shorter durations (e.g. 2-minute initial timeout, 1-minute repeat
interval), deploy, test, then restore to 35 minutes / 2 hours.

---

## Troubleshooting

| Symptom | Check |
|---|---|
| No notification after 35 min | HA_TOKEN set in `/home/pi/.node-red/environment`; Node-RED restarted after setting it |
| Wrong device notified | Service name `mobile_app_pixel_10_pro_xl` in `fn_build_alert` matches HA companion app device |
| Alert not appearing in log dashboard | `jctsh/core/watchdog/log` routed by core log flow; confirm core.flow.json is imported and active |
| Timer not resetting on heartbeat | Check Node-RED debug panel for heartbeat messages arriving on `jctsh/+/+/heartbeat` |
