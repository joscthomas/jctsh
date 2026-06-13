# Automatic Garage Door Opener/Closer

Hardware-modified visor remote wired to a Zigbee switch, bringing the LiftMaster garage
door under voice and smart home control without modifying the opener unit.

**Status:** Production
**Hardware:** CreaCity visor remote + Zigbee low-voltage switch (no microcontroller,
no custom firmware)

---

## What It Solves

LiftMaster Security+ 2.0 openers use rolling-code RF and cannot be controlled by generic
smart home switches. This component solves that by wiring a Zigbee relay directly to the
PCB button contacts of a paired CreaCity remote — the opener receives a normal RF signal
and never knows the difference. No modification to the LiftMaster unit, no proprietary
bridge hardware.

---

## Architecture

```
SmartThings / Google Home
        │
        ▼
Zigbee low-voltage switch (relay closes momentarily)
        │
        ▼
CreaCity remote PCB (button contacts bridged)
        │
        ▼
Security+ 2.0 RF signal
        │
        ▼
LiftMaster garage door opener
```

The Zigbee switch acts as a momentary trigger: each activation closes the relay briefly,
causing the remote to fire one RF signal. The opener toggles the door state in response.

---

## Quick Start

No firmware to flash. Setup is:

1. Open CreaCity remote, solder leads to the button PCB contacts
2. Connect leads to the Zigbee switch output terminals
3. Pair the CreaCity remote to the LiftMaster opener (standard learn-button process)
4. Pair the Zigbee switch to the SmartThings hub
5. Create the three virtual switches in SmartThings
6. Link SmartThings to Google Home
7. Create the auto-close routine in SmartThings

See [CLAUDE.md](CLAUDE.md) for SmartThings device IDs and full routine configuration.

---

## How It Works

### Voice Control

The Zigbee switch is exposed to Google Home via SmartThings. "Hey Google, turn on the
garage door opener" closes the relay → remote fires → door toggles.

### Auto-Close Routine

Configured in SmartThings (not HA). Fires when all three conditions are true:

| | Condition |
|---|---|
| Precondition | Garage Door Auto Close Enable VSwitch is **on** |
| Trigger | Garage Door Open VSwitch turns **on** (door opened) |
| Safety | Garage Presence VSwitch is **off** (no one in garage) |

Action: activate Zigbee switch → door closes.

The Garage Presence VSwitch is managed by the
[garage-presence](../garage-presence/) component — that component is the safety interlock
that prevents the door closing while someone is inside.

### SmartThings Devices

| Device | ST ID | HA Entity | Role |
|---|---|---|---|
| Open/Close Garage Door | 89d71ace-... | `switch.open_close_garage_door` | Triggers door toggle |
| Auto Close Enable VSwitch | 284c6997-... | `switch.garage_door_auto_close_enable_vswitch` | Master enable |
| Garage Door Open VSwitch | c3edbefa-... | `switch.garage_door_open_vswitch` | Door state |
| Garage Presence VSwitch | a3185dc5-... | `switch.garage_presence_vswitch` | Safety condition |

---

## Files

| File | Purpose |
|---|---|
| `CLAUDE.md` | SmartThings device IDs, full routine configuration, architecture decisions |
