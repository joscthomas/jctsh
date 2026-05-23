# Garage Radar — Integration Notes

## Step 4.5 — Enhancement Integration Notes

### MQTT account
`garage-radar` account confirmed in CLAUDE.md credentials table. Created during Steps
1–4 and verified working (Steps 1–4 complete, MQTT publishing confirmed). No action
needed unless account is deleted and must be recreated:
```
sudo mosquitto_passwd -b /etc/mosquitto/passwd garage-radar <password>
sudo chown root:mosquitto /etc/mosquitto/passwd
sudo systemctl restart mosquitto
```

### Log routing
Node-RED (or the core log server) subscribes to the wildcard `jctsh/+/+/log`
(or `jctsh/#`). All garage-radar log messages published to
`jctsh/components/garage-radar/log` are routed to the Python log server automatically.
No per-component Node-RED changes are needed for logging — the wildcard handles it.

### Watchdog
`core/node-red/watchdog.flow.json` builds the new JCTsh watchdog flow. It subscribes
to `jctsh/+/+/heartbeat` — the garage-radar heartbeat (`jctsh/components/garage-radar/heartbeat`,
every 5 minutes) is caught automatically by this wildcard. If no heartbeat arrives
within 10 minutes, a push notification fires via HA companion app (Pixel 10 Pro) and
an alert is logged to `jctsh/core/watchdog/log`. No changes to this flow are needed
when new components are added — the wildcard picks them up automatically.

### SmartThings
The garage radar has no direct SmartThings device. The radar integrates with SmartThings
indirectly: it triggers the HA garage presence timer, which controls the existing
`switch.garage_presence_vswitch` that SmartThings already knows about. SmartThings sees
the outcome (garage presence on/off) without needing to know the radar exists.

Rejected alternatives: direct SmartThings API calls (requires a PAT — not used in this
project), additional virtual switch (redundant alongside existing Garage Presence Vswitch),
HA entity exposure (standard HA SmartThings integration does not push HA entities to ST).
See `smartthings-integration.md` for the full rationale.

### HA REST API notification endpoint
`POST http://localhost:8123/api/services/notify/mobile_app_pixel_10_pro`
Used by the watchdog flow for Pixel 10 Pro alerts. Confirmed from architecture
document; validate the service name in HA Developer Tools → Services if the
notification does not arrive during watchdog testing.

---

## Step 8 — Integration Investigation Notes (Step 8)

## Where the 20-minute timeout lives

**Home Assistant only.** No Node-RED involvement in garage presence.

- `timer.garage_presence_timer` — HA countdown timer
- `input_number.garage_timer_duration` — configurable duration (default 20 min)
- Timer is started/restarted by the "Garage Presence - Restart timer on activity" automation
- Timer expiry turns off `switch.garage_presence_vswitch` via "Garage Presence - Timer expired"

## Existing presence inputs

All three existing inputs are triggers in the same "Restart timer on activity" automation:

| Entity | Trigger condition | Notes |
|---|---|---|
| `binary_sensor.garage_motion_motion` | `to: "on"` | PIR — may stick `on` in heat |
| `binary_sensor.back_door_door` | any state change | ST→HA sync can be unreliable |
| `binary_sensor.garage_cam_motion` | `to: "on"` | PIR — unreliable in hot garage |

## Radar entity in HA

ESPHome device `garage-radar`, sensor named `Presence` (device_class: occupancy).
HA entity ID: `binary_sensor.garage_radar_presence`

The `delayed_off: 30s` filter in `garage-radar.yaml` means the entity stays `on` for
30 seconds after the radar clears — smoothing momentary detection gaps before HA sees
the state change.

## What needs to change

**One addition only:** add `binary_sensor.garage_radar_presence` as a trigger
(`to: "on"`) in the "Garage Presence - Restart timer on activity" automation.

No new automations. No Node-RED changes. No helpers. Nothing else is modified.

## Integration path

```
LD2412 radar detects presence
    ↓ UART → ESPHome → 30s delayed_off filter
binary_sensor.garage_radar_presence → on
    ↓ triggers
"Garage Presence - Restart timer on activity"
    ↓ restarts
timer.garage_presence_timer (20 min)
    ↓ turns on
switch.garage_presence_vswitch
    ↓ (existing downstream automations unchanged)
SmartThings → lights, garage door
```
