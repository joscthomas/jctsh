# Garage Radar — Integration Investigation Notes (Step 8)

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
