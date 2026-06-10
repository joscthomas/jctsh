# JCTsh Node-RED Watchdog

Monitors all JCTsh component heartbeats. Sends a push notification to the Pixel
if any component goes silent for 35 minutes.

---

## How It Works

1. All ESP32 components publish a heartbeat every 5 minutes to `jctsh/+/+/heartbeat`
2. The watchdog MQTT In node subscribes to that wildcard — all components are caught
   automatically, no flow changes needed when new components are added
3. On each heartbeat receipt, a per-component 35-minute setTimeout is reset
4. If 35 minutes pass with no heartbeat from a component:
   - Push notification sent to Pixel 10 Pro XL via HA companion app
   - Alert logged to `jctsh/core/watchdog/log`

The 35-minute window = 5-minute heartbeat interval × 7, giving 6 missed heartbeats
before alerting. This tolerates brief MQTT disconnects and device reboots without
false alarms.

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

**Push notification (Pixel 10 Pro XL):**
```
Title: JCTsh Watchdog
Message: JCTsh alert: <component> has not reported in 35 minutes
```

**Log message (`jctsh/core/watchdog/log`):**
```json
{ "component": "watchdog", "category": "Alert", "message": "Component <name> silent for 35 minutes" }
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
a heartbeat every 5 minutes to `jctsh/components/<name>/heartbeat`.

---

## Testing

1. Note the time of the last heartbeat from the component under test (log dashboard)
2. Power off the ESP32
3. Wait 35 minutes from the last heartbeat
4. Confirm push notification arrives on the Pixel
5. Confirm alert appears in log dashboard under component `watchdog`
6. Power ESP32 back on — watchdog timer resets on the next heartbeat (no further alerts)

To test without waiting 35 minutes: temporarily edit the `fn_timer_manager` function
node to use a shorter timeout (e.g. 2 minutes), deploy, test, then restore to 35.

---

## Troubleshooting

| Symptom | Check |
|---|---|
| No notification after 35 min | HA_TOKEN set in `/home/pi/.node-red/environment`; Node-RED restarted after setting it |
| Wrong device notified | Service name `mobile_app_pixel_10_pro_xl` in `fn_build_alert` matches HA companion app device |
| Alert not appearing in log dashboard | `jctsh/core/watchdog/log` routed by core log flow; confirm core.flow.json is imported and active |
| Timer not resetting on heartbeat | Check Node-RED debug panel for heartbeat messages arriving on `jctsh/+/+/heartbeat` |
