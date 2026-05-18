# Automatic Garage Door Opener/Closer — Component Context

Hardware + SmartThings component. No ESP32, no Node-RED, no HA automations.
Fully implemented through hardware modification, Zigbee pairing, and a SmartThings routine.
See `jctsh/CLAUDE.md` for monorepo-wide conventions.

## Architecture
```
SmartThings / Google Home
        │
        ▼
Zigbee Low-Voltage Switch (relay closes momentarily)
        │
        ▼
CreaCity Remote Circuit Board (trigger contacts bridged)
        │
        ▼
RF Signal (Security+ 2.0 rolling code)
        │
        ▼
LiftMaster Garage Door Opener
```

No custom code. The auto-close routine lives entirely in SmartThings.

## SmartThings Devices
| Device | ST ID | HA Entity ID | Role |
|---|---|---|---|
| Open/Close Garage Door (Zigbee switch) | 89d71ace-151d-41aa-866f-0290e22bfb91 | `switch.open_close_garage_door` | Triggers door toggle |
| Garage Door Auto Close Enable VSwitch | 284c6997-af09-4be7-9d39-e03ab7f8190a | `switch.garage_door_auto_close_enable_vswitch` | Master enable for auto-close routine |
| Garage Door Open VSwitch | c3edbefa-e4fe-494a-aeca-01282bd4cbb4 | `switch.garage_door_open_vswitch` | Reflects door open/closed state |
| Garage Presence VSwitch | a3185dc5-13c1-4a64-85b5-4784312baa72 | `switch.garage_presence_vswitch` | Safety condition — managed by garage-presence component |

## SmartThings Auto-Close Routine
Configured in SmartThings (not HA). Fires when all conditions are true:

| | Detail |
|---|---|
| Precondition | Garage Door Auto Close Enable VSwitch is **on** |
| Trigger | Garage Door Open VSwitch turns **on** (door opened) |
| Condition | Garage Presence VSwitch is **off** (no presence detected) |

Action: turn on `Open/Close Garage Door` switch → Zigbee relay closes → remote fires → LiftMaster closes door.

## Integration Points
- **garage-presence component** manages `switch.garage_presence_vswitch` — this is the safety
  condition that prevents the door closing while someone is in the garage
- **Google Home** — Zigbee switch exposed via SmartThings; voice command toggles the door

## Hardware Notes
- CreaCity Universal Remote (ASIN B098SP6RJ9), model 893Max — visor clip form factor
- PCB button contacts soldered to Zigbee switch output terminals
- LiftMaster opener unmodified — receives standard Security+ 2.0 RF signal
- Do not modify the LiftMaster unit
