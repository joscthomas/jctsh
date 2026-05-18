# Garage Presence — Component Context

HA-only component. No ESP32, no Node-RED. Tracks presence in the garage by running
a countdown timer that resets on any activity. The timer expiry signal is available
to other automations via `timer.garage_presence_timer` — what happens on expiry is
intentionally decoupled from this component.
See `jctsh/CLAUDE.md` for monorepo-wide conventions.

## Architecture
- **Home Assistant** runs the countdown timer and automation
- **SmartThings** provides trigger sensors
- Path to SmartThings: HA REST API → SmartThings integration (see jctsh/CLAUDE.md)

## How It Works
1. Any garage activity (motion, door, camera) restarts the HA timer
2. Timer duration is read from `input_number.garage_timer_duration` (default 20 min)
3. Timer expiry is available as a `timer.finished` event — consumed by other automations

## HA Helpers
| Helper | Entity ID | Purpose |
|---|---|---|
| Garage Presence Timer | `timer.garage_presence_timer` | Countdown timer |
| Garage Timer Duration | `input_number.garage_timer_duration` | Duration in minutes (1–120, default 20) |

Both created via HA UI (Settings → Devices & Services → Helpers). Not in configuration.yaml.

## SmartThings Devices
| Device | ST ID | HA Entity ID | Role |
|---|---|---|---|
| Garage Sensor (motion) | eae7580a-66cb-476f-b5a5-f0672b2a76aa | `binary_sensor.garage_motion_motion` | Trigger ✅ |
| Back Door Sensor (door) | 15597627-aec7-4e51-baec-7d106c7ee092 | `binary_sensor.back_door_door` | Trigger ✅ |
| Garage Cam (motion) | b11a8e19-87da-4ca3-b062-a8a95254548b | `binary_sensor.garage_cam_motion` | Trigger (cam sensitivity issue — wired up, unreliable) |

Note: Garage Timer Duration (ST 49a4fa15-940d-45e8-a644-acbd4c0d3b67) was not exposed
as an HA entity by the SmartThings integration. Replaced by `input_number.garage_timer_duration`.

Note: `binary_sensor.garage_door_sensor_door` was the originally assumed HA entity ID
for the door sensor — the actual entity is `binary_sensor.back_door_door`.

## HA Automations
Both created via HA UI (Settings → Automations & Scenes → Edit in YAML).

**Garage Presence - Restart timer on activity** (`mode: restart`)
```yaml
alias: Garage Presence - Restart timer on activity
triggers:
  - entity_id: binary_sensor.garage_motion_motion
    to: "on"
    trigger: state
  - entity_id: binary_sensor.back_door_door
    trigger: state
  - entity_id: binary_sensor.garage_cam_motion
    to: "on"
    trigger: state
actions:
  - target:
      entity_id: timer.garage_presence_timer
    data:
      duration: "{{ (states('input_number.garage_timer_duration') | int) * 60 }}"
    action: timer.start
  - action: switch.turn_on
    target:
      entity_id: switch.garage_presence_vswitch
mode: restart
```

**Garage Presence - Timer expired** (`mode: single`)
```yaml
alias: Garage Presence - Timer expired
triggers:
  - event_type: timer.finished
    event_data:
      entity_id: timer.garage_presence_timer
    trigger: event
actions:
  - action: switch.turn_off
    target:
      entity_id: switch.garage_presence_vswitch
mode: single
```

## Adding More Triggers
Edit the automation in HA UI → Edit in YAML → add a new `state` trigger entry.

## Testing
1. Set `input_number.garage_timer_duration` to `3` in Developer Tools → States
2. Trigger back door or motion sensor
3. Confirm timer card on Overview dashboard starts at 3 minutes
4. To force expiry: Developer Tools → Actions → `timer.finish` → `timer.garage_presence_timer`
