# Garage Presence — Component Context

HA-only component. No ESP32, no Node-RED. Automatically closes the garage door when
no activity has been detected for a configurable duration.
See `jctsh/CLAUDE.md` for monorepo-wide conventions.

## Architecture
- **Home Assistant** runs the countdown timer and automations
- **SmartThings** provides trigger sensors and receives output signals via virtual switches
- Path to SmartThings: HA REST API → SmartThings integration (see jctsh/CLAUDE.md)

## How It Works
1. Any garage activity (motion, door, camera) restarts the HA timer
2. Timer duration is read from `input_number.garage_timer_duration` (default 20 min)
3. When timer expires: Garage Presence Vswitch is turned off; if auto-close is enabled
   and the door is open, the garage door is triggered to close

## HA Helpers
| Helper | Entity ID | Purpose |
|---|---|---|
| Garage Presence Timer | `timer.garage_presence_timer` | Countdown timer |
| Garage Timer Duration | `input_number.garage_timer_duration` | Duration in minutes (1–120, default 20) |

Both created via HA UI (Settings → Devices & Services → Helpers). Not in configuration.yaml.

## SmartThings Devices
| Device | ST ID | HA Entity ID | Role |
|---|---|---|---|
| Garage Sensor | eae7580a-66cb-476f-b5a5-f0672b2a76aa | `binary_sensor.garage_motion_motion` | Trigger |
| Garage Door Sensor | 15597627-aec7-4e51-baec-7d106c7ee092 | `binary_sensor.garage_door_sensor_door` | Trigger |
| Garage Cam | b11a8e19-87da-4ca3-b062-a8a95254548b | `binary_sensor.garage_cam_motion` | Trigger |
| Garage Presence Vswitch | a3185dc5-13c1-4a64-85b5-4784312baa72 | `switch.garage_presence_vswitch` | Output — turned off on expiry |
| Garage Door Auto Close Enable | 284c6997-af09-4be7-9d39-e03ab7f8190a | `switch.garage_door_auto_close_enable_vswitch` | Gate — must be on to auto-close |
| Garage Door Open Vswitch | c3edbefa-e4fe-494a-aeca-01282bd4cbb4 | `switch.garage_door_open_vswitch` | Gate — must be on to auto-close |
| Open/Close Garage Door | 89d71ace-151d-41aa-866f-0290e22bfb91 | `switch.open_close_garage_door` | Output — triggered to close door |

Note: Garage Timer Duration (ST 49a4fa15-940d-45e8-a644-acbd4c0d3b67) was not exposed
as an HA entity by the SmartThings integration. Replaced by `input_number.garage_timer_duration`.

## HA Automations
Both created via HA UI (Settings → Automations & Scenes → Edit in YAML).

**Garage Presence - Restart timer on activity** (`mode: restart`)
- Triggers: any of the 3 sensors above
- Action: `timer.start` with duration from `input_number.garage_timer_duration`

**Garage Presence - Timer expired** (`mode: single`)
- Trigger: `timer.finished` event on `timer.garage_presence_timer`
- Action: turn off `switch.garage_presence_vswitch`; if auto-close enabled and door
  open, turn on `switch.open_close_garage_door`

## Adding More Triggers
To add more devices to Automation 1, edit the automation in HA UI and add a new
`state` trigger with the device's HA entity ID.

## Testing
1. Set `input_number.garage_timer_duration` to `1` (1 minute)
2. Trigger any sensor
3. Developer Tools → States → filter `timer.garage_presence_timer` → confirm `active`
4. To force expiry without waiting: Developer Tools → Services → `timer.finish` →
   `timer.garage_presence_timer`
5. Confirm `switch.garage_presence_vswitch` turned off in SmartThings
