# JCT Smart Home — Automatic Garage Door Opener/Closer
**Author:** Joseph C Thomas (JCT)  
**Purpose:** Documents the design, hardware, and automation logic for the Automatic Garage Door Opener/Closer component of JCT Smart Home (JCTsh).  
**Project:** JCT Smart Home (JCTsh)  
**Version:** 1.0  
**Version description:** Initial release.

---

## Overview

The Automatic Garage Door Opener/Closer component integrates a hardware-modified visor remote with a Zigbee low-voltage switch to bring the LiftMaster garage door opener under full smart home control. It supports both voice-commanded operation via Google Home and fully automatic closing via a SmartThings routine when certain presence and enable conditions are met.

There is no custom code in this component. It is fully implemented through hardware modification, Zigbee device pairing, and SmartThings/Google Home configuration.

---

## Hardware

### Garage Door Opener Unit
- **Device:** CreaCity Universal Garage Door Opener Remote (Amazon ASIN: B098SP6RJ9), model 893Max
- **Compatibility:** LiftMaster, Chamberlain, and Craftsman openers manufactured 1993–present; uses Security+ 2.0 rolling code technology
- **Form factor:** Visor clip remote
- **Modification:** The remote's circuit board was opened and the contacts that trigger the door activation button were identified and exposed. These contacts serve as the trigger input for the Zigbee switch.

### Zigbee Low-Voltage Switch
- Wired directly to the trigger contacts on the CreaCity remote circuit board
- When the Zigbee switch closes its relay momentarily, it simulates a button press on the remote, which transmits the rolling-code RF signal to the LiftMaster opener
- Paired to the SmartThings hub as a standard Zigbee switch device

### LiftMaster Garage Door Opener
- The existing LiftMaster unit mounted in the garage receives the RF signal from the CreaCity remote exactly as it would from a normal button press
- No modification to the LiftMaster unit itself

---

## How It Works

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
RF Signal Transmitted (Security+ 2.0 rolling code)
        │
        ▼
LiftMaster Garage Door Opener (door opens or closes)
```

The Zigbee switch acts as a momentary trigger: each time it is activated, it briefly closes the circuit across the remote's button contacts, causing the remote to fire exactly one RF signal to the LiftMaster opener. The opener toggles the door (open → close or close → open) in response.

---

## Virtual Switches (VSwitches)

This component depends on three VSwitches managed in SmartThings:

| VSwitch | Purpose |
|---|---|
| **Garage Door Enable Auto Close VSwitch** | Master enable/disable for the automatic closing routine. When off, the auto-close routine will not fire. |
| **Garage Door Open VSwitch** | Reflects the current open/closed state of the garage door. Turned on when the door is open, off when closed. |
| **Garage Presence VSwitch** | Reflects whether presence is currently detected in the garage. Managed by the Garage Presence component of JCTsh. |

---

## Activation Methods

### 1. Google Home Voice Command

The Zigbee switch is exposed to Google Home through SmartThings. A spoken command (e.g., *"Hey Google, turn on the garage door opener"*) activates the Zigbee switch, which triggers the remote and toggles the garage door.

### 2. SmartThings Routine — Garage Door Auto Close

This routine automatically closes the garage door when all of the following conditions are true:

| Condition | Detail |
|---|---|
| **Precondition** | Garage Door Enable Auto Close VSwitch is **on** |
| **Trigger** | Garage Door Open VSwitch is **on** (door is open) |
| **Condition** | Garage Presence VSwitch is **off** (no presence in garage) |

**Action:** Activate the Zigbee switch → triggers the CreaCity remote → LiftMaster closes the door.

The routine will not fire if the enable VSwitch is off (allowing the user to disable auto-close when desired) or if presence is detected in the garage (preventing the door from closing while someone is inside).

---

## Dependencies

| Dependency | Role |
|---|---|
| SmartThings hub | Manages the Zigbee switch, VSwitches, and the auto-close routine |
| Google Home | Provides voice command interface |
| Garage Presence component (JCTsh) | Manages the Garage Presence VSwitch used as a safety condition |

---

## Setup Summary

1. Opened the CreaCity visor remote and identified the PCB contacts corresponding to the door-trigger button.
2. Soldered leads to those contacts and connected them to the output terminals of the Zigbee low-voltage switch.
3. Programmed the CreaCity remote to the LiftMaster opener using the standard learn-button pairing process.
4. Paired the Zigbee switch to the SmartThings hub.
5. Created the three VSwitches in SmartThings.
6. Linked SmartThings to Google Home so the Zigbee switch is voice-controllable.
7. Created the Garage Door Auto Close routine in SmartThings with the conditions and action described above.

No software development or custom code was required. The component is fully operational.
